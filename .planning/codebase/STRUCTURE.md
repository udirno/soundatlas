# Codebase Structure

> Directory layout, key locations, and naming conventions for HealthMap

## Directory Tree

```
healthmap/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point, CORS, router mounting, seed endpoint
│   │   ├── config.py                  # Pydantic Settings (env-based config)
│   │   ├── database.py                # SQLAlchemy engine, session, Base
│   │   ├── core/
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── correlations.py    # Disease-climate correlation endpoints
│   │   │       ├── disease.py         # Disease CRUD and metrics endpoints
│   │   │       ├── insights.py        # AI-powered insight generation
│   │   │       └── regions.py         # Region listing endpoints
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── climate.py             # ClimateRecord ORM model
│   │   │   ├── disease.py             # Disease, DiseaseRecord ORM models
│   │   │   ├── economic.py            # EconomicRecord ORM model
│   │   │   └── region.py              # Region ORM model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── disease.py             # Pydantic response schemas
│   │   │   ├── insights.py            # Insight request/response schemas
│   │   │   └── region.py              # Region response schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ai_service.py          # Anthropic Claude integration (686 lines of core logic)
│   │   │   ├── correlation_service.py # Pearson/Spearman correlation computation
│   │   │   ├── disease_service.py     # Disease data queries, metrics, trends
│   │   │   └── trend_service.py       # Anomaly detection, growth rate, time series
│   │   └── utils/
│   │       └── __init__.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py  # Initial migration
│   ├── alembic.ini
│   ├── ingest_covid.py                # Standalone COVID data ingestion script
│   ├── requirements.txt
│   ├── runtime.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root layout with fonts, metadata
│   │   │   ├── page.tsx               # Main page — composes Sidebar, Map, AIInsightPanel
│   │   │   └── globals.css            # Tailwind imports + custom styles
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   └── TrendChart.tsx     # Recharts-based disease trend visualization
│   │   │   ├── layout/
│   │   │   │   ├── AIInsightPanel.tsx # AI chat/insight panel (right sidebar)
│   │   │   │   ├── NavBar.tsx         # Top navigation bar
│   │   │   │   └── Sidebar.tsx        # Disease/region/date filters (left sidebar)
│   │   │   └── map/
│   │   │       └── MapContainer.tsx   # Mapbox GL globe with country selection
│   │   └── lib/
│   │       └── api-client.ts          # Axios API client + TypeScript interfaces
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── eslint.config.mjs
│   ├── postcss.config.mjs
│   └── Dockerfile
├── database/
│   ├── init.sql                       # Schema DDL: tables, indexes, PostGIS, seed diseases
│   └── seed/
│       └── seed_regions.sql           # Region seed data (20 countries)
├── data-pipeline/
│   ├── requirements.txt
│   └── scripts/
│       ├── ingest_climate.py
│       ├── ingest_covid_complete.py
│       ├── ingest_owid.py
│       ├── ingest_who_malaria.py
│       └── ingest_who_tb.py
├── docker-compose.yml                 # Orchestrates backend, frontend, postgres, redis
├── render.yaml                        # Render.com deployment config
├── vercel.json                        # Vercel frontend deployment config
├── runtime.txt
├── DEPLOYMENT.md
└── README.md
```

## Key Locations

| What | Where |
|------|-------|
| API entry point | `backend/app/main.py` |
| API routes | `backend/app/api/routes/` |
| ORM models | `backend/app/models/` |
| Business logic | `backend/app/services/` |
| Pydantic schemas | `backend/app/schemas/` |
| Configuration | `backend/app/config.py` |
| DB connection | `backend/app/database.py` |
| Frontend entry | `frontend/src/app/page.tsx` |
| Frontend components | `frontend/src/components/` |
| API client | `frontend/src/lib/api-client.ts` |
| DB schema DDL | `database/init.sql` |
| Data ingestion | `data-pipeline/scripts/` |
| Deployment | `docker-compose.yml`, `render.yaml`, `vercel.json` |

## Naming Conventions

### Python (Backend)
- **Files:** `snake_case.py` — `correlation_service.py`, `disease.py`
- **Classes:** `PascalCase` — `DiseaseService`, `CorrelationService`, `AIService`
- **Functions/methods:** `snake_case` — `get_disease_data`, `compute_disease_climate_correlation`
- **Constants:** `UPPER_SNAKE_CASE` — `DATABASE_URL`, `CORS_ORIGINS`
- **ORM models:** singular nouns — `Region`, `Disease`, `DiseaseRecord`

### TypeScript (Frontend)
- **Files:** `PascalCase.tsx` for components — `MapContainer.tsx`, `TrendChart.tsx`
- **Files:** `kebab-case.ts` for utilities — `api-client.ts`
- **Components:** `PascalCase` — `MapContainer`, `AIInsightPanel`, `Sidebar`
- **Interfaces:** `PascalCase` — `Region`, `PeriodMetrics`, `InsightResponse`
- **Variables/functions:** `camelCase` — `selectedDisease`, `handleRegionSelect`

### Directory Organization
- Components grouped by function: `layout/`, `map/`, `charts/`
- Backend follows layered pattern: `routes/ → services/ → models/`
- Data pipeline scripts prefixed with `ingest_` by data source

## Where to Add New Code

| Adding | Location | Pattern |
|--------|----------|---------|
| New API endpoint | `backend/app/api/routes/{resource}.py` | Create router, add to `main.py` |
| New ORM model | `backend/app/models/{entity}.py` | SQLAlchemy model, import in `__init__.py` |
| New service | `backend/app/services/{name}_service.py` | Static methods class pattern |
| New Pydantic schema | `backend/app/schemas/{resource}.py` | Pydantic BaseModel |
| New React component | `frontend/src/components/{category}/` | Default export, PascalCase file |
| New API client method | `frontend/src/lib/api-client.ts` | Add to `apiClient` object |
| New data ingestion | `data-pipeline/scripts/ingest_{source}.py` | Standalone script |
| New DB migration | `backend/alembic/versions/` | `alembic revision --autogenerate` |

## Special Directories

- `backend/venv/` — Python virtual environment (not committed)
- `frontend/node_modules/` — npm dependencies (not committed)
- `frontend/.next/` — Next.js build output (not committed)
- `backend/alembic/versions/` — Database migration history
- `data-pipeline/scripts/` — Standalone ingestion scripts, run manually or via cron
