# SoundAtlas

Music geography intelligence platform. Upload your Spotify library and see where your music actually comes from — artist origins plotted on a world map, colored by top genre per country, with stats on geographic diversity, top genres, and per-country breakdowns.

**Live:** [soundatlas-pi.vercel.app](https://soundatlas-pi.vercel.app)

## Stack

- **Frontend** — Next.js (App Router) + TypeScript + Mapbox GL + Tailwind
- **Backend** — FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
- **Pipeline** — Spotify API + MusicBrainz (for artist → country resolution)
- **AI Chat** — Anthropic Claude API
- **Deploy** — Vercel (frontend) + Railway (backend, Postgres, Redis)

## Local development

```bash
cp .env.example .env   # fill in SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, ANTHROPIC_API_KEY, NEXT_PUBLIC_MAPBOX_TOKEN
docker compose up -d
cd frontend && npm install && npm run dev
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs

## Getting your Spotify data

The pipeline runs against your personal Spotify streaming history. To get the file:

1. Go to [spotify.com/account/privacy](https://www.spotify.com/account/privacy)
2. Under **Download your data**, request **Extended streaming history** (not the basic one)
3. Wait — Spotify emails a download link in up to ~30 days (usually a few days)
4. Unzip. You'll get files like `Streaming_History_Audio_*.json`

## Pipeline

Point `run_pipeline.py` at one of the JSON files from the export:

```bash
cd pipeline
python run_pipeline.py path/to/Streaming_History_Audio_2024.json
```

The pipeline parses the history, resolves each artist to a country of origin via MusicBrainz, enriches genre and image data via the Spotify API, and writes everything to Postgres.
