# URL Shortener with Analytics

A small but production-shaped URL shortener: **FastAPI** + **PostgreSQL** for
storage and **Redis** for hot-path caching and rate limiting. A classic
system-design build that shows API design, caching strategy, and abuse
protection — not just CRUD.

| Area | What's shown |
|------|--------------|
| **FastAPI** | typed routes, Pydantic models, dependency injection, lifespan |
| **PostgreSQL** | SQLAlchemy 2.0 ORM, indexed lookups, click analytics |
| **Redis** | caches code→URL so redirects skip the DB; fixed-window rate limiter |
| **System design** | collision-free base62 codes from the primary key, hot/cold path split |

## Design notes (interview talking points)

- **Short codes are base62 of the row id** (+ an offset). Because the id is
  unique, codes never collide — no random-generate-and-retry loop.
- **Redirects check Redis first**, falling back to Postgres only on a cache miss,
  then re-populating the cache. The read-heavy hot path mostly avoids the DB.
- **Rate limiting** is a Redis fixed-window counter (`INCR` + `EXPIRE`) keyed by
  client IP, so link creation can't be abused.
- **Analytics** (click count + last-accessed) are updated with a single `UPDATE`
  on redirect.

## Run

```bash
docker compose up --build      # API on http://localhost:8000
```

```bash
# create a short link
curl -s localhost:8000/shorten -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/some/long/path"}'
# -> {"short_code":"...","short_url":"http://localhost:8000/...","original_url":"..."}

# follow it (redirects)
curl -sL localhost:8000/<code> -o /dev/null -w "%{http_code}\n"

# analytics
curl -s localhost:8000/api/stats/<code>
```

Interactive API docs at <http://localhost:8000/docs>. Stop: `docker compose down -v`.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest          # base62 + API flow on SQLite (no infra needed)
```

## Layout

```
app/shortener.py   base62 code generation (pure, unit-tested)
app/db.py          SQLAlchemy models + session (Postgres / SQLite)
app/cache.py       Redis cache + fixed-window rate limiter (no-op without Redis)
app/main.py        FastAPI routes
tests/             base62 + API integration tests
docker-compose.yml postgres + redis + api
```
