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

## Pipeline

```bash
cd pipeline
python run_pipeline.py path/to/your/spotify/StreamingHistory.json
```
