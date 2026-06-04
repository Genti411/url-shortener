"""URL shortener API (FastAPI).

Routes:
  POST /shorten            create a short link (rate-limited per client IP)
  GET  /{code}             redirect to the original URL (Redis-cached), counts a click
  GET  /api/stats/{code}   click analytics for a code
  GET  /healthz            liveness

The redirect path checks Redis first and only falls back to Postgres on a miss,
so the hot path mostly avoids the database.
"""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from . import cache
from . import db as dbm
from . import shortener

RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "20"))  # creations per minute per IP


@asynccontextmanager
async def lifespan(_app: FastAPI):
    dbm.init_db()
    yield


app = FastAPI(title="URL Shortener", lifespan=lifespan)


class ShortenIn(BaseModel):
    url: HttpUrl


class ShortenOut(BaseModel):
    short_code: str
    short_url: str
    original_url: str


@app.post("/shorten", response_model=ShortenOut, status_code=201)
def shorten(body: ShortenIn, request: Request, db: Session = Depends(dbm.get_db)):
    client_ip = request.client.host if request.client else "anon"
    if not cache.rate_limit_ok(client_ip, RATE_LIMIT):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    row = dbm.ShortURL(original_url=str(body.url))
    db.add(row)
    db.flush()                       # assigns row.id
    row.short_code = shortener.code_for_id(row.id)
    db.commit()

    cache.cache_set(row.short_code, row.original_url)
    base = str(request.base_url).rstrip("/")
    return ShortenOut(
        short_code=row.short_code,
        short_url=f"{base}/{row.short_code}",
        original_url=row.original_url,
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/stats/{code}")
def stats(code: str, db: Session = Depends(dbm.get_db)):
    row = db.scalar(select(dbm.ShortURL).where(dbm.ShortURL.short_code == code))
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "short_code": row.short_code,
        "original_url": row.original_url,
        "clicks": row.clicks,
        "created_at": row.created_at,
        "last_accessed": row.last_accessed,
    }


@app.get("/{code}")
def redirect(code: str, db: Session = Depends(dbm.get_db)):
    url = cache.cache_get(code)
    if url is None:
        row = db.scalar(select(dbm.ShortURL).where(dbm.ShortURL.short_code == code))
        if row is None:
            raise HTTPException(status_code=404, detail="not found")
        url = row.original_url
        cache.cache_set(code, url)
    # Count the click (analytics). Done via UPDATE so it works whether or not the
    # row was loaded into the session above.
    db.execute(
        update(dbm.ShortURL)
        .where(dbm.ShortURL.short_code == code)
        .values(clicks=dbm.ShortURL.clicks + 1, last_accessed=func.now())
    )
    db.commit()
    return RedirectResponse(url, status_code=307)
