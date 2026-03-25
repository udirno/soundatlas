# Architecture

**Analysis Date:** 2026-03-24

## Pattern Overview

**Overall:** Layered client-server architecture with data analytics pipeline

**Key Characteristics:**
- Separation of concerns: Frontend (Next.js), Backend (FastAPI), Database (PostgreSQL), Data Pipeline
- API-first design with RESTful endpoints for data access and AI insights
- Stateless services communicating via HTTP
- Real-time data visualization with time-series queries
- AI-augmented insights using Claude API for natural language analysis

## Layers

**Presentation (Frontend):**
- Purpose: Interactive UI for exploring disease data, visualizing trends, and querying AI insights
- Location: `/frontend/src/`
- Contains: React components, hooks, page layouts, API client
- Depends on: Backend API, Mapbox GL JS, Recharts visualization
- Used by: End users via web browser

**Business Logic / Application (Backend):**
- Purpose: API layer exposing disease data, correlations, trends, and AI-powered insights
- Location: `/backend/app/`
- Contains: Route handlers, service classes, database models, schemas
- Depends on: SQLAlchemy ORM, Database, Redis (optional), Claude API
- Used by: Frontend, external clients

**Data Access (Services):**
- Purpose: Encapsulate domain-specific business logic and queries
- Location: `/backend/app/services/`
- Key services:
  - `DiseaseService`: Query and filter disease records by region/date range
  - `TrendService`: Time-series analysis, anomaly detection, growth rate calculation
  - `CorrelationService`: Pearson and Spearman correlation between disease and climate factors
  - `AIService`: Claude-based natural language insight generation

**Data Model (ORM Models):**
- Purpose: SQLAlchemy ORM mapping to database tables
- Location: `/backend/app/models/`
- Entities:
  - `Region`: Geographic areas with population, coordinates
  - `Disease`: Disease definitions with categories
  - `DiseaseRecord`: Time-series disease metrics (cases, deaths, rates) by region/date
  - `ClimateRecord`: Environmental data (temperature, rainfall, humidity) by region/date
  - `EconomicRecord`: Socioeconomic indicators (GDP, poverty, vaccination rates) by region/year

**Data Storage:**
- Purpose: Persistent storage and querying of multidimensional health data
- Location: PostgreSQL with PostGIS extension
- Database file: `/database/init.sql`
- Includes: Seeded diseases (COVID-19, Tuberculosis, Malaria), indexes for query performance

**API Routes:**
- Purpose: HTTP endpoints for accessing data and generating insights
- Location: `/backend/app/api/routes/`
- Key routes:
  - `/api/diseases/`: List diseases, get time-series data, retrieve metrics
  - `/api/regions/`: List all geographic regions
  - `/api/correlations/`: Compute disease-climate correlations
  - `/api/insights/`: Generate AI-powered insights with conversation history support

## Data Flow

**Query Disease Trends:**
1. Frontend selects disease, region, date range via UI
2. Frontend calls `/api/diseases/{disease_name}/time-series` endpoint
3. Backend `TrendService.get_time_series_data()` queries `DiseaseRecord` table filtered by region/date
4. Results returned as JSON time-series
5. Frontend renders with Recharts line chart

**Generate AI Insight:**
1. User enters natural language question in `AIInsightPanel`
2. Frontend calls `/api/insights/` with disease, region, dates, question
3. Backend endpoint gathers:
   - Disease metrics from `DiseaseService.get_latest_metrics()` or period metrics
   - Climate data from `ClimateRecord` table
   - Economic data from `EconomicRecord` table
   - Correlations from `CorrelationService.get_all_correlations()`
4. `AIService.generate_insight()` calls Claude API with context and conversation history
5. Claude returns narrative analysis; backend wraps with supporting data
6. Frontend displays insight text with correlation tables and anomalies

**Anomaly Detection:**
1. `TrendService.detect_anomalies()` loads `DiseaseRecord` for region/date range
2. Calculates mean and standard deviation of new_cases
3. Flags values >2.5 standard deviations as anomalies with z-score, severity
4. Returns anomalies list with dates and deviation percentages
5. Frontend displays anomalies in insight response

**State Management:**
- Frontend: React useState for selected disease, region, date range, metrics, comparison mode
- Backend: Stateless; requests include all parameters needed
- Conversation history: Persisted in frontend state between API calls, passed to Claude API for context

## Key Abstractions

**Service Classes:**
- Purpose: Encapsulate business logic, provide clean interfaces for routes
- Examples: `DiseaseService`, `TrendService`, `CorrelationService`, `AIService`
- Pattern: Static methods receiving DB session + parameters; return formatted data

**Pydantic Schemas:**
- Purpose: Request/response validation and type hints
- Location: `/backend/app/schemas/`
- Examples: `Disease`, `DiseaseRecord`, `InsightQuery`, `InsightResponse`

**API Router Pattern:**
- Purpose: Organize endpoints by domain (diseases, regions, correlations, insights)
- Each router in `/backend/app/api/routes/` is included in main app with prefix
- Enables modular route management

**Database Models with Relationships:**
- Purpose: Define ORM schema with foreign keys and relationships
- Pattern: Declarative Base classes; SQLAlchemy automates SQL generation
- Relationships enable lazy-loading of related data (e.g., disease.records)

## Entry Points

**Backend Main Entry:**
- Location: `/backend/app/main.py`
- Triggers: `uvicorn` startup (see `docker-compose.yml`)
- Responsibilities:
  - Initialize FastAPI app
  - Configure CORS middleware
  - Register route routers (diseases, regions, correlations, insights)
  - Create database tables on startup via lifespan event
  - Provide `/` health endpoint

**Frontend Entry:**
- Location: `/frontend/src/app/layout.tsx` and `/frontend/src/app/page.tsx`
- Triggers: Next.js page load
- Responsibilities:
  - Render root layout with NavBar, Sidebar, MapContainer, AIInsightPanel
  - Manage global UI state (selected disease, region, dates, comparison mode)
  - Coordinate data fetching between components

**Data Seeding:**
- Location: `/backend/app/main.py` (`/api/seed` endpoint) and `/backend/ingest_covid.py`
- Triggers: Manual POST request or startup
- Responsibilities:
  - Populate `regions`, `diseases`, `disease_records`, `climate_records`, `economic_records` with sample data
  - Enables application to run without external data sources

## Error Handling

**Strategy:** Graceful degradation with optional dependencies

**Backend Patterns:**
- Missing API keys (Anthropic, OpenWeather): Services initialize with empty strings; features degrade gracefully
- Database query failures: Return 404 HTTPException with descriptive message
- Correlation/anomaly insufficient data: Return error dict with "error" key; routes handle gracefully
- Claude API failures: Catch exception; return "Error generating insight" message to frontend

**Frontend Patterns:**
- Failed metric fetch: Display "No data" error state in Sidebar
- Failed insight generation: Display error message in AIInsightPanel
- Missing environment variables (API URL, Mapbox token): Provide defaults

## Cross-Cutting Concerns

**Logging:** None configured; relies on FastAPI/Uvicorn request logging and browser console

**Validation:**
- Backend: Pydantic schemas validate request bodies and return types
- Frontend: No explicit validation; assumes backend returns expected shape

**Authentication:** None implemented; endpoints are publicly accessible (CORS configured for localhost:3000)

**Database Transactions:**
- Pattern: FastAPI dependency `get_db()` yields SessionLocal
- Routes receive Session; commits happen implicitly on function return
- Errors trigger rollback

---

*Architecture analysis: 2026-03-24*
