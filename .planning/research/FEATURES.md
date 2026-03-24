# Feature Landscape

**Domain:** Personal music analytics + geographic visualization platform
**Project:** SoundAtlas
**Researched:** 2026-03-24
**Confidence:** MEDIUM — Training data knowledge of Spotify Wrapped, Last.fm, Obscurify, Stats for Spotify,
Receiptify confirmed against project context. WebSearch/WebFetch unavailable; findings based on training
data (cutoff August 2025). Flag any rapidly-evolving competitor features for validation.

---

## Reference Platforms Surveyed

| Platform | Core Value | Confidence |
|----------|-----------|------------|
| Spotify Wrapped | Annual top artists/tracks/genres, shareable stories | HIGH (widely documented) |
| Last.fm | Continuous scrobble tracking, social charts, listening history | HIGH (stable platform) |
| Obscurify | Obscurity score, taste comparison | MEDIUM (training data only) |
| Stats for Spotify (statsforspotify.com) | Top artists/tracks by time range, audio feature radar | MEDIUM (training data only) |
| Receiptify | Playlist/listening stats as a receipt PNG, shareable image | MEDIUM (training data only) |
| Music-Map / Every Noise at Once | Genre geography, artist similarity mapping | MEDIUM (training data only) |
| Chartmetric / Soundcharts | Professional geographic streaming analytics | MEDIUM (enterprise-focused) |

---

## Table Stakes

Features users of music analytics tools expect. Missing = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Top artists list | Every music stats tool shows this; baseline orientation | Low | SoundAtlas has this per-country in detail panel |
| Top tracks list | Paired with top artists; expected at both global and filtered level | Low | Needed at global level and per-country |
| Genre distribution visualization | Users want to understand their taste profile at a glance | Medium | Pie chart per country already planned; global breakdown needed |
| Total library count | "How many songs do I have?" is the first question | Low | Show 9,115 liked tracks prominently |
| Artist count | Pairs with track count to convey breadth | Low | 3,022 artists should be surfaced |
| Interactive map with country markers | The core screen — absence breaks the whole product | High | Mapbox + sized/colored markers already planned |
| Country click → detail view | Users clicking a country expect drilldown; no drilldown = broken UX | Medium | Right panel already planned |
| Country name + track count in tooltip/marker | Users need to know what they're hovering before clicking | Low | Tooltip on Mapbox marker |
| Responsive feedback on map interaction | Hover states, selection states, click animations | Low | CSS + Mapbox layer styling |
| Loading state | 9K tracks → data loads asynchronously; spinners/skeletons expected | Low | React loading states |
| Error state | Network failures, empty data; graceful degradation expected | Low | Error boundary components |
| Search / filter (at minimum by artist name) | Users look for specific artists; no search = frustration | Medium | pg_trgm fuzzy search already planned |
| Global stats summary | High-level numbers before drilling down (top country, diversity score, total countries) | Low | Sidebar already planned |

---

## Differentiators

Features that set SoundAtlas apart from existing tools. Not baseline expected, but highly valued when present.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Geographic origin mapping (not streaming location) | No competitor shows WHERE artists are FROM; Spotify shows where you stream, not cultural roots. Rihanna = Barbados, not US | High | Core thesis of SoundAtlas; MusicBrainz origin data is the moat |
| Geographic diversity score (Shannon entropy) | Single number capturing how globally diverse your taste is — quotable, shareable, conversation-starting | Medium | Shannon entropy 0–10 already planned; display prominently |
| Audio feature comparison by country | Energy/danceability/valence/tempo profiles per country — "My Brazilian music is X% more danceable than my German music" | High | Recharts bar/radar charts; genuinely novel insight |
| Continent-level aggregate view | Zoom out from country → see listening across continents | Medium | Requires continent grouping logic; adds spatial hierarchy |
| Genre-per-country color encoding on map | Visual encoding where color = dominant genre immediately reveals taste geography | Medium | Already planned; rare in competitors |
| AI natural language music exploration | "What's the most energetic country in my library?" — conversational exploration of personal data | High | Claude API + RAG already planned; no competitor has this |
| Cross-country audio feature comparisons | Side-by-side comparison of audio feature profiles between two selected countries | Medium | Extend detail panel with comparison mode |
| "Your most underrepresented continent" insight | Surfaces blind spots in listening geography — novel framing | Low | Computed metric from existing data |
| Decade-of-release breakdown per country | Shows whether you listen to contemporary vs classic artists by region | Medium | Requires track release year data (available via Spotify API) |
| Top tracks per country with preview | Hearing the music, not just reading names, creates an "aha" moment | High | Spotify 30-second preview API; significant UX uplift but adds complexity |
| Genre evolution over library age | When did you start listening to music from X country? | High | Requires added_at timestamp from Spotify liked songs data |

---

## Anti-Features

Features to explicitly NOT build in SoundAtlas v1, with rationale.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| User authentication / OAuth login | Single-user personal tool; auth adds weeks of work for zero v1 value; ships pre-loaded | Ship with pre-loaded personal data; note "clone and run locally" in README |
| Multi-user support / social features | Scope creep; Last.fm already owns social music; SoundAtlas is personal intelligence | Serve one user excellently; multi-user is a v3+ consideration |
| Real-time Spotify sync | Webhook/polling complexity; liked songs don't change hourly | Manual re-sync button is sufficient; auto-sync is a future enhancement |
| Streaming history analysis (104K plays) | Noisy signal; library = deliberate curation; play counts bias toward recently released; feature parity with Last.fm you'll lose | Library-only keeps signal clean; stream history is out of scope |
| Music recommendations engine | Spotify already does this better; recommendation adds ML complexity without geographic insight value | Surface geographic discovery instead ("Artists from Colombia you don't have yet" is future scope) |
| Shareable image exports (Receiptify-style) | Nice to have but pure vanity feature; no v1 discovery or insight value | Deferred to v2 if there's demand |
| Lyric search (ChromaDB/LyricLens) | P2 already in scope as deferred; ChromaDB adds infrastructure complexity | Keep deferred per project decision |
| Play count / listening time stats | Liked songs export has no play count; inferring from 104K history events is a separate pipeline | Don't approximate; present what you have cleanly |
| Artist biography / news feed | Content aggregation adds API dependencies and is done better by dedicated apps | Link to artist Spotify page instead |
| Mobile app or PWA push notifications | Personal web tool; mobile is not the primary use case | Web-first; responsive layout is sufficient |
| Playlist creation from map selections | Writing back to Spotify requires OAuth and write scopes | Read-only for v1; playlist creation is a future feature |

---

## Feature Dependencies

```
Map render (Mapbox markers)
  → Country markers sized by track count         [requires: country → track count aggregation]
  → Country markers colored by dominant genre    [requires: genre bucketing logic]

Country detail panel
  → Artist list                                  [requires: country → artist mapping]
  → Genre pie chart                              [requires: genre assignment per track]
  → Audio feature comparison chart               [requires: audio features in PostgreSQL]
  → Top tracks list                              [requires: track → country join]

Global stats sidebar
  → Diversity score                              [requires: country distribution + Shannon entropy]
  → Top countries list                           [requires: country → track count aggregation]
  → Genre distribution global                   [requires: genre bucketing across all tracks]
  → Total artists / tracks counts               [requires: database population]

AI chat panel
  → Natural language queries                    [requires: Claude API + RAG context from PostgreSQL]
  → Country comparison answers                  [requires: audio features + country mapping]
  → Diversity insights                          [requires: diversity score + global stats]

Search (fuzzy artist/track)
  → Search results                              [requires: pg_trgm index on artists + tracks]
  → Click result → navigate to country          [requires: artist → country mapping]

Data pipeline (upstream of all features)
  → Spotify data export ingestion               [no upstream dependency]
  → Spotify API audio features enrichment       [requires: track URIs from export]
  → MusicBrainz origin country lookup           [requires: artist names/MBIDs]
  → Genre bucketing                             [requires: Spotify API genre tags]
  → Database population                         [requires: all pipeline steps complete]
```

---

## MVP Recommendation

For a personal tool that delivers the core value proposition immediately, prioritize:

**Must ship (table stakes + core differentiator):**
1. Interactive Mapbox world map with sized + colored country markers
2. Country detail panel (artist list, genre pie chart, audio feature charts, top tracks)
3. Global stats sidebar (diversity score, top countries, genre distribution, totals)
4. Fuzzy search by artist name (pg_trgm already planned)
5. Data pipeline seeding all ~3K artists with origin countries

**High value differentiator to include in v1:**
6. AI chat panel with RAG — this is the feature no competitor has and elevates SoundAtlas from "pretty map" to "music intelligence platform"
7. Geographic diversity score displayed prominently in sidebar — the single most quotable output of the platform

**Defer to v2:**
- Continent-level aggregate view (Medium complexity, can add without breaking existing UI)
- Cross-country audio feature comparison mode (Extend detail panel)
- Decade-of-release breakdown (Requires additional API enrichment)
- Shareable image exports
- Lyric search (already scoped as P2)

---

## Competitive Positioning

| Dimension | Spotify Wrapped | Last.fm | Stats for Spotify | SoundAtlas |
|-----------|----------------|---------|-------------------|------------|
| Geographic origin of artists | No | No | No | **Yes — core feature** |
| Audio feature breakdown | Partial (annual) | No | Yes (radar chart) | Yes (per country) |
| AI natural language exploration | No | No | No | **Yes — differentiator** |
| Geographic diversity score | No | No | No | **Yes — unique metric** |
| Shareable / social | Yes (core) | Yes | Partial | No (out of scope v1) |
| Continuous tracking | No (annual) | Yes | Yes | No (library snapshot) |
| Personal data ownership | No | Partial | No (OAuth session) | **Yes — local/self-hosted** |

SoundAtlas occupies an uncontested niche: **geographic cultural intelligence** about personal music taste.
No competitor answers "Where in the world does my music come from?" with artist-origin accuracy.

---

## Sources

- Spotify Wrapped feature set: Training data (HIGH confidence — extensively documented publicly)
- Last.fm feature set: Training data (HIGH confidence — stable platform since 2002)
- Stats for Spotify (statsforspotify.com) feature set: Training data (MEDIUM confidence — verify current feature set)
- Obscurify feature set: Training data (MEDIUM confidence — small indie tool, may have changed)
- Receiptify feature set: Training data (MEDIUM confidence — verify current features)
- Every Noise at Once / Music-Map: Training data (MEDIUM confidence)
- Chartmetric geographic analytics: Training data (MEDIUM confidence — enterprise product)
- SoundAtlas project context: `.planning/PROJECT.md` (HIGH confidence)
- WebSearch / WebFetch: UNAVAILABLE — all findings from training data; validate competitor features before finalizing roadmap
