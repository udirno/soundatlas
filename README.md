# SoundAtlas

Music geography intelligence platform. The pipeline reads your Spotify liked-tracks export, resolves each artist to a country of origin, and plots them on a world map colored by top genre. Ask a built-in AI chat questions about your listening geography.

**Live:** [soundatlas-pi.vercel.app](https://soundatlas-pi.vercel.app) (loaded with my own library)

## Stack

- **Frontend** — Next.js (App Router) + TypeScript + Mapbox GL + Tailwind
- **Backend** — FastAPI + async SQLAlchemy + PostgreSQL + Redis
- **Pipeline** — Python + Spotify API + MusicBrainz
- **AI Chat** — Anthropic Claude API
- **Deploy** — Vercel (frontend) + Railway (backend, Postgres, Redis)

## How it works

```
  YourLibrary.json (Spotify export)
           │
           ▼
   pipeline scripts ─────────▶ Postgres ◀───── FastAPI (:8000)
           │                                         ▲
           ├─▶ Spotify API     (genres, images)      │
           └─▶ MusicBrainz     (country of origin)   │
                                                     │
                                 Next.js (:3000) ────┘
                                       │
                                       ├─▶ Mapbox GL     (map render)
                                       └─▶ Claude API    (AI chat)
```

## Prerequisites

You need Docker + Docker Compose, plus four credentials:

| Credential | Where to get it |
|---|---|
| `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET` | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) → create an app |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | [account.mapbox.com/access-tokens](https://account.mapbox.com/access-tokens) → default public token (starts with `pk.`) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) |

And your Spotify library export:

1. Go to [spotify.com/account/privacy](https://www.spotify.com/account/privacy)
2. Request **Account data** (the default — *not* Extended streaming history)
3. Spotify emails the download in ~5 days
4. Unzip to `~/Downloads/Spotify Account Data/YourLibrary.json` (or anywhere — you can point the pipeline at a custom path)

## Quickstart

```bash
# 1. Configure credentials
cp .env.example .env
# Edit .env and fill in the four values above

# 2. Start all services (Postgres, Redis, backend, frontend)
docker compose up -d

# 3. Seed the database from your Spotify export
cd pipeline
pip install -r requirements.txt
python run_pipeline.py
```

Then open [http://localhost:3000](http://localhost:3000).

The pipeline takes ~50 min for a few thousand artists — MusicBrainz rate-limits country lookups to 1 req/sec.

## Pipeline flags

```bash
python run_pipeline.py --export-path /custom/path/YourLibrary.json   # non-default export location
python run_pipeline.py --skip-musicbrainz                            # fast dry run, no country resolution
python run_pipeline.py --stats-only                                  # print current DB stats, no API calls
```

## Running into issues?

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
