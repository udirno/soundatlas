# Phase 5: Global Stats and Search - Research

**Researched:** 2026-03-25
**Domain:** Next.js 14 / React 18 UI components — sidebar analytics panel, debounced search with autocomplete, Mapbox imperative fly-to
**Confidence:** HIGH

---

## Summary

Phase 5 is a pure frontend phase. Both backend endpoints are already built and tested (`GET /api/analytics/dashboard` and `GET /api/search?q=`). The work consists of three distinct UI concerns wired together through `HomeClient`'s shared state:

1. A `StatsSidebar` component that fetches once on mount and displays global analytics.
2. A `SearchBar` component (likely in the header area or overlaid on the map) that debounces keystrokes, calls the search endpoint, renders a dropdown of results, and handles selection.
3. Map imperative navigation: when a search result is selected, `MapView` must `flyTo` the country coordinates and `HomeClient` must set `selectedCountryId` to open the detail panel.

**The single largest gap:** `SearchArtistHit` and `SearchTrackHit` in the backend schema do NOT return `country_id`. SRCH-02 requires flying the map to the artist's origin country. The backend search service must be updated to include `country_id` on artist hits and `artist.country_id` via join on track hits. This is a required backend change before the frontend can implement SRCH-02.

**Primary recommendation:** Extend `SearchArtistHit` to include `country_id: Optional[int]`, extend `SearchTrackHit` to include `country_id: Optional[int]` (resolved via `Track → Artist → country_id`), then build the frontend components against those extended types.

---

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.3.1 | Component state, hooks | Already in project |
| Next.js | 14.2.15 | App router, client components | Already in project |
| Tailwind CSS | 3.4.13 | Utility styling | Already in project |
| mapbox-gl | 3.20.0 | Map imperative API | Already in project |
| Recharts | 3.8.0 | Optional — could use for stat bars | Already in project |

### No New Dependencies Required
All functionality can be built with:
- Native React `useState` / `useEffect` / `useRef` — for debounce, loading, dropdown state
- Native `fetch` via `api.ts` helper pattern — for analytics and search
- Tailwind — for all UI styling
- Mapbox GL JS imperative API (already imported in MapView) — for `flyTo`

**No new npm packages are needed for this phase.**

**Installation:**
```bash
# Nothing to install — all dependencies are present
```

---

## Architecture Patterns

### Recommended Project Structure (additions only)
```
frontend/src/
├── components/
│   ├── StatsSidebar.tsx     # New: global analytics panel (left side)
│   ├── SearchBar.tsx        # New: debounced search + autocomplete dropdown
│   ├── HomeClient.tsx       # Modified: add statsData state, search handler, flyTo ref
│   └── MapView.tsx          # Modified: expose flyTo via imperative ref or prop callback
├── lib/
│   └── api.ts               # Modified: add fetchDashboard(), fetchSearch() + new types
```

### Pattern 1: Lifting Map Navigation to HomeClient

`MapView` currently manages the map imperatively inside its own `useEffect`. To fly programmatically from a search selection, `HomeClient` needs a way to call `map.current.flyTo(...)`.

**Standard approach:** Pass a ref callback or use `useImperativeHandle`.

```typescript
// Source: React docs — useImperativeHandle + forwardRef
// In MapView.tsx
import { forwardRef, useImperativeHandle } from 'react';

export interface MapViewHandle {
  flyTo: (lng: number, lat: number, zoom?: number) => void;
}

const MapView = forwardRef<MapViewHandle, MapViewProps>(({ countries, onCountrySelect }, ref) => {
  const map = useRef<mapboxgl.Map | null>(null);

  useImperativeHandle(ref, () => ({
    flyTo(lng: number, lat: number, zoom = 4) {
      map.current?.flyTo({ center: [lng, lat], zoom, duration: 1200 });
    },
  }));
  // ... rest unchanged
});
```

```typescript
// In HomeClient.tsx
const mapRef = useRef<MapViewHandle>(null);

function handleSearchSelect(countryId: number, lng: number, lat: number) {
  mapRef.current?.flyTo(lng, lat);
  setSelectedCountryId(countryId);
}
```

**Alternative (simpler):** Add `flyToTarget` prop of type `{ lng: number; lat: number } | null` to `MapView`, trigger flyTo in a `useEffect` watching that prop. This avoids `forwardRef` complexity at the cost of slightly indirect signaling. Either approach works; `useImperativeHandle` is more explicit for imperative actions.

### Pattern 2: Debounced Search with Inline Dropdown

```typescript
// Source: Standard React debounce pattern (no library needed)
const [query, setQuery] = useState('');
const [results, setResults] = useState<SearchResult | null>(null);
const [isOpen, setIsOpen] = useState(false);

useEffect(() => {
  if (!query.trim()) {
    setResults(null);
    return;
  }
  const timer = setTimeout(async () => {
    const data = await fetchSearch(query);
    setResults(data);
    setIsOpen(true);
  }, 300);
  return () => clearTimeout(timer);
}, [query]);
```

**Debounce delay:** 300ms is the standard for search-as-you-type. Less is too aggressive for network calls; more feels sluggish.

### Pattern 3: StatsSidebar Data Fetch

The dashboard endpoint returns all stats in one call. Fetch once on mount in `StatsSidebar` using the established component pattern:

```typescript
// Pattern matches existing CountryPanel and HomeClient patterns
const [stats, setStats] = useState<DashboardStats | null>(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  fetchDashboard()
    .then(setStats)
    .catch(err => console.error('Failed to fetch dashboard stats:', err))
    .finally(() => setLoading(false));
}, []);
```

### Pattern 4: Diversity Score Display (0–10 scale)

The backend `diversity_score` is a float in `[0, 1]` (Shannon entropy normalized to max entropy). The requirement says display on 0–10 scale. Multiply by 10 and round to one decimal place in the frontend:

```typescript
const displayScore = (stats.diversity_score * 10).toFixed(1);
```

**Do not change the backend** — the 0–1 value is the canonical representation; the 0–10 scale is a presentation concern.

### Pattern 5: "Not in your library" for Track Hits

`SearchTrackHit` already has `in_library: bool`. When `in_library === false`, show "Not in your library" instead of navigating. Artists always exist in the library by definition (they only appear if they have tracks), so the not-in-library message applies only to track hits where `in_library` is false.

### Anti-Patterns to Avoid

- **Fetching analytics from `page.tsx` (server component) and passing as prop:** The stats are client-interactive (potential refresh) — keep them in `StatsSidebar` via `useEffect`. Consistent with how `CountryPanel` fetches its own data.
- **Calling `flyTo` directly from `SearchBar`:** `SearchBar` should not hold a map reference. Bubble the selection event up to `HomeClient` via callback prop, then `HomeClient` calls `mapRef.current.flyTo(...)`.
- **Showing the dropdown while `query` is empty:** Guard the dropdown on `query.trim().length > 0`.
- **No loading state in search dropdown:** Show a spinner or "Searching..." text during the async call — prevents empty flicker.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debounce | Custom debounce class | `setTimeout` + `clearTimeout` in `useEffect` cleanup | This is the canonical React pattern; no library needed for a single use case |
| Fuzzy matching | Client-side fuzzy search | Backend `pg_trgm` via `GET /api/search?q=` | Already built, GIN indexed, threshold tuned |
| Diversity calculation | Frontend Shannon entropy | Backend `diversity_score` field | Already computed and normalized |
| Dropdown positioning | Absolute positioning math | Tailwind `absolute top-full left-0 z-50 w-full` | Simple CSS is sufficient |

**Key insight:** The backend has already solved all the hard algorithmic problems. Frontend work is pure UI composition and event wiring.

---

## Critical Gap: Backend Schema Extension Required

**This is the most important finding in this research.**

The `SearchArtistHit` schema does NOT include `country_id`:

```python
# Current backend/app/schemas/search.py
class SearchArtistHit(BaseModel):
    id: int
    name: str
    spotify_id: Optional[str] = None
    genres: Optional[list[str]] = None
    image_url: Optional[str] = None
    score: float
    # MISSING: country_id: Optional[int]
```

SRCH-02 requires "flies the map to that artist's origin country." Without `country_id` in the search result, the frontend cannot resolve which country to fly to or which `selectedCountryId` to set.

Similarly, `SearchTrackHit` has no `country_id`. A track's country must be resolved through its artist: `Track → Artist.country_id`.

**Required backend changes (one task):**

1. Add `country_id: Optional[int]` to `SearchArtistHit`
2. Add `country_id: Optional[int]` to `SearchTrackHit`
3. Update `search_service.fuzzy_search` to select `Artist.country_id` in the artist query and join `Track → Artist` to get `Artist.country_id` in the track query

```python
# Updated artist query — add Artist.country_id to SELECT
artist_stmt = (
    select(
        Artist.id,
        Artist.name,
        Artist.spotify_id,
        Artist.genres,
        Artist.image_url,
        Artist.country_id,          # ADD THIS
        func.similarity(Artist.name, q).label("score"),
    )
    ...
)

# Updated track query — join Artist to get country_id
track_stmt = (
    select(
        Track.id,
        Track.name,
        Track.spotify_id,
        Track.album_name,
        Artist.country_id,          # ADD THIS via join
        func.similarity(Track.name, q).label("score"),
        in_library_subq.label("in_library"),
    )
    .join(Artist, Track.artist_id == Artist.id, isouter=True)  # LEFT JOIN — artist_id is nullable
    .where(func.similarity(Track.name, q) > SIMILARITY_THRESHOLD)
    ...
)
```

Additionally, the frontend needs `CountryListItem` data (latitude/longitude) to perform the `flyTo`. Two options:

**Option A (simpler):** `HomeClient` already has `countries: CountryListItem[]` passed from `page.tsx`. When a search result returns `country_id`, look up coordinates from the existing `countries` array: `countries.find(c => c.id === result.country_id)`. No extra API call needed.

**Option B:** Fetch country detail in the search selection handler. More expensive and slower.

**Use Option A** — the `countries` array is already available in `HomeClient`.

---

## Common Pitfalls

### Pitfall 1: MapView `flyTo` Before Map Fully Loaded
**What goes wrong:** Calling `map.current.flyTo(...)` before the `map.current.on('load', ...)` callback fires causes a silent no-op or error.
**Why it happens:** Map initialization is async. The `useImperativeHandle` ref is set on the React component mount, but the Mapbox map may not be loaded yet.
**How to avoid:** In the `flyTo` imperative method, check `map.current?.loaded()` before calling. If not loaded, store the target and trigger on load.
**Warning signs:** Map does not move after search selection during initial page load.

### Pitfall 2: Search Dropdown Z-Index Conflicts
**What goes wrong:** The autocomplete dropdown appears behind the Mapbox canvas (which has its own stacking context).
**Why it happens:** Mapbox's canvas element creates a new stacking context. A `z-50` dropdown inside the map container may be clipped.
**How to avoid:** Place `SearchBar` in `HomeClient` at the same DOM level as `MapView`, not nested inside it. Render the dropdown with `position: fixed` or a portal, or ensure the search container is a sibling of (not a child of) the map container.
**Warning signs:** Dropdown renders but is invisible or partially hidden.

### Pitfall 3: Stats Sidebar Overlapping CountryPanel
**What goes wrong:** If `StatsSidebar` is fixed on the left and `CountryPanel` is fixed on the right, they coexist fine. But if both are right-side panels, one will hide the other.
**Why it happens:** `CountryPanel` is `fixed top-0 right-0 w-96`. A stats sidebar must be on the **left** side.
**How to avoid:** Place `StatsSidebar` as `fixed top-0 left-0 h-screen w-72` (or similar) — mirroring CountryPanel on the opposite side.
**Warning signs:** One panel disappears when the other opens.

### Pitfall 4: `useImperativeHandle` Requires `forwardRef` Wrapper
**What goes wrong:** TypeScript error when trying to attach a ref to a function component without `forwardRef`.
**Why it happens:** React does not allow refs on function components unless wrapped with `forwardRef`.
**How to avoid:** Wrap `MapView` with `forwardRef<MapViewHandle, MapViewProps>` before using `useImperativeHandle`. Update the `dynamic()` import type accordingly.
**Warning signs:** TS error "cannot assign a ref to a function component" or ref is always null.

### Pitfall 5: Dynamic Import Type with forwardRef
**What goes wrong:** After wrapping `MapView` with `forwardRef`, the dynamic import in `HomeClient` may lose the ref forwarding capability.
**Why it happens:** `next/dynamic` wraps the component in a loader; refs may not forward through the dynamic wrapper automatically.
**How to avoid:** Assign the result of `dynamic()` to a typed variable, or use the `flyToTarget` prop pattern instead of `forwardRef` to avoid this complexity entirely.
**Warning signs:** `mapRef.current` is always null despite component being mounted.

### Pitfall 6: Search Results for Tracks Without Country
**What goes wrong:** A track hit returns `country_id: null` (artist has no country mapping). Clicking it tries to fly to undefined coordinates.
**Why it happens:** Artist enrichment may have failed for some artists — `country_id` is nullable.
**How to avoid:** In the search selection handler, check `country_id !== null` before calling `flyTo`. If `country_id` is null, show a toast or inline message "Country not mapped for this artist."
**Warning signs:** `map.flyTo` called with `undefined` coordinates, map flies to [0, 0].

---

## Code Examples

Verified patterns from existing codebase:

### Adding fetchDashboard and fetchSearch to api.ts

```typescript
// Source: Pattern from existing fetchCountries / fetchCountryDetail
export interface DashboardStats {
  country_count: number;
  artist_count: number;
  track_count: number;
  diversity_score: number;  // 0–1, display as *10 for 0–10 scale
  top_genres: Array<{ genre: string; count: number }>;
  top_countries: Array<{ id: number; name: string; iso_alpha2: string; artist_count: number }>;
}

export interface SearchArtistHit {
  id: number;
  name: string;
  spotify_id: string | null;
  genres: string[] | null;
  image_url: string | null;
  score: number;
  country_id: number | null;  // Added in backend extension
}

export interface SearchTrackHit {
  id: number;
  name: string;
  spotify_id: string | null;
  album_name: string | null;
  score: number;
  in_library: boolean;
  country_id: number | null;  // Added in backend extension
}

export interface SearchResult {
  query: string;
  artists: SearchArtistHit[];
  tracks: SearchTrackHit[];
}

export async function fetchDashboard(): Promise<DashboardStats> {
  const res = await fetch(`${getBaseUrl()}/api/analytics/dashboard`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to fetch dashboard: ${res.status}`);
  return res.json() as Promise<DashboardStats>;
}

export async function fetchSearch(q: string): Promise<SearchResult> {
  const res = await fetch(
    `${getBaseUrl()}/api/search?q=${encodeURIComponent(q)}`,
    { cache: 'no-store' }
  );
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json() as Promise<SearchResult>;
}
```

### HomeClient with Stats + Search Integration

```typescript
// Source: Extrapolated from existing HomeClient.tsx pattern
'use client';

import { useState, useRef } from 'react';
import dynamic from 'next/dynamic';
import type { CountryListItem } from '@/lib/api';
import CountryPanel from './CountryPanel';
import StatsSidebar from './StatsSidebar';
import SearchBar from './SearchBar';

const MapView = dynamic(() => import('@/components/MapView'), {
  ssr: false,
  loading: () => <div className="w-full h-screen bg-gray-950" />,
});

// If using flyToTarget prop pattern (simpler than forwardRef):
export default function HomeClient({ countries }: HomeClientProps) {
  const [selectedCountryId, setSelectedCountryId] = useState<number | null>(null);
  const [flyToTarget, setFlyToTarget] = useState<{ lng: number; lat: number } | null>(null);

  function handleSearchSelect(countryId: number) {
    const country = countries.find(c => c.id === countryId);
    if (!country?.longitude || !country?.latitude) return;
    setFlyToTarget({ lng: country.longitude, lat: country.latitude });
    setSelectedCountryId(countryId);
  }

  return (
    <main className="w-full h-screen relative">
      <StatsSidebar />
      <SearchBar onSelect={handleSearchSelect} />
      <MapView
        countries={countries}
        onCountrySelect={setSelectedCountryId}
        flyToTarget={flyToTarget}
        onFlyToComplete={() => setFlyToTarget(null)}
      />
      {selectedCountryId !== null && (
        <CountryPanel
          countryId={selectedCountryId}
          onClose={() => setSelectedCountryId(null)}
        />
      )}
    </main>
  );
}
```

### MapView flyToTarget Prop Pattern (avoids forwardRef + dynamic import complexity)

```typescript
// Source: Standard React useEffect pattern for watching prop changes
useEffect(() => {
  if (!flyToTarget || !map.current) return;
  if (!map.current.loaded()) {
    // Store for after load — or skip; search result assumed after initial load
    return;
  }
  map.current.flyTo({
    center: [flyToTarget.lng, flyToTarget.lat],
    zoom: Math.max(map.current.getZoom(), 4),
    duration: 1200,
  });
  onFlyToComplete?.();
}, [flyToTarget]);
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Separate debounce library (lodash.debounce) | `setTimeout` + cleanup in `useEffect` | No dependency needed |
| Redux for cross-component state | Props + callbacks from `HomeClient` | Matches existing project pattern |
| Server component fetch for analytics | Client `useEffect` fetch in `StatsSidebar` | Consistent with CountryPanel pattern; allows future refresh |

---

## Open Questions

1. **Search bar placement — header vs. map overlay**
   - What we know: There is no header component yet; `layout.tsx` has no nav bar.
   - What's unclear: Whether to add a top header bar or overlay the search on the map.
   - Recommendation: Overlay on the map (positioned top-center with `absolute` or `fixed`) — avoids adding a new layout wrapper and is consistent with the full-screen map aesthetic. z-index must be high enough to clear the Mapbox canvas.

2. **Stats sidebar visibility — always visible or toggle**
   - What we know: `CountryPanel` is conditionally rendered. The layout has no persistent sidebar.
   - What's unclear: Whether the stats sidebar should be always visible or shown/hidden by a button.
   - Recommendation: Always visible on left side (fixed, narrow width ~280px). The map fills remaining space. CountryPanel opens on the right when needed. This is the simplest implementation that meets requirements.

3. **Top 5 countries in sidebar — clickable?**
   - What we know: Requirements say "display top 5 countries ranked by artist count." No explicit click behavior specified.
   - What's unclear: Whether clicking a top country row should navigate the map.
   - Recommendation: Make them clickable (call `onCountrySelect`) — this is a natural UX affordance and requires only passing a callback prop to `StatsSidebar`.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `backend/app/schemas/search.py` — confirmed `country_id` absent from search hits
- Direct codebase inspection: `backend/app/services/search_service.py` — confirmed query structure
- Direct codebase inspection: `backend/app/services/analytics_service.py` — confirmed `diversity_score` is 0–1 (Shannon entropy / max entropy)
- Direct codebase inspection: `frontend/src/components/HomeClient.tsx` — confirmed `countries` array is available in HomeClient
- Direct codebase inspection: `frontend/src/components/MapView.tsx` — confirmed `map.current.flyTo` API available, map is not exposed outside component
- Direct codebase inspection: `frontend/package.json` — confirmed no new dependencies needed

### Secondary (MEDIUM confidence)
- React docs pattern: `useImperativeHandle` + `forwardRef` for exposing imperative methods to parent
- React docs pattern: `setTimeout` + `useEffect` cleanup for debounce

---

## Metadata

**Confidence breakdown:**
- Backend gap (missing country_id in search): HIGH — directly verified by reading schema and service files
- Standard stack: HIGH — all dependencies confirmed in package.json
- Architecture patterns: HIGH — based on direct codebase reading
- Mapbox flyTo API: HIGH — `map.current.flyTo` already used in MapView click handler
- Pitfalls: MEDIUM-HIGH — based on known React/Mapbox integration patterns

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable stack; backend endpoints are built)
