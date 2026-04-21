# Troubleshooting

Common errors hit while running SoundAtlas locally or deploying it.

## `docker compose up` fails with "port is already in use"

Something else is bound to :3000, :5432, :6379, or :8000 — usually a local Postgres, a running Next.js dev server, or Redis.

```bash
lsof -i :5432   # substitute the port in the error
kill <pid>
```

## Backend returns 500: `relation "countries" does not exist`

Alembic migrations didn't run. The backend container's Dockerfile runs `alembic upgrade head` on startup, so this usually means the backend is running outside Docker. Fix:

```bash
cd backend
alembic upgrade head
```

## Map is blank or console shows `Failed to initialize WebGL`

Chrome has hardware acceleration off. Open `chrome://settings/system`, enable **Use graphics acceleration when available**, restart Chrome.

## Pipeline: `ModuleNotFoundError: No module named 'psycopg2'`

Pipeline deps aren't installed:

```bash
cd pipeline
pip install -r requirements.txt
```

(`requirements.txt` installs `psycopg2-binary`.)

## Pipeline: Spotify returns 401 / 403

`SPOTIFY_CLIENT_ID` or `SPOTIFY_CLIENT_SECRET` in `.env` is wrong, or the Spotify developer app is disabled. Verify both in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

## Pipeline is stuck or very slow

MusicBrainz enforces 1 request/second (their [ToS](https://wiki.musicbrainz.org/MusicBrainz_API/Rate_Limiting)). A full run with a few thousand artists takes ~50 min. Skip that step for a fast test:

```bash
python run_pipeline.py --skip-musicbrainz
```

## A specific artist's country is wrong

Some MusicBrainz entries are ambiguous. Audit + correct:

```bash
python pipeline/audit_countries.py       # flag suspicious resolutions
python pipeline/apply_corrections.py     # apply manual overrides from corrections.json
```

## Deployment: Railway backend crashes with `ModuleNotFoundError: psycopg2`

Railway's injected `DATABASE_URL` starts with `postgresql://`, but the async backend needs `postgresql+asyncpg://`. The rewrite happens in `backend/app/config.py` via a `field_validator`:

```python
@field_validator("DATABASE_URL", mode="after")
@classmethod
def fix_async_url(cls, v: str) -> str:
    if v.startswith("postgresql://"):
        return v.replace("postgresql://", "postgresql+asyncpg://", 1)
    return v
```

If you still see the error, confirm `DATABASE_URL` is actually reaching the app (Railway → service → Variables) and the validator is running.

## Deployment: Vercel preview URLs get CORS errors

The backend whitelists all Vercel subdomains via regex (`backend/app/main.py`):

```python
allow_origin_regex=r"https://.*\.vercel\.app"
```

For any other domain, add it to `CORS_ORIGINS` (comma-separated) in Railway's backend env vars.

## Deployment: Frontend can't reach backend (404 on `/api/...`)

Check `NEXT_PUBLIC_API_URL` in Vercel's env vars. It should be the backend root (`https://your-backend.up.railway.app`) with **no trailing `/api`** — the frontend code appends that itself. Also remember `NEXT_PUBLIC_*` vars are baked in at build time, so you must redeploy after changing them.
