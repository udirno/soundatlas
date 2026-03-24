# Domain Pitfalls

**Domain:** Music intelligence platform with geographic visualization (Spotify + MusicBrainz + Mapbox + PostgreSQL + Claude RAG)
**Researched:** 2026-03-24
**Note on confidence:** External web tools unavailable during research. Findings draw from training data on these well-documented APIs. Spotify audio features deprecation status and MusicBrainz MBID edge cases are flagged LOW confidence — verify against current official docs before Phase 1 begins.

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or blocking pipeline failures.

---

### Pitfall 1: MusicBrainz Artist Disambiguation — Wrong Entity Selected

**What goes wrong:** MusicBrainz search by artist name returns multiple entities with the same name. Naive "take the first result" selects the wrong artist — e.g., searching "Phoenix" returns a French indie band AND a 1980s disco act. The pipeline silently stores the wrong `area` (origin country) for that artist, polluting the map with no error raised.

**Why it happens:** MusicBrainz `artist?query=artist:Phoenix` returns results ranked by relevance score, not by which entity is most likely the Spotify artist. Scores cluster close together for common names. Without cross-referencing Spotify's own artist data (genres, popularity, follower count), there is no signal to pick correctly.

**Consequences:** Wrong country pinned on map for affected artists. Cascading error: country track counts, genre breakdowns, and diversity score all reflect corrupt data. No way to detect without manual audit.

**Prevention:**
1. During MusicBrainz lookup, also pull the Spotify artist object (genres, popularity). Cross-reference by comparing MusicBrainz `disambiguation` field and `type` field against Spotify genres. A "rock" artist in Spotify matching a "rock" MusicBrainz entity is more reliable than name alone.
2. When MusicBrainz returns multiple results with score > 85, store `disambiguation_confidence: LOW` and log the artist for manual review rather than auto-selecting.
3. Add a `resolution_method` column to the `artists` table: `exact_match`, `high_confidence`, `low_confidence`, `manual`, `unresolved`. This makes the problem auditable.
4. Build a manual override table (`artist_country_overrides`) early — before the pipeline runs — so corrections can be applied without re-running the full pipeline.

**Detection (warning signs):**
- Artists with well-known origins appearing on wrong countries (e.g., The Beatles pinned to USA)
- Multiple artists sharing the same MusicBrainz MBID in your database
- MusicBrainz disambiguation field contains descriptors that don't match Spotify genre data

**Phase:** Data pipeline (Phase 1 / seeding phase)

---

### Pitfall 2: MusicBrainz Pipeline Non-Idempotency and Crash Recovery

**What goes wrong:** The pipeline runs for ~50 minutes (3,022 artists at 1 req/sec). At minute 43, a transient network error, a 503 from MusicBrainz, or a script crash means the whole run must restart from scratch. On restart, artists already resolved get re-queried, burning quota and time. Worse: if the pipeline partially writes and then crashes mid-transaction, the database is in a half-resolved state with no clear restart cursor.

**Why it happens:** Pipelines written as simple loops without checkpointing assume successful completion. A single unhandled exception aborts everything.

**Consequences:** 50+ minute re-runs on every failure. Potential rate-limit ban from MusicBrainz if the pipeline hammers the API after restarts. Database inconsistency if some artists have `area` set and others don't, with no way to distinguish "intentionally null" from "not yet processed."

**Prevention:**
1. Add a `mb_resolution_status` column with values: `pending`, `resolved`, `not_found`, `skipped`. The pipeline query is always `WHERE mb_resolution_status = 'pending'` — restarts pick up exactly where they left off.
2. Commit each artist row individually (not in batches) so a crash loses at most one lookup, not a batch.
3. Implement exponential backoff on 429 and 503 responses, not just a fixed 1-second sleep. MusicBrainz serves 503 under load.
4. Log every API call with timestamp, artist name, MBID returned, and HTTP status to a `pipeline_log` table. This gives a full audit trail and helps diagnose rate-limit events.
5. Run the pipeline as a background task with a progress endpoint (`GET /api/admin/pipeline/status`) rather than a blocking script. This lets you monitor without SSH-ing in.

**Detection (warning signs):**
- Script exits without `resolution_status` column in schema — no restart cursor exists
- Using `INSERT` instead of `INSERT ... ON CONFLICT DO UPDATE` (upsert) in artist resolution
- No exponential backoff visible in pipeline code

**Phase:** Data pipeline (Phase 1)

---

### Pitfall 3: Spotify Audio Features Endpoint May Be Deprecated or Restricted

**What goes wrong:** Spotify deprecated or restricted the `GET /v1/audio-features` endpoint for new app registrations as of 2024. Apps created after a certain cutoff date may receive 403 responses or empty data from this endpoint even with valid tokens. The pipeline silently stores null audio features for all tracks, and features-dependent UI (energy distributions, danceability charts) shows empty charts with no clear error.

**Why it happens:** Spotify announced restrictions on several developer endpoints in 2024, including audio features and audio analysis, citing usage changes. The restriction applies by app creation date, not by account type.

**Consequences:** The entire audio feature visualization layer (energy, danceability, valence, tempo, acousticness, instrumentalness) returns empty data. The app still works but loses a significant feature dimension.

**Prevention:**
1. Verify endpoint availability before designing the pipeline around it. Make a test call to `/v1/audio-features?ids=[one_track_id]` with the actual Spotify app credentials being used for SoundAtlas — not just documentation.
2. Design audio feature storage with nullable columns and a `features_available` boolean flag per track. If the endpoint is restricted, degrade gracefully rather than erroring out.
3. Keep audio features enrichment as a separate pipeline stage that can be skipped entirely without breaking the core map.

**Detection (warning signs):**
- HTTP 403 from `/v1/audio-features` with error `"Forbidden"` rather than `"Unauthorized"`
- 200 response but `audio_features` array contains all null entries
- Spotify developer portal shows a warning banner about restricted endpoints for your app

**Confidence:** LOW — Spotify's current policy state should be verified against official developer docs before building the pipeline. This is the single highest-risk external dependency.

**Phase:** Data pipeline (Phase 1) — verify before writing a single line of enrichment code

---

### Pitfall 4: Mapbox GL JS — Individual HTML Markers at Scale Kill Performance

**What goes wrong:** The natural instinct for "put each artist on the map" is to create one `new mapboxgl.Marker()` per artist. With 3,022 artists this creates 3,022 DOM elements. Panning and zooming becomes janky (< 20fps on mid-range hardware). Click handling on overlapping markers becomes unreliable. Mobile is unusable.

**Why it happens:** Mapbox Marker objects are DOM-based, not WebGL-rendered. Each is a separate HTML element. The browser's layout engine must manage thousands of positioned elements during every pan/zoom event.

**Consequences:** Map feels broken. Users blame the app. Performance issues of this type are very hard to fix after the fact without rearchitecting the data model.

**Prevention:**
1. Never use `mapboxgl.Marker` for dataset-scale points. Use a GeoJSON source with a `circle` layer instead — this is WebGL-rendered and handles tens of thousands of points at 60fps.
2. For country-level visualization (which SoundAtlas uses), aggregate data at the country level server-side. Return a GeoJSON FeatureCollection where each feature is a country centroid with properties: `track_count`, `artist_count`, `dominant_genre`, `country_code`. ~200 countries is trivially fast in WebGL.
3. Use Mapbox's built-in `cluster` source option only if you need individual artist pins (future feature). For the current "country bubble" design, country-level GeoJSON is the right model.
4. Store country centroids in PostgreSQL (longitude, latitude per ISO country code). Serve them from a single API endpoint as GeoJSON. Cache this endpoint aggressively in Redis — it changes only when the pipeline reruns.

**Detection (warning signs):**
- Any code that calls `new mapboxgl.Marker()` in a loop over artist data
- Map initialization time > 2 seconds on localhost

**Phase:** Frontend map (Phase 2)

---

### Pitfall 5: Click and Hover Interaction Conflicts on Overlapping Country Bubbles

**What goes wrong:** Multiple countries have nearby or overlapping centroids at lower zoom levels (e.g., Belgium/Netherlands/Luxembourg cluster). Click events fire on the wrong layer or on multiple layers simultaneously. Hover state gets "stuck" when the cursor leaves a feature boundary abruptly.

**Why it happens:** Mapbox GL JS `queryRenderedFeatures` returns all features at a point, not just the topmost. Without explicit layer ordering and `e.features[0]` selection, multiple handlers fire. `mouseleave` events don't fire if the cursor transitions directly between two adjacent features without touching the empty map.

**Consequences:** Clicking on a small country bubble opens the wrong country panel. Hover highlight stays on a country after cursor has moved away, making the UI feel broken.

**Prevention:**
1. Always use `map.on('click', 'layer-id', handler)` scoped to specific layer IDs, not `map.on('click', handler)` on the map.
2. Use `e.features[0]` and return early — never iterate all features at a click point for country selection.
3. Track hover state in a `ref` variable, not component state, to avoid re-renders. Clear hover state in `mousemove` on the map, not just `mouseleave` on the layer.
4. Add `cursor: pointer` via `map.on('mouseenter', 'layer-id', ...)` and `cursor: ''` via `map.on('mouseleave', 'layer-id', ...)`.
5. Test interaction at zoom level 2 (most clustered) and zoom level 5 (most spread) specifically.

**Detection (warning signs):**
- Using `map.on('click', handler)` without a layer ID parameter
- Hover state managed in React `useState` (causes re-renders on every mouse move)

**Phase:** Frontend map (Phase 2)

---

### Pitfall 6: Genre Classification — Treating Spotify's 2,000+ Tags as a Flat List

**What goes wrong:** Spotify's genre tags are hyper-specific: `"vapor twitch"`, `"post-teen pop"`, `"indie poptimism"`, `"bubblegum bass"`. Displaying these raw makes the genre UI unusable. Trying to manually map 2,000+ tags to macro genres (Rock, Pop, Electronic, etc.) is brittle — new tags appear in the data and fall through to "Other."

**Why it happens:** Spotify's genre tags are crowd-sourced and organic, not a controlled taxonomy. A naive `if genre contains "rock"` substring approach misclassifies `"psychedelic rock"` vs `"art rock"` into the same bucket while missing `"shoegaze"` which is functionally rock.

**Consequences:** The genre breakdown chart shows 50%+ "Other." Country detail panels have meaningless genre data. The diversity score calculation is skewed.

**Prevention:**
1. Do not build a manual lookup table. Instead, run a clustering/grouping step on the actual genre tags in the dataset as part of the pipeline. Collect all unique genre tags, group them by common substrings (using pg_trgm similarity or simple Python string matching), and let the data determine the macro categories.
2. Use a two-pass approach: first collect all genre tags across all 3,022 artists, then define macro buckets based on frequency — the top 10-15 patterns in the actual data become the buckets, everything else becomes "Other."
3. Store both raw Spotify genres (as a JSONB array) and the derived macro genre per artist. This lets you re-bucket without re-pulling from Spotify.
4. A reasonable initial macro genre set for a general music library: Electronic, Hip-Hop/R&B, Rock/Indie, Pop, Classical/Jazz, Latin, World/Folk, Metal/Punk, Country, Other. Derive thresholds from the actual data rather than assuming.

**Detection (warning signs):**
- More than 20% of tracks classified as "Other" genre
- Genre bucket definitions exist only as constants in code (not derived from data)
- No `raw_genres` JSONB column alongside `macro_genre` string column

**Phase:** Data pipeline genre bucketing (Phase 1), with UI validation in Phase 2

---

## Moderate Pitfalls

---

### Pitfall 7: Spotify API Token Expiration During Long-Running Pagination

**What goes wrong:** Fetching audio features for 9,115 tracks at 100 per batch requires 92 API calls. Spotify access tokens expire after 3,600 seconds (1 hour). A pipeline that fetches in a tight loop finishes in ~5 minutes, but a pipeline that pauses between stages (fetch, process, enrich) can cross the 1-hour boundary, causing 401 errors mid-run.

**Prevention:**
1. Use the Client Credentials flow (no user scope needed for audio features on pre-known track IDs). Tokens are easy to refresh programmatically.
2. Implement a `SpotifyClient` wrapper class that tracks `token_expires_at` and auto-refreshes before each request batch, not after failure.
3. Never hard-code the token — always fetch fresh before the pipeline starts and monitor expiry.

**Detection (warning signs):** 401 errors appearing after 50+ minutes of pipeline runtime, not at the start.

**Phase:** Data pipeline (Phase 1)

---

### Pitfall 8: MusicBrainz "area" Field Is Not Always Origin Country

**What goes wrong:** MusicBrainz `area` on an artist entity represents the area associated with the artist, which may be their base of operations, their label's HQ city, or simply the area of the submitting editor's preference — not necessarily birth country or cultural origin. For bands, `begin_area` (formation location) often differs from `area`. For immigrant artists, `area` may reflect current residence.

**Prevention:**
1. Prefer `begin_area` for the formation/origin location when present. Fall back to `area` only if `begin_area` is absent.
2. For individual artists, `begin_area` = birthplace; for groups, `begin_area` = formation city. Both are more useful than `area` for the "where is this music from" question.
3. Map `begin_area` → country using MusicBrainz's area hierarchy (area → parent area → country). This requires traversing the area hierarchy, which may require an additional API call per artist. Cache the area-to-country mapping aggressively — there are only ~250 countries and a few thousand regions.

**Detection (warning signs):** Artists showing up in unexpected countries; cross-referencing 5 artists manually and finding 2+ wrong.

**Phase:** Data pipeline (Phase 1)

---

### Pitfall 9: PostgreSQL pg_trgm Index Not Used for Short Queries

**What goes wrong:** `pg_trgm` GIN indexes only activate for queries with 3+ character trigrams. Searching for "U2" or "PJ" returns a sequential scan on the full artists table, not an index scan. At 3,022 artists this is fast, but the behavior surprises developers who expect the index to always kick in.

**Prevention:**
1. This is acceptable at 3K artist scale — sequential scans of small tables are still sub-millisecond.
2. Document the limitation explicitly in the search service code as a comment. Do not add complexity (prefix indexes, etc.) to handle it.
3. Add a minimum search length of 2 characters in the frontend and a minimum of 1 character server-side with a fallback to `ILIKE '%query%'` for 1-2 character queries.

**Detection (warning signs):** Running `EXPLAIN ANALYZE` on a 2-character search query and seeing `Seq Scan`.

**Phase:** Search feature (Phase 2 or 3)

---

### Pitfall 10: Claude API Context Window Overflow for Large Music Libraries

**What goes wrong:** Naively stuffing all 9,115 tracks into a Claude API prompt to answer "what are my most common genres?" will exceed context limits and produce errors or truncated context. Even at 100 tokens per track, 9,115 tracks = ~900K tokens, exceeding Claude's practical useful context for this purpose.

**Why it happens:** RAG implementations often start by just sending all data because it's simpler. It works for small datasets, then breaks at scale.

**Prevention:**
1. Never send raw track data to Claude. Send pre-aggregated statistics only: top 20 countries by track count, top 30 genre buckets, summary stats (mean energy, danceability distribution), not individual track rows.
2. For natural language queries about specific artists or tracks, use PostgreSQL full-text search to retrieve relevant rows first (5-20 rows), then pass those rows as context.
3. Design the RAG context builder as an explicit step: `parse_question → determine_query_type → fetch_relevant_context(max_tokens=4000) → build_prompt → call_claude`. Never skip the context-limiting step.
4. Use Claude's token counting API to assert context size before sending — fail loudly in dev if context exceeds budget.

**Detection (warning signs):** API errors mentioning context length; response times > 30 seconds for simple aggregate questions.

**Phase:** AI chat feature (Phase 3)

---

### Pitfall 11: JSONB Genre Array Queries Miss Index Without Correct Operator

**What goes wrong:** Storing Spotify genres as `genres JSONB` (e.g., `["indie pop", "chamber pop", "art pop"]`) and querying with `WHERE genres::text ILIKE '%pop%'` is a full table cast and scan — no index is used. The GIN index on JSONB only activates with `@>`, `?`, or `?|` operators.

**Prevention:**
1. Use `genres @> '["indie pop"]'::jsonb` for exact-match genre filtering.
2. For fuzzy genre search (user types "pop", should match "indie pop", "chamber pop", etc.), use a separate `pg_trgm` index on a computed column or use the macro genre string column for filtering, not raw JSONB.
3. Create the GIN index at schema creation time: `CREATE INDEX idx_artists_genres ON artists USING GIN (genres)`.

**Detection (warning signs):** `EXPLAIN ANALYZE` showing `Seq Scan` + `Filter: (genres::text ~~...` on genre queries.

**Phase:** Database schema (Phase 1), query optimization (Phase 2)

---

## Minor Pitfalls

---

### Pitfall 12: Mapbox Token Exposure in Client Bundle

**What goes wrong:** `NEXT_PUBLIC_MAPBOX_TOKEN` is intentionally public-facing (required for client-side Mapbox GL JS), but using a token without URL restrictions means anyone who inspects the page source can use your token to make Mapbox API calls that bill to your account.

**Prevention:** Restrict the Mapbox public token to allowed URLs (your production domain + localhost) in the Mapbox dashboard. This is a 30-second configuration change that eliminates token abuse risk.

**Phase:** Pre-deployment (Phase 3)

---

### Pitfall 13: "Origin Country" vs "Current Country" Confusion in Data Model

**What goes wrong:** The schema stores `country_code` on the artist. But the concept "origin country" is ambiguous for individual artists (birthplace? nationality? cultural identity?) vs bands (formation city's country? label country?). Without a clear definition locked in early, the map shows inconsistent data — Rihanna might appear in USA (where her career is based) vs Barbados (where she was born).

**Prevention:** Encode the definition in the schema: column comment `-- MusicBrainz begin_area country: where artist/group was formed/born, not current residence`. Add this to the `artists` table DDL. The PROJECT.md already specifies the intent (origin = cultural roots), so execute on it at schema level.

**Phase:** Database schema (Phase 1)

---

### Pitfall 14: Missing Artists in Sidebar — Unresolved Countries Silently Ignored

**What goes wrong:** Artists without a resolved MusicBrainz country are supposed to appear in the sidebar. If the frontend filters on `country_code IS NOT NULL` and never renders the null case, these ~N artists simply vanish from the UI with no indication they exist. Users have no way to know their library has unresolved artists.

**Prevention:** Explicitly design the sidebar component for `country_code IS NULL` artists from the start. The API should have a dedicated endpoint `GET /api/artists/unresolved` returning paginated unresolved artists. The sidebar should show a count ("47 artists without origin data") that links to a list.

**Phase:** Frontend (Phase 2)

---

### Pitfall 15: Diversity Score Instability on Small Country Samples

**What goes wrong:** Shannon entropy normalized to 0-10 is mathematically unstable for countries with very few tracks (1-2 tracks). A library with 9,100 tracks from USA and 1 track each from 15 other countries scores very low on diversity despite technically having 16 countries represented. The normalized score can fluctuate significantly as pipeline adds/removes artists from edge-case countries.

**Prevention:** Apply a minimum threshold: only count countries with >= 3 tracks toward the Shannon entropy calculation. Countries with 1-2 tracks still appear on the map but don't contribute to the diversity score. Document this threshold clearly in the UI tooltip.

**Phase:** Analytics calculation (Phase 1-2)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| MusicBrainz enrichment pipeline | Wrong artist disambiguation (Pitfall 1) | Cross-reference Spotify genres + manual override table |
| MusicBrainz enrichment pipeline | Pipeline non-idempotency (Pitfall 2) | `mb_resolution_status` column + upsert pattern |
| Spotify audio features fetch | Endpoint deprecation (Pitfall 3) | Verify endpoint access before writing pipeline code |
| Spotify audio features fetch | Token expiration mid-pipeline (Pitfall 7) | Auto-refresh wrapper with `expires_at` tracking |
| Genre bucketing | Flat tag list unusability (Pitfall 6) | Data-driven bucketing from actual tag frequency |
| Database schema | JSONB index not used (Pitfall 11) | GIN index + correct operator selection |
| Frontend map | Individual markers at scale (Pitfall 4) | GeoJSON source + circle layer, never HTML markers |
| Frontend map interactions | Click/hover conflicts (Pitfall 5) | Layer-scoped event handlers, ref-based hover state |
| Frontend map | Mapbox token billing risk (Pitfall 12) | URL-restrict token in Mapbox dashboard |
| Search feature | pg_trgm short query fallback (Pitfall 9) | Minimum length + ILIKE fallback for 1-2 chars |
| AI chat | Context window overflow (Pitfall 10) | Pre-aggregate data, RAG with 5-20 row context |
| Analytics | Diversity score instability (Pitfall 15) | Minimum 3-track threshold for Shannon entropy |
| UI completeness | Unresolved artists disappear (Pitfall 14) | Explicit sidebar design + `/api/artists/unresolved` endpoint |

---

## Sources

**Confidence levels:**

| Pitfall | Confidence | Basis |
|---------|------------|-------|
| MusicBrainz disambiguation (1) | HIGH | Well-documented MusicBrainz search API behavior; widely reported in developer forums |
| Pipeline idempotency (2) | HIGH | Standard data engineering pattern; applicable to any rate-limited pipeline |
| Spotify audio features deprecation (3) | LOW | Restriction announced mid-2024 per training data; current status requires verification at official Spotify developer docs |
| Mapbox HTML markers at scale (4) | HIGH | Documented in Mapbox official performance guides; confirmed pattern |
| Mapbox interaction conflicts (5) | HIGH | Documented Mapbox GL JS behavior with queryRenderedFeatures |
| Genre classification (6) | HIGH | Spotify genre data characteristics are well-documented and stable |
| Token expiration (7) | HIGH | Spotify OAuth spec; 3600-second expiry is documented |
| MusicBrainz area vs begin_area (8) | MEDIUM | MusicBrainz data model docs; area semantics can vary by contributor |
| pg_trgm short query (9) | HIGH | PostgreSQL documentation on trigram minimum length |
| Claude context window (10) | HIGH | Anthropic documentation; consistent behavior across Claude versions |
| JSONB GIN index operator (11) | HIGH | PostgreSQL JSONB documentation |
| Mapbox token exposure (12) | HIGH | Mapbox dashboard documentation |
| Origin country ambiguity (13) | HIGH | MusicBrainz data model documentation |
| Unresolved artists UI (14) | HIGH | Standard data completeness UX pattern |
| Diversity score instability (15) | HIGH | Shannon entropy mathematical properties |

**Official sources to verify before Phase 1:**
- Spotify audio features endpoint status: https://developer.spotify.com/documentation/web-api/reference/get-audio-features
- MusicBrainz rate limiting: https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- MusicBrainz artist entity fields (area vs begin_area): https://musicbrainz.org/doc/Artist
- Mapbox GL JS performance guide: https://docs.mapbox.com/mapbox-gl-js/guides/performance/
