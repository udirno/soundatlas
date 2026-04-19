# Roadmap: SoundAtlas

## Milestones

- **v1.0 MVP** — Phases 1-6 (shipped 2026-03-25) — [Full details](milestones/v1.0-ROADMAP.md)
- **v1.1 Polish & Deploy** — Phases 7-9 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-6) — SHIPPED 2026-03-25</summary>

- [x] Phase 1: Infrastructure and Pipeline Foundation (3/3 plans) — completed 2026-03-24
- [x] Phase 2: Data Enrichment Pipeline (3/3 plans) — completed 2026-03-25
- [x] Phase 3: Backend API (4/4 plans) — completed 2026-03-24
- [x] Phase 4: Map View and Country Detail (3/3 plans) — completed 2026-03-25
- [x] Phase 5: Global Stats and Search (2/2 plans) — completed 2026-03-25
- [x] Phase 6: AI Chat (2/2 plans) — completed 2026-03-25

</details>

### v1.1 Polish & Deploy (In Progress)

**Milestone Goal:** Fix UX rough edges and deploy to production so friends can view the map.

- [x] **Phase 7: Visual Polish** — All UI panels clean + audio features/diversity score fixed — completed 2026-04-18
- [ ] **Phase 8: Feature Polish** — Chat panel expand/collapse (AF + DIV requirements completed in Phase 7)
- [ ] **Phase 9: Production Deployment** — App live on Vercel and Railway

---

### Phase 7: Visual Polish

**Goal:** Every panel looks clean, readable, and visually consistent
**Depends on:** Phase 6 (v1.0 complete)
**Requirements:** UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08
**Success Criteria** (what must be TRUE):
  1. All text in every panel is fully visible — no overflow, no clipping, no truncation
  2. StatsSidebar cards have consistent spacing and clear typography hierarchy
  3. CountryPanel sections are well-spaced, artist rows scannable, genre chart labels readable
  4. Pie chart slices never show overlapping labels, even for small slices
  5. SearchBar dropdown, map tooltips, and panel borders share a unified visual style
  6. Top tracks show correct distinct data per line (track name and album name, not duplicated)
**Plans:** 1 plan

Plans:
- [ ] 07-01-PLAN.md — Fix class conflicts, pie label overlap, top tracks dedup, tooltip hierarchy, search focus ring

---

### Phase 8: Feature Polish

**Goal:** Audio features display conditionally, diversity score communicates meaning, and chat panel is expandable
**Depends on:** Phase 7
**Requirements:** CHAT-01, CHAT-02 (AF-01, AF-02, DIV-01, DIV-02 completed in Phase 7)
**Success Criteria** (what must be TRUE):
  1. Selecting a country with no audio feature data shows no audio features section — the section is absent, not a placeholder
  2. Selecting a country with audio feature data shows the radar chart with correct values and no error state
  3. Diversity score includes a label or description explaining what it measures and what a high or low score means
  4. Chat panel has an expand control that opens it to a larger or fullscreen view for comfortable reading
  5. Expanded chat view has a visible close/collapse control that returns it to its default sidebar size
**Plans:** TBD

Plans:
- [ ] 08-01: Audio features conditional rendering and diversity score redesign
- [ ] 08-02: AI chat panel expand/collapse implementation

---

### Phase 9: Production Deployment

**Goal:** App is live on public URLs with production configuration and fully functional end-to-end
**Depends on:** Phase 8
**Requirements:** DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. Visiting the Vercel URL shows the map immediately — no login, no loading errors
  2. Clicking a country opens the detail panel with real data from the Railway-hosted database
  3. The AI chat panel sends a message and receives a response from the Railway-hosted backend
  4. Production environment has no secrets in code — all API keys and connection strings are environment variables
**Plans:** TBD

Plans:
- [ ] 09-01: Railway backend, PostgreSQL, and Redis deployment
- [ ] 09-02: Vercel frontend deployment and production environment wiring

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Infrastructure | v1.0 | 3/3 | Complete | 2026-03-24 |
| 2. Data Enrichment | v1.0 | 3/3 | Complete | 2026-03-25 |
| 3. Backend API | v1.0 | 4/4 | Complete | 2026-03-24 |
| 4. Map View | v1.0 | 3/3 | Complete | 2026-03-25 |
| 5. Stats and Search | v1.0 | 2/2 | Complete | 2026-03-25 |
| 6. AI Chat | v1.0 | 2/2 | Complete | 2026-03-25 |
| 7. Visual Polish | v1.1 | 1/1 | Complete | 2026-04-18 |
| 8. Feature Polish | v1.1 | 0/TBD | Not started | — |
| 9. Production Deployment | v1.1 | 0/TBD | Not started | — |
