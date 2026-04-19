# Requirements: SoundAtlas

**Defined:** 2026-04-18
**Core Value:** Interactive world map that instantly reveals the geographic diversity of a music library

## v1.1 Requirements

Requirements for v1.1 Polish & Deploy. Each maps to roadmap phases.

### UI Polish

- [ ] **UI-01**: All text properly contained within its parent containers (no overflow/clipping)
- [ ] **UI-02**: StatsSidebar visually refined — clean spacing, typography hierarchy, polished metrics cards
- [ ] **UI-03**: CountryPanel visually refined — better section spacing, artist rows, genre chart labels not clipped
- [ ] **UI-04**: Pie chart labels don't overlap on small slices
- [ ] **UI-08**: Top tracks display shows correct distinct info per line (no duplicate track name as album text)
- [ ] **UI-05**: SearchBar dropdown styled consistently with overall polish level
- [ ] **UI-06**: Map tooltip styling refined (spacing, typography, visual hierarchy)
- [ ] **UI-07**: Overall visual consistency — unified spacing, borders, shadows, and transitions across all panels

### Audio Features

- [ ] **AF-01**: Audio features section hidden when no data exists for the selected country
- [ ] **AF-02**: Audio features section displays correctly when data is available (no "currently unavailable")

### Diversity Score

- [ ] **DIV-01**: Diversity score includes clear explanation of what it measures and how
- [ ] **DIV-02**: Diversity score uses friendlier framing (e.g., contextual labels, what drives it)

### AI Chat

- [ ] **CHAT-01**: AI chat panel can be expanded to a larger/fullscreen view
- [ ] **CHAT-02**: Expanded chat view is easy to dismiss back to the sidebar size

### Deployment

- [ ] **DEPLOY-01**: Frontend deployed to Vercel and accessible via public URL
- [ ] **DEPLOY-02**: Backend, PostgreSQL, and Redis deployed to Railway
- [ ] **DEPLOY-03**: Environment configured for production (CORS, API URLs, secrets)
- [ ] **DEPLOY-04**: App loads and functions correctly in production

## v2.0 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Multi-User

- **USER-01**: User can sign in with Spotify OAuth
- **USER-02**: User's library is automatically imported after OAuth
- **USER-03**: Each user sees their own map with their own data
- **USER-04**: User can share a link to their map

### Re-Sync

- **SYNC-01**: User can manually trigger a re-sync to update with new liked songs

## Out of Scope

| Feature | Reason |
|---------|--------|
| Spotify OAuth login | Deferred to v2.0 — polish and deploy single-user first |
| Multi-user support | Deferred to v2.0 — requires significant architecture changes |
| Mobile responsiveness | Not required for v1.1 — desktop-first for personal website |
| Lyric search (ChromaDB) | P2 priority, deferred |
| Streaming history integration | Library-only for clean signal |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 7 | Pending |
| UI-02 | Phase 7 | Pending |
| UI-03 | Phase 7 | Pending |
| UI-04 | Phase 7 | Pending |
| UI-05 | Phase 7 | Pending |
| UI-06 | Phase 7 | Pending |
| UI-07 | Phase 7 | Pending |
| UI-08 | Phase 7 | Pending |
| AF-01 | Phase 8 | Pending |
| AF-02 | Phase 8 | Pending |
| DIV-01 | Phase 8 | Pending |
| DIV-02 | Phase 8 | Pending |
| CHAT-01 | Phase 8 | Pending |
| CHAT-02 | Phase 8 | Pending |
| DEPLOY-01 | Phase 9 | Pending |
| DEPLOY-02 | Phase 9 | Pending |
| DEPLOY-03 | Phase 9 | Pending |
| DEPLOY-04 | Phase 9 | Pending |

**Coverage:**
- v1.1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-04-18*
*Last updated: 2026-04-18 after v1.1 roadmap creation*
