# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**AI & Insights:**
- Anthropic Claude API - Natural language question answering and disease insight generation
  - SDK/Client: `anthropic` 0.43.0 (location: `backend/requirements.txt`)
  - Integration: `backend/app/services/ai_service.py`
  - Auth: `ANTHROPIC_API_KEY` environment variable

**Mapping & Location Services:**
- Mapbox GL JS - Interactive vector map rendering and geospatial visualization
  - SDK/Client: `mapbox-gl` 3.16.0 and `@types/mapbox-gl` 3.4.1
  - Integration: `frontend/src/components/map/MapContainer.tsx`
  - Auth: `NEXT_PUBLIC_MAPBOX_TOKEN` environment variable (public token for frontend)

**Weather & Climate Data:**
- OpenWeather API - Historical and current climate data
  - Auth: `OPENWEATHER_API_KEY` environment variable
  - Purpose: Populated into `ClimateRecord` model (location: `backend/app/models/climate.py`)
  - Data stored: temperature, rainfall, humidity, wind speed, pressure with `data_source` field set to "OpenWeather"
  - Note: API calls not yet fully implemented; model prepared for integration

## Data Storage

**Primary Database:**
- PostgreSQL 15 with PostGIS 3.3
  - Connection: `DATABASE_URL` environment variable (format: `postgresql://user:password@host:port/database`)
  - Client: SQLAlchemy 2.0.23 ORM (location: `backend/app/database.py`)
  - Schema: Managed via Alembic migrations (location: `backend/alembic/`)
  - Models: `backend/app/models/` containing:
    - `region.py` - Geographic regions with PostGIS geometry support
    - `disease.py` - Disease records and statistics
    - `climate.py` - Climate observations
    - `economic.py` - Economic/socioeconomic indicators

**Caching Layer:**
- Redis 7 Alpine
  - Connection: `REDIS_URL` environment variable (format: `redis://host:port`)
  - Client: `redis` 5.0.1 Python package
  - Purpose: Query result caching, session management
  - Docker service: `healthmap_redis` in `docker-compose.yml`

**File Storage:**
- Local filesystem only - No external storage service (S3, etc.)
- Database seeding from SQL files in `database/seed/`

## Authentication & Identity

**Authentication Provider:**
- Custom JWT-based authentication (planned)
  - Implementation: Uses `python-jose[cryptography]` 3.3.0 and `passlib[bcrypt]` 1.7.4
  - Token handling: `backend/app/core/` (location: `backend/app/core/`)
  - Password hashing: bcrypt via passlib

**Public API Access:**
- Frontend endpoints marked as public (no authentication required)
- Backend supports CORS for multiple origins via `CORS_ORIGINS` environment variable

## Monitoring & Observability

**Error Tracking:**
- Not detected - No Sentry, Rollbar, or similar service integrated

**Logs:**
- Console-based logging through FastAPI logger
- Application debug mode controllable via `DEBUG` environment variable

**Health Checks:**
- Render platform health checks (Docker healthcheck defined in `docker-compose.yml`)
- Backend `/health` endpoint returns `{"status": "healthy"}` (location: `backend/app/main.py`)
- PostgreSQL health check using `pg_isready`
- Redis health check using `redis-cli ping`

## CI/CD & Deployment

**Hosting Platforms:**
- Render - Backend API, PostgreSQL, Redis deployment
  - Blueprint deployment via `render.yaml` (location: `render.yaml`)
  - Services: `healthmap-api` (FastAPI), `healthmap-db` (PostgreSQL), `healthmap-redis` (Redis)
  - Region: Oregon (specified in `render.yaml`)
  - Plan: Free tier

- Vercel - Frontend Next.js deployment
  - Configuration: `vercel.json` (location: `vercel.json`)
  - Build command: `npm run build`
  - Dev command: `npm run dev`

**CI Pipeline:**
- Not detected - No GitHub Actions, GitLab CI, or similar detected

**Local Development:**
- Docker Compose orchestration for full stack (`docker-compose.yml`)
  - Network: `healthmap_network` bridge
  - Services with health checks and automatic startup ordering

## Environment Configuration

**Required Environment Variables:**

*Database:*
- `DATABASE_URL` - PostgreSQL connection string (required)
- `POSTGRES_USER` - Default: `healthmap_user`
- `POSTGRES_PASSWORD` - Default: `healthmap_password`
- `POSTGRES_DB` - Default: `healthmap_db`

*Caching:*
- `REDIS_URL` - Redis connection string (required)

*API Keys:*
- `ANTHROPIC_API_KEY` - Anthropic Claude API key (optional; degrades gracefully if missing)
- `MAPBOX_TOKEN` - Mapbox server-side token (optional)
- `NEXT_PUBLIC_MAPBOX_TOKEN` - Mapbox public token for frontend (optional)
- `OPENWEATHER_API_KEY` - OpenWeather API key (optional; degrades gracefully if missing)

*Application:*
- `BACKEND_HOST` - Default: `0.0.0.0`
- `BACKEND_PORT` - Default: `8000`
- `CORS_ORIGINS` - Comma-separated list of allowed origins (default: `http://localhost:3000`)
- `NEXT_PUBLIC_API_URL` - Backend API base URL for frontend (default: `http://localhost:8000`)
- `DEBUG` - Boolean debug mode (default: `true` for development, `false` for production)

**Secrets Location:**
- `.env` file in project root (not committed, template: `.env.example`)
- `backend/.env.example` provides backend-specific template
- Render blueprint auto-links `DATABASE_URL` and `REDIS_URL` from provisioned services

## Webhooks & Callbacks

**Incoming:**
- Not detected - No webhook endpoints for external data ingestion

**Outgoing:**
- Not detected - No outgoing webhook calls to external services

## API Client Integration

**Frontend HTTP Client:**
- axios 1.13.2
  - Configuration: `frontend/src/lib/api-client.ts`
  - Base URL: `process.env.NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`)
  - Endpoints consumed:
    - `/api/regions` - List geographic regions
    - `/api/disease/*` - Disease metrics and data
    - `/api/correlations/*` - Correlation analysis
    - `/api/insights/*` - AI-powered insights
    - `/api/trends/*` - Time series trends

**Backend HTTP Clients:**
- httpx 0.25.2 - Async HTTP for external API calls
- Preparatory groundwork for OpenWeather API integration (not fully implemented)

---

*Integration audit: 2026-03-24*
