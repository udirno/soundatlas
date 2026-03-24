# Phase 1: Infrastructure and Pipeline Foundation - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Docker Compose environment with PostgreSQL, Redis, FastAPI, and Next.js services. Database schema with all tables and extensions. Spotify export parser that extracts liked tracks into memory. Live validation of Spotify audio features endpoint access. Data enrichment, API endpoints, and frontend are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Database schema design
- Seed countries table with all UN-recognized countries (~193) — comprehensive world coverage even for countries with zero artists
- Audio features stored as nullable float columns directly on the tracks table (energy, danceability, valence, tempo, etc.) — no separate table
- Artist genres stored as PostgreSQL text[] array column on artists table — no separate genres/join table
- user_tracks table is minimal: track IDs, artist FK, and timestamps only — no play count or extra metadata

### Docker environment layout
- Single docker-compose.yml file — no base/override split, dev-only project
- Pipeline scripts run on the host machine (not in Docker), connecting to PostgreSQL in Docker
- PostgreSQL data persists via named Docker volume — survives `docker compose down`/up cycles
- Standard port mapping: PostgreSQL 5432, Redis 6379, FastAPI 8000, Next.js 3000

### Spotify export parsing
- Parser built as an importable Python module — Phase 2 enrichment scripts can import and reuse it
- Input path provided via CLI argument or environment variable (not hardcoded)
- Malformed entries (missing artist name, no Spotify ID) are skipped with a logged warning — don't block the parse
- Deduplication happens during parsing — same Spotify track ID appearing multiple times keeps first occurrence only

### Audio features validation
- Standalone validation script separate from the parser — run independently to test endpoint access
- Uses a real track ID extracted from the user's YourLibrary.json export — proves the full flow works
- Single track test is sufficient — no batch testing needed in validation
- On 403 result, writes a config file flag (e.g., AUDIO_FEATURES_AVAILABLE=false) that Phase 2 reads to decide whether to skip audio features enrichment

### Claude's Discretion
- Exact database migration tool/approach
- Docker healthcheck configuration
- Python project structure and dependency management
- Logging format and verbosity levels
- Error handling patterns within scripts

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-infrastructure-and-pipeline-foundation*
*Context gathered: 2026-03-24*
