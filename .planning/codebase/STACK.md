# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- TypeScript 5 - Frontend (React/Next.js components, client logic)
- Python 3.11 - Backend (FastAPI server, data processing)

**Secondary:**
- JavaScript - Build scripts, configuration files
- SQL - Database schema and migrations

## Runtime

**Environment:**
- Node.js 18+ - Frontend execution and build
- Python 3.11.11 - Backend runtime (specified in `runtime.txt`)

**Package Managers:**
- npm (Node) - Frontend dependency management, lockfile: `package-lock.json` present
- pip (Python) - Backend dependency management, uses `requirements.txt`

## Frameworks

**Core:**
- Next.js 16.2.0 - Frontend framework with TypeScript support (`frontend/package.json`)
- FastAPI 0.104.1 - Backend web framework with async support (`backend/requirements.txt`)

**Frontend UI:**
- React 19.2.0 - UI component library
- TailwindCSS 4 - Utility-first styling framework
- Tailwind Typography 0.5.19 - Rich text styling plugin

**Geospatial & Visualization:**
- Mapbox GL JS 3.16.0 - Interactive map rendering
- Recharts 3.4.1 - React charting library
- Lucide React 0.553.0 - Icon library

**Backend Services:**
- SQLAlchemy 2.0.23 - ORM for database abstraction
- Alembic 1.12.1 - Database migration tool
- GeoAlchemy2 0.14.2 - PostGIS spatial database support

**Authentication & Security:**
- python-jose[cryptography] 3.3.0 - JWT token handling
- passlib[bcrypt] 1.7.4 - Password hashing
- pydantic 2.5.0 - Data validation
- pydantic-settings 2.1.0 - Configuration management

**Backend Utilities:**
- Uvicorn[standard] 0.24.0 - ASGI server
- httpx 0.25.2 - Async HTTP client
- python-multipart 0.0.6 - Multipart form data parsing
- python-dotenv 1.0.0 - Environment variable loading
- Redis 5.0.1 - Cache client

**Data Processing:**
- pandas 2.1.3 - Data analysis and manipulation (data-pipeline)
- numpy 1.26.2 - Numerical computing (data-pipeline)
- requests 2.31.0 - HTTP requests (data-pipeline)
- pyyaml 6.0.1 - YAML parsing (data-pipeline)

## Testing & Linting

**Frontend:**
- ESLint 9 - JavaScript/TypeScript linting
- ESLint config for Next.js - Framework-specific rules

**Development:**
- TypeScript compiler - Type checking

## Build & Dev Tools

**Frontend:**
- Next.js CLI - Build and development server (`npm run dev`, `npm run build`)
- PostCSS 4 - CSS processing

**Backend:**
- Uvicorn - Development and production server

## Configuration Files

**Frontend:**
- `frontend/tsconfig.json` - TypeScript configuration
- `frontend/next.config.ts` - Next.js configuration
- `frontend/tailwind.config.ts` - TailwindCSS configuration
- `frontend/eslint.config.mjs` - ESLint rules
- `frontend/postcss.config.mjs` - PostCSS plugins

**Backend:**
- `backend/alembic.ini` - Database migration configuration
- `backend/requirements.txt` - Python dependencies
- `backend/app/config.py` - Application settings (location: `backend/app/config.py`)

**Database:**
- `database/init.sql` - Initial schema setup
- `database/seed/` - Sample data seeding

**Deployment:**
- `render.yaml` - Render platform configuration (location: `render.yaml`)
- `vercel.json` - Vercel platform configuration (location: `vercel.json`)
- `docker-compose.yml` - Local development container orchestration
- `backend/Dockerfile` - Backend container image definition
- `frontend/Dockerfile` - Frontend container image definition

**Environment:**
- `.env.example` - Environment variable template (location: `.env.example`)
- `backend/.env.example` - Backend-specific environment variables (location: `backend/.env.example`)

## Platform Requirements

**Development:**
- Docker & Docker Compose - Containerized local development
- Git - Version control
- npm 10+ - Node package manager
- Python 3.11+ - Python runtime

**Production Platforms:**
- Render - Backend deployment (FastAPI, PostgreSQL, Redis)
- Vercel - Frontend deployment (Next.js)

## Database Technologies

**Primary Storage:**
- PostgreSQL 15 - Relational database with PostGIS extension for geospatial data
- PostGIS 3.3 - Spatial and geographic objects support

**Caching:**
- Redis 7 - In-memory data store for caching and session management

## Containerization

**Docker:**
- Docker Compose version 3.8 - Local development orchestration
- Custom Dockerfiles for backend and frontend
- PostgreSQL 15 PostGIS image: `postgis/postgis:15-3.3`
- Redis Alpine image: `redis:7-alpine`

---

*Stack analysis: 2026-03-24*
