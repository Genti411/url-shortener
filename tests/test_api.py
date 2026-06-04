import os
import sys
from pathlib import Path

# Configure for tests BEFORE importing the app: SQLite, no Redis.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'test_urls.db'}"
os.environ.pop("REDIS_URL", None)

from fastapi.testclient import TestClient

from app import db as dbm
from app.main import app

dbm.init_db()
client = TestClient(app)


def test_shorten_redirect_and_stats():
    r = client.post("/shorten", json={"url": "https://example.com/page"})
    assert r.status_code == 201
    code = r.json()["short_code"]
    assert r.json()["short_url"].endswith(code)

    # Redirect (do not follow) points at the original URL.
    rr = client.get(f"/{code}", follow_redirects=False)
    assert rr.status_code == 307
    assert rr.headers["location"] == "https://example.com/page"

    # The click was counted.
    st = client.get(f"/api/stats/{code}")
    assert st.status_code == 200
    assert st.json()["clicks"] == 1
    assert st.json()["original_url"] == "https://example.com/page"


def test_invalid_url_rejected():
    assert client.post("/shorten", json={"url": "not-a-url"}).status_code == 422


def test_unknown_code_404():
    assert client.get("/api/stats/zzzznope").status_code == 404
    assert client.get("/zzzznope", follow_redirects=False).status_code == 404
