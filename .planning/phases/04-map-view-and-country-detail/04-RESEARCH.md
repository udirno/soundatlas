# Phase 4: Map View and Country Detail - Research

**Researched:** 2026-03-24
**Domain:** Mapbox GL JS (WebGL map), Recharts (data visualization), Next.js 14 App Router (client/server boundaries)
**Confidence:** HIGH

## Summary

Phase 4 builds the primary UI of SoundAtlas: an interactive world map where each country is a WebGL-rendered circle sized by track count and colored by dominant genre, plus a detail panel that opens on country click. The three technical pillars are Mapbox GL JS v3 (map rendering), Recharts v3 (genre pie chart and audio feature radar/bar chart), and Next.js 14 App Router patterns (client component boundaries, SSR exclusion, data fetching).

The most important architectural constraint is already decided by prior-phase decisions: all map markers MUST use a GeoJSON source + circle layer, not `new mapboxgl.Marker()`. This is not a preference — the dataset contains ~3,022 artist countries, and Mapbox's own documentation states that HTML markers become unresponsive past ~100 points. The circle layer renders in WebGL and handles thousands of features without performance degradation. The entire map component (and chart components) must be excluded from SSR via `dynamic(..., { ssr: false })` because Mapbox GL JS and Recharts both require the browser DOM.

A critical data reality: Spotify restricted audio feature endpoints in November 2024. The backend returns null for all audio feature fields (energy, danceability, valence, tempo, acousticness). The frontend must render these charts gracefully with an empty/unavailable state — don't throw errors, don't hide the chart section, just show a clear "Audio data unavailable" message. This is confirmed by both the project's prior-phase decisions and the backend service code which explicitly handles `None` values by returning null floats.

**Primary recommendation:** Mount the full-screen map as a dynamically imported client component, fetch country list data server-side in page.tsx and pass it as props, then render the detail panel as a sibling client component controlled by map click state.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mapbox-gl | 3.20.0 | WebGL map rendering, GeoJSON layers, interactions | Official Mapbox JS SDK; v3 is current stable, WebGL 2-only, backwards-compatible |
| recharts | 3.8.0 | Genre pie chart, audio feature radar/bar chart | Most widely used React charting library; composable SVG charts with TypeScript support |
| next | 14.2.15 | App shell (already installed) | Already in package.json; App Router patterns apply |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @types/mapbox-gl | ^3.x | TypeScript types for mapbox-gl | Required for type-safe map API usage in TypeScript |
| tailwindcss | ^3.4 | Panel layout, typography (already installed) | Already in project; use for detail panel layout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mapbox-gl (direct) | react-map-gl | react-map-gl wraps mapbox-gl with React props but adds abstraction complexity; direct mapbox-gl gives cleaner imperative control for GeoJSON layer management |
| recharts | chart.js / victory | recharts is already specified in project requirements; no alternatives valid |
| CSS Popup | mapboxgl.Popup | mapboxgl.Popup is CSS-only HTML overlay — fine for hover tooltip; detail panel is a React component sidebar, not a Popup |

**Installation:**
```bash
npm install mapbox-gl recharts @types/mapbox-gl
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── app/
│   ├── page.tsx              # Server component — fetches /api/countries, renders MapView
│   ├── layout.tsx            # Already exists
│   └── globals.css           # Add mapbox-gl CSS import here
├── components/
│   ├── MapView.tsx           # 'use client' — Mapbox map, full-screen, GeoJSON circle layer
│   ├── CountryPanel.tsx      # 'use client' — right-side detail panel (conditionally rendered)
│   ├── GenrePieChart.tsx     # 'use client' — Recharts PieChart, receives genre_breakdown prop
│   └── AudioFeatureChart.tsx # 'use client' — Recharts RadarChart or BarChart, handles null data
└── lib/
    └── api.ts                # Typed fetch helpers for /api/countries and /api/countries/{id}
```

### Pattern 1: SSR Exclusion for Mapbox Component
**What:** Mapbox GL JS accesses `window` and requires browser WebGL. Next.js pre-renders `'use client'` components on the server, causing `ReferenceError: window is not defined`. Use `dynamic(..., { ssr: false })` to skip server rendering entirely for the map container.
**When to use:** Any component that imports `mapbox-gl` directly.
**Example:**
```typescript
// Source: https://nextjs.org/docs/app/building-your-application/optimizing/lazy-loading
// src/app/page.tsx (Server Component)
import dynamic from 'next/dynamic';

const MapView = dynamic(() => import('@/components/MapView'), {
  ssr: false,
  loading: () => <div className="w-full h-screen bg-gray-950" />,
});
```

### Pattern 2: Map Initialization in useEffect with useRef
**What:** Store the map container DOM node in `useRef` and initialize the map inside `useEffect`. The map instance lives outside React state (do NOT put it in `useState` — the Map object is not serializable and triggers re-render loops). Clean up with `map.remove()` on unmount.
**When to use:** The canonical pattern for imperative Mapbox GL JS in React.
**Example:**
```typescript
// Source: https://dev.to/dqunbp/using-mapbox-gl-in-react-with-next-js-2glg
'use client';
import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

export default function MapView({ countries }: { countries: CountryFeatureCollection }) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!;
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [0, 20],
      zoom: 1.5,
    });

    map.current.on('load', () => {
      // Add GeoJSON source and circle layer here
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  return <div ref={mapContainer} className="w-full h-screen" />;
}
```

### Pattern 3: GeoJSON Source + Circle Layer with Data-Driven Expressions
**What:** The `/api/countries` response (list of CountryListItem objects) must be transformed into a GeoJSON FeatureCollection before being passed to Mapbox. Each feature uses `latitude`/`longitude` as its Point geometry and includes `track_count`, `artist_count`, and `top_genre` as properties. The circle layer then uses Mapbox expressions to size by `track_count` and color by `top_genre`.
**When to use:** Any time you render dataset-scale point data on Mapbox.
**Example:**
```typescript
// Source: https://docs.mapbox.com/mapbox-gl-js/guides/add-your-data/style-layers/
// Transform API response to GeoJSON
function toGeoJSON(countries: CountryListItem[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: countries
      .filter(c => c.latitude != null && c.longitude != null)
      .map(c => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [c.longitude!, c.latitude!] },
        properties: {
          id: c.id,
          name: c.name,
          track_count: c.track_count,
          artist_count: c.artist_count,
          top_genre: c.top_genre ?? 'Unknown',
        },
      })),
  };
}

// Add source and layer after map load
map.current.addSource('countries', {
  type: 'geojson',
  data: toGeoJSON(countries),
});

map.current.addLayer({
  id: 'country-circles',
  type: 'circle',
  source: 'countries',
  paint: {
    // Proportional sizing: sqrt scaling prevents large countries overwhelming small ones
    'circle-radius': [
      'interpolate', ['linear'],
      ['sqrt', ['get', 'track_count']],
      0, 4,
      10, 10,
      50, 24,
      100, 36,
    ],
    // Categorical color by genre — define genre palette
    'circle-color': [
      'match', ['get', 'top_genre'],
      'pop', '#f43f5e',
      'hip hop', '#f97316',
      'rock', '#8b5cf6',
      'electronic', '#06b6d4',
      'r&b', '#10b981',
      'latin', '#eab308',
      '#94a3b8', // fallback
    ],
    'circle-opacity': 0.85,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
    'circle-stroke-opacity': 0.3,
  },
});
```

### Pattern 4: Hover Tooltip using Mapbox Popup + addInteraction
**What:** In Mapbox GL JS v3, the recommended hover pattern uses `map.addInteraction()` for `mousemove` with `{ target: { layerId } }` to get quick feature access, and `map.on('mouseleave', layerId, handler)` to clean up. Create a single `Popup` instance outside the handler and update it on each move.
**When to use:** Hover tooltips on layer features.
**Example:**
```typescript
// Source: https://docs.mapbox.com/mapbox-gl-js/example/hover-tooltip/
const tooltip = new mapboxgl.Popup({
  closeButton: false,
  closeOnClick: false,
  offset: [0, -12],
});

map.addInteraction('country-hover', {
  type: 'mousemove',
  target: { layerId: 'country-circles' },
  handler: (e) => {
    map.getCanvas().style.cursor = 'pointer';
    const props = e.feature.properties;
    tooltip
      .setLngLat(e.lngLat)
      .setHTML(`
        <div class="mapbox-tooltip">
          <strong>${props.name}</strong><br/>
          ${props.artist_count} artists · ${props.top_genre}
        </div>
      `)
      .addTo(map);
  },
});

map.on('mouseleave', 'country-circles', () => {
  map.getCanvas().style.cursor = '';
  tooltip.remove();
});
```

### Pattern 5: Click-to-Fly + Open Detail Panel
**What:** Use `map.on('click', layerId, handler)` to detect circle clicks. Extract feature coordinates, call `map.flyTo()` with that center, and call a React state setter (passed in as a prop or via a callback ref) to open the detail panel.
**When to use:** Click interaction that must trigger both a map animation and a React UI state change.
**Example:**
```typescript
// Source: https://docs.mapbox.com/mapbox-gl-js/example/center-on-feature/
map.on('click', 'country-circles', (e) => {
  if (!e.features?.length) return;
  const feature = e.features[0];
  const coords = (feature.geometry as GeoJSON.Point).coordinates as [number, number];
  const countryId = feature.properties?.id as number;

  map.flyTo({
    center: coords,
    zoom: Math.max(map.getZoom(), 4),
    duration: 1200,
  });

  onCountrySelect(countryId); // React state setter — triggers detail panel open
});
```

### Pattern 6: Recharts with 'use client' in Next.js App Router
**What:** Recharts uses D3 and requires the browser DOM. All Recharts components must be in files with `'use client'` at the top. You can fetch data in a Server Component and pass it as props to the chart components.
**When to use:** Every chart component.
**Example:**
```typescript
// Source: https://recharts.github.io/en-US/api/PieChart/
'use client';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

const GENRE_COLORS: Record<string, string> = {
  pop: '#f43f5e',
  'hip hop': '#f97316',
  rock: '#8b5cf6',
  electronic: '#06b6d4',
  'r&b': '#10b981',
  latin: '#eab308',
};

export function GenrePieChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }));

  if (chartData.length === 0) {
    return <p className="text-gray-500 text-sm">No genre data available</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={chartData} dataKey="value" nameKey="name" outerRadius={80}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={GENRE_COLORS[entry.name] ?? '#94a3b8'} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
```

### Pattern 7: Audio Feature Null Handling
**What:** All audio feature fields (energy, danceability, valence, tempo, acousticness) are null in the database because Spotify restricted the endpoint in November 2024. The comparison endpoint will return all nulls. The chart must detect this and show an informational empty state instead of rendering empty axes.
**When to use:** Any component consuming audio feature data from `/api/countries/{id}/comparison`.
**Example:**
```typescript
'use client';
import {
  ResponsiveContainer, RadarChart, PolarGrid,
  PolarAngleAxis, Radar, Legend
} from 'recharts';

type FeatureMap = Record<string, number | null>;

function hasAnyData(features: FeatureMap): boolean {
  return Object.values(features).some(v => v !== null);
}

export function AudioFeatureChart({
  countryAverages,
  globalAverages,
}: {
  countryAverages: FeatureMap;
  globalAverages: FeatureMap;
}) {
  if (!hasAnyData(countryAverages)) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
        Audio feature data is unavailable for this release.
      </div>
    );
  }

  const FEATURES = ['energy', 'danceability', 'valence', 'acousticness'];
  const chartData = FEATURES.map(f => ({
    feature: f,
    country: countryAverages[f] ?? 0,
    global: globalAverages[f] ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <RadarChart data={chartData}>
        <PolarGrid />
        <PolarAngleAxis dataKey="feature" />
        <Radar name="Country" dataKey="country" stroke="#f43f5e" fill="#f43f5e" fillOpacity={0.3} />
        <Radar name="Global" dataKey="global" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.2} />
        <Legend />
      </RadarChart>
    </ResponsiveContainer>
  );
}
```

### Anti-Patterns to Avoid
- **Using `new mapboxgl.Marker()` for country circles:** HTML DOM overhead kills performance at 3,000+ points. The project decision explicitly prohibits this. Use the GeoJSON source + circle layer pattern.
- **Putting the `Map` instance in `useState`:** The Map object has internal mutable state, is not serializable, and triggers re-renders. Always store it in `useRef`.
- **Importing `mapbox-gl` in a Server Component:** This causes build-time failures. Always use `dynamic(..., { ssr: false })` for the wrapping page component, and `'use client'` on the map component itself.
- **Forgetting the mapbox-gl CSS import:** Without `mapbox-gl/dist/mapbox-gl.css`, the map renders broken (missing controls, wrong popup positioning). Import it inside the client component file.
- **Fetching country detail data on map click in MapView:** This creates tight coupling and makes testing hard. Fetch in `CountryPanel` via `useEffect` or pass a fetch function prop. MapView should only emit `countryId`.
- **Using `tempo` in RadarChart:** Tempo is in BPM (60–200 range) while other features are 0–1 normalized. Mixing them distorts the radar chart. Either normalize tempo to 0–1 before charting or exclude it from the radar and show it separately as text.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Map tooltip positioning | Custom React overlay with absolute CSS | `mapboxgl.Popup` | Popup handles coordinate-to-screen projection, viewport edge cases, and z-index correctly |
| Fly-to animation | Custom CSS transitions on map container | `map.flyTo()` | Built-in interpolation with configurable easing, duration, and curve |
| Proportional circle sizing formula | Custom pixel math | Mapbox `interpolate` expression with `sqrt` of track_count | Expressions run GPU-side; sqrt scaling is the standard approach to prevent large-count dominance |
| Chart responsiveness | `width={someNumber}` hardcoded | `ResponsiveContainer` from Recharts | Handles resize events and container width changes automatically |
| Genre color palette sync | Separate palette files for map and chart | Single exported `GENRE_COLORS` constant in `lib/colors.ts` | Map circle colors and pie chart slice colors must match visually |
| Null data detection for audio features | Per-field undefined checks | `hasAnyData()` helper checking all values | All fields will be null simultaneously due to API restriction — check collectively |

**Key insight:** The Mapbox expressions engine (interpolate, match, get) runs on the GPU inside WebGL. Doing equivalent logic in JavaScript per-feature before rendering defeats the purpose of using a layer.

## Common Pitfalls

### Pitfall 1: `window is not defined` at Build or Runtime
**What goes wrong:** Next.js 14 pre-renders `'use client'` components on the server. Mapbox GL JS accesses `window`, `navigator`, `document`, and WebGL — none available in Node.js. The build succeeds but runtime throws on first render.
**Why it happens:** Forgetting `dynamic(..., { ssr: false })` on the parent page import, or importing mapbox-gl in a module that gets evaluated at module load time rather than inside a `useEffect`.
**How to avoid:** Always wrap the Map component import with `dynamic({ ssr: false })` in page.tsx. Never import `mapbox-gl` directly in a Server Component or at module level in shared files.
**Warning signs:** `ReferenceError: window is not defined` in build output or server logs.

### Pitfall 2: Map CSS Not Imported
**What goes wrong:** The Mapbox popup appears at position (0,0) on the page. Navigation controls (zoom buttons) are unstyled. Map canvas has incorrect dimensions.
**Why it happens:** `mapbox-gl/dist/mapbox-gl.css` was not imported.
**How to avoid:** Add `import 'mapbox-gl/dist/mapbox-gl.css'` inside the `MapView.tsx` client component file, not in `globals.css` (it only loads when the client component mounts).
**Warning signs:** Popups rendering in wrong position, navigation controls appearing as raw HTML.

### Pitfall 3: Circle Layer Added Before Map 'load' Event
**What goes wrong:** `map.addSource()` throws `Error: Style is not done loading`. The source and layer disappear on style reload.
**Why it happens:** Calling `addSource`/`addLayer` synchronously after `new mapboxgl.Map()` before the style has finished loading.
**How to avoid:** All `addSource`, `addLayer`, `addInteraction`, and `map.on('click', layerId)` calls must be inside the `map.on('load', () => { ... })` callback.
**Warning signs:** Console errors "Style is not done loading" or the circle layer missing on initial render.

### Pitfall 4: Recharts Components Rendered as Server Components
**What goes wrong:** Build error: `Error: Hooks can only be called inside of the body of a function component` or hydration mismatch warnings.
**Why it happens:** Recharts v3 uses React hooks internally and requires the browser DOM. Without `'use client'`, Next.js tries to render charts on the server.
**How to avoid:** Every file containing a Recharts component (`PieChart`, `RadarChart`, `BarChart`, `ResponsiveContainer`) must have `'use client'` as the first line.
**Warning signs:** Build-time hook errors, hydration mismatch warnings in console.

### Pitfall 5: Tempo Scale Distorting RadarChart
**What goes wrong:** The radar chart for audio features shows tempo as a massive spike (values of 60–200) while energy/danceability/valence are 0–1. The chart is visually meaningless.
**Why it happens:** Spotify features use different scales: energy/danceability/valence/acousticness are 0–1 normalized, but tempo is in BPM.
**How to avoid:** Exclude tempo from the radar chart. Show it as a text stat ("Avg tempo: 128 BPM") or normalize it separately (tempo / 200) before including in a radar.
**Warning signs:** One radar axis extending far beyond the others.

### Pitfall 6: GeoJSON Features with Null Coordinates Crashing the Layer
**What goes wrong:** Mapbox throws errors when a GeoJSON feature has null coordinates, which may happen if `latitude`/`longitude` is null in the backend response for newly-added countries without geocoding.
**Why it happens:** Backend `CountryListItem` schema has `latitude: Optional[float]` and `longitude: Optional[float]`.
**How to avoid:** Filter out nulls in the `toGeoJSON` transform: `.filter(c => c.latitude != null && c.longitude != null)`.
**Warning signs:** Map crashes immediately on load with a GeoJSON validation error.

### Pitfall 7: mapboxgl.Popup in React State Causing Stale Closures
**What goes wrong:** The tooltip shows stale data or doesn't update on subsequent hover events because the Popup instance was recreated inside a stale closure.
**Why it happens:** Creating `new mapboxgl.Popup()` inside a `useEffect` or event handler that doesn't have access to the latest state.
**How to avoid:** Create the Popup instance once in a ref or outside the event handler scope, and only call `.setHTML()` and `.setLngLat()` inside the handler.
**Warning signs:** Tooltip shows wrong country data on second hover.

## Code Examples

Verified patterns from official sources:

### GeoJSON Circle Layer with Proportional Sizing
```typescript
// Source: https://docs.mapbox.com/mapbox-gl-js/guides/add-your-data/style-layers/
// Source: https://docs.mapbox.com/mapbox-gl-js/example/data-driven-circle-colors/
map.addLayer({
  id: 'country-circles',
  type: 'circle',
  source: 'countries',
  paint: {
    'circle-radius': [
      'interpolate', ['linear'],
      ['sqrt', ['get', 'track_count']],
      0, 4,      // sqrt(0)  -> 4px
      7, 12,     // sqrt(50) -> 12px
      10, 20,    // sqrt(100) -> 20px
      22, 36,    // sqrt(500) -> 36px
    ],
    'circle-color': [
      'match', ['get', 'top_genre'],
      'pop', '#f43f5e',
      'hip hop', '#f97316',
      'rock', '#8b5cf6',
      'electronic', '#06b6d4',
      'r&b', '#10b981',
      'latin', '#eab308',
      '#94a3b8',
    ],
    'circle-opacity': 0.85,
    'circle-stroke-width': 1,
    'circle-stroke-color': '#ffffff',
    'circle-stroke-opacity': 0.3,
  },
});
```

### Hover Tooltip (Mapbox GL JS v3 Interactions API)
```typescript
// Source: https://docs.mapbox.com/mapbox-gl-js/example/hover-tooltip/
const tooltip = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, offset: [0, -12] });

map.addInteraction('country-hover', {
  type: 'mousemove',
  target: { layerId: 'country-circles' },
  handler: (e) => {
    map.getCanvas().style.cursor = 'pointer';
    const p = e.feature.properties;
    tooltip
      .setLngLat(e.lngLat)
      .setHTML(`<b>${p.name}</b><br>${p.artist_count} artists · ${p.top_genre}`)
      .addTo(map);
  },
});

map.on('mouseleave', 'country-circles', () => {
  map.getCanvas().style.cursor = '';
  tooltip.remove();
});
```

### Click to Fly + Open Panel
```typescript
// Source: https://docs.mapbox.com/mapbox-gl-js/example/center-on-feature/
map.on('click', 'country-circles', (e) => {
  if (!e.features?.length) return;
  const coords = (e.features[0].geometry as GeoJSON.Point).coordinates as [number, number];
  map.flyTo({ center: coords, zoom: Math.max(map.getZoom(), 4), duration: 1200 });
  onCountrySelect(e.features[0].properties?.id as number);
});
```

### Recharts RadarChart for Audio Feature Comparison
```typescript
// Source: https://recharts.github.io/en-US/api/RadarChart (API reference)
'use client';
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend } from 'recharts';

const data = [
  { feature: 'energy', country: 0.72, global: 0.65 },
  { feature: 'danceability', country: 0.68, global: 0.61 },
  { feature: 'valence', country: 0.54, global: 0.50 },
  { feature: 'acousticness', country: 0.21, global: 0.29 },
];

<ResponsiveContainer width="100%" height={220}>
  <RadarChart data={data}>
    <PolarGrid />
    <PolarAngleAxis dataKey="feature" />
    <Radar name="Country" dataKey="country" stroke="#f43f5e" fill="#f43f5e" fillOpacity={0.4} />
    <Radar name="Global" dataKey="global" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.2} />
    <Legend />
  </RadarChart>
</ResponsiveContainer>
```

### Environment Variable Setup
```
# .env.local
NEXT_PUBLIC_MAPBOX_TOKEN=pk.your_token_here
```
```typescript
// In MapView.tsx
mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mapboxgl.Marker()` for data points | GeoJSON source + circle layer (WebGL) | Mapbox always recommended this; v3 reinforces it | Mandatory for datasets >100 points |
| `map.on('mouseenter', layerId)` | `map.addInteraction(id, { type, target, handler })` | Mapbox GL JS v3 introduced Interactions API | New API provides direct feature access (`e.feature`); old API still works but less ergonomic |
| `map.on('click', layerId)` | Still the standard for click events | N/A — unchanged | `map.on('click', layerId)` is still the right pattern for click |
| Recharts 2.x `activeIndex` prop | Recharts 3.x uses `Tooltip` component for active state | Recharts 3.0 (2025) | `activeIndex` removed; use `Tooltip` |
| `mapbox://styles/mapbox/dark-v10` | `mapbox://styles/mapbox/dark-v11` (or `standard` with dark config) | v3 era | dark-v11 confirmed available; `standard` is new default but requires different configuration for dark mode |

**Deprecated/outdated:**
- `mapboxgl.Marker` for data layers: Not deprecated, but explicitly documented as wrong for datasets >100 points. Never use for this project.
- Recharts `activeIndex` prop: Removed in v3. Use `Tooltip` instead.
- `CategoricalChartState` in Recharts: Removed in v3. Use hooks like `useActiveTooltipLabel` instead.

## Open Questions

1. **Mapbox access token availability**
   - What we know: Token must be set as `NEXT_PUBLIC_MAPBOX_TOKEN` in `.env.local`; it is not in the current frontend source
   - What's unclear: Whether the developer has a Mapbox account and token configured
   - Recommendation: The plan should include a task step to verify the token exists and is configured; the map will fail silently (blank canvas) without a valid token

2. **Genre taxonomy for color palette**
   - What we know: `top_genre` is computed from artist genres in the backend using `Counter.most_common(1)`; genres come from Spotify which uses freeform genre tags
   - What's unclear: What the actual top genres in the dataset are — the match expression needs real genre strings
   - Recommendation: Plan should include a step to query `GET /api/analytics/genres` to inspect actual genre values and build the color palette from real data rather than assumed strings

3. **Country centroid data completeness**
   - What we know: `latitude` and `longitude` are `Optional[float]` in the backend schema
   - What's unclear: How many countries in the actual database have null coordinates
   - Recommendation: Filter nulls in `toGeoJSON` (already noted in pitfalls) and add a console warning so missing countries can be identified during development

4. **`dark-v11` vs `standard` style for dark map**
   - What we know: `dark-v11` is confirmed available; `mapbox://styles/mapbox/standard` is the new default in v3 and supports dark configuration
   - What's unclear: Whether `dark-v11` will be deprecated in future versions
   - Recommendation: Use `mapbox://styles/mapbox/dark-v11` now — it is confirmed available and stable; migration to `standard` with dark config can be deferred

## Sources

### Primary (HIGH confidence)
- Official Mapbox docs - https://docs.mapbox.com/mapbox-gl-js/example/popup-on-hover/ — Interactions API + Popup pattern
- Official Mapbox docs - https://docs.mapbox.com/mapbox-gl-js/example/hover-tooltip/ — mousemove hover-tooltip implementation
- Official Mapbox docs - https://docs.mapbox.com/mapbox-gl-js/example/center-on-feature/ — flyTo on click pattern
- Official Mapbox docs - https://docs.mapbox.com/mapbox-gl-js/guides/add-your-data/style-layers/ — GeoJSON source and circle layer API
- Official Mapbox docs - https://docs.mapbox.com/help/dive-deeper/markers-vs-layers/ — markers vs layers performance guidance
- Official Mapbox GitHub - https://github.com/mapbox/mapbox-gl-js/releases — version 3.20.0 confirmed current
- Official Recharts docs - https://recharts.github.io/en-US/api/PieChart/ — PieChart API
- Official Recharts wiki - https://github.com/recharts/recharts/wiki/3.0-migration-guide — v3 breaking changes
- Official Next.js docs - https://nextjs.org/docs/app/building-your-application/optimizing/lazy-loading — dynamic import with ssr:false
- Project backend source - /Users/udirno/Desktop/SoundAtlas/backend/app/schemas/country.py — confirmed null audio features
- Project backend source - /Users/udirno/Desktop/SoundAtlas/backend/app/services/country_service.py — confirmed null handling

### Secondary (MEDIUM confidence)
- https://dev.to/dqunbp/using-mapbox-gl-in-react-with-next-js-2glg — useRef/useEffect pattern for Mapbox in Next.js (consistent with official docs)
- Multiple community sources confirming Recharts requires `'use client'` in Next.js App Router

### Tertiary (LOW confidence)
- Genre color palette recommendations are based on common practice, not verified against actual dataset genre strings — must be validated against `GET /api/analytics/genres`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — mapbox-gl 3.20.0 and recharts 3.8.0 confirmed current from GitHub releases; installation commands verified
- Architecture patterns: HIGH — all patterns verified against official Mapbox and Next.js documentation
- Pitfalls: HIGH — window-is-not-defined, missing CSS, load event timing all verified from official docs and consistent with multiple community sources
- Audio feature null handling: HIGH — confirmed from backend source code (explicit None handling in country_service.py)
- Genre palette: LOW — palette strings assumed; must be verified against actual data from `/api/analytics/genres`

**Research date:** 2026-03-24
**Valid until:** 2026-04-23 (30 days — mapbox-gl is active development but APIs are stable; recharts v3 is recent but stable)
