# Coding Conventions

**Analysis Date:** 2026-03-24

## Naming Patterns

**Files:**
- React components: PascalCase (e.g., `NavBar.tsx`, `AIInsightPanel.tsx`)
- Hooks and utilities: camelCase (e.g., `api-client.ts`)
- Python modules: snake_case (e.g., `disease_service.py`, `correlation_service.py`)
- Configuration files: kebab-case or camelCase (e.g., `eslint.config.mjs`, `tailwind.config.ts`)

**Functions:**
- TypeScript: camelCase (e.g., `getRegions()`, `handleApplyFilters()`, `generateInsight()`)
- Python: snake_case (e.g., `get_diseases()`, `compute_disease_climate_correlation()`)
- Async handlers: prefix with `handle` (e.g., `handleSend()`, `handleRegionSelect()`)

**Variables:**
- TypeScript: camelCase for all variables and state (e.g., `selectedDisease`, `comparisonCountries`, `dateRange`)
- Python: snake_case for all variables (e.g., `disease_by_date`, `climate_vals`, `common_dates`)
- Boolean variables: prefix with `is`, `has`, or `show` (e.g., `isLoading`, `hasError`, `showRegions`)

**Types:**
- TypeScript interfaces: PascalCase with `Props` suffix for component props (e.g., `SidebarProps`, `AIInsightPanelProps`)
- TypeScript types: PascalCase for data types (e.g., `Region`, `PeriodMetrics`, `TimeSeriesData`)
- Python models: PascalCase (e.g., `Disease`, `DiseaseRecord`, `Region`)
- Python schemas: PascalCase (e.g., `DiseaseDataResponse`)

## Code Style

**Formatting:**
- Frontend: ESLint with Next.js core web vitals and TypeScript rules
- Config: `eslint.config.mjs` (flat config format)
- No Prettier config - ESLint handles formatting
- Indentation: 2 spaces (TypeScript/TSX)
- Indentation: 4 spaces (Python)

**Linting:**
- Framework: ESLint v9 with Next.js rules
- Config file: `/Users/udirno/Desktop/HealthMap/frontend/eslint.config.mjs`
- Rules enforced: Next.js core web vitals + TypeScript best practices
- Backend: No explicit linting config found - conventions appear ad-hoc

**Tailwind CSS:**
- Utility-first approach with tailwind.config.ts
- Color scheme: Dark theme with slate/blue palette
- Size classes: Semantic sizing (e.g., `h-16`, `px-8`, `rounded-lg`)
- Responsive: Mobile-first implicit (rarely uses explicit breakpoints)

## Import Organization

**Order (TypeScript/TSX):**
1. React imports (`import { useState } from 'react'`)
2. Third-party packages (`import axios from 'axios'`)
3. Lucide React icons (`import { TrendingUp, Loader2 } from 'lucide-react'`)
4. Recharts components (`import { LineChart, Line } from 'recharts'`)
5. Local utilities and types (`import { apiClient, PeriodMetrics } from '@/lib/api-client'`)
6. Local components (`import NavBar from '@/components/layout/NavBar'`)

**Path Aliases:**
- Frontend: `@/*` resolves to `/src/*` (configured in `tsconfig.json`)
- Example: `@/components/layout/NavBar` → `src/components/layout/NavBar`

**Order (Python):**
1. Standard library imports
2. Third-party imports (SQLAlchemy, FastAPI, Pydantic)
3. Local imports (models, schemas, services)

## Error Handling

**TypeScript/React:**
- Try-catch blocks in async functions (e.g., in `handleSend()`)
- State-based error display via `error` state variable
- User-facing messages: simple strings (e.g., `'No data'`, `'Failed to load chart data'`)
- Console logging for debug info: `console.error('Error message:', error)`
- HTTP errors: Caught and converted to user messages, not thrown

**Python:**
- HTTPException for API responses (e.g., `HTTPException(status_code=404, detail=...)`)
- Return None for missing data rather than raising exceptions
- Dictionary-based error responses for service layer (e.g., `{"error": "Insufficient data"}`)
- Query builders check for existence before processing

## Logging

**Framework:** `console` (browser) for frontend, no structured logging in backend

**Patterns:**
- Frontend: `console.error()` only for actual errors that need developer attention
- Backend: No logging found - errors handled silently with error returns
- No log levels or structured logging in place

## Comments

**When to Comment:**
- Function docstrings in Python (triple-quoted): Describe purpose and parameters
- JSDoc/TSDoc: Not consistently used, but found on exported interfaces
- Inline comments: Rare; code structure is generally self-documenting
- Complex logic: Single-line comments explaining intent (e.g., `// In comparison mode, add/remove from comparison list`)

**Example patterns:**

Python docstring:
```python
def get_diseases(db: Session) -> List[Disease]:
    """Get all available diseases"""
    return db.query(Disease).all()
```

Inline comment explaining logic:
```typescript
// Small delay to let metrics render first
await new Promise(resolve => setTimeout(resolve, 100));
```

## Function Design

**Size:**
- Functions typically 20-80 lines for service methods
- React components 100-400 lines (includes JSX)
- No explicit line length limits enforced

**Parameters:**
- TypeScript: Props interfaces for components, individual parameters for functions
- Python: Explicit parameters with type hints, Session as dependency injection
- Database Session: Passed as `db: Session = Depends(get_db)` in FastAPI routes

**Return Values:**
- TypeScript: Interfaces define return shapes (e.g., `Promise<Region[]>`)
- Python: Explicit type hints (e.g., `-> Optional[Dict[str, Any]]`)
- Nullable returns: Use `Optional[T]` or `Union[T, None]` rather than throwing

## Module Design

**Exports:**
- React components: Default export is the component function
- Utilities: Named exports for functions, types exported alongside
- Services: Static methods grouped in classes (e.g., `class DiseaseService`)

**Barrel Files:**
- Used for models: `app/models/__init__.py`
- Used for schemas: `app/schemas/__init__.py`
- Used for routes: `app/api/__init__.py`
- Not explicitly used in frontend src directory

**File Organization:**
- Components organized by feature/layout (e.g., `components/layout/`, `components/charts/`, `components/map/`)
- Services organized by domain (e.g., `app/services/disease_service.py`)
- Models and schemas paired 1:1 (model in `models/`, schema in `schemas/`)

## Type Safety

**TypeScript:**
- Strict mode enabled (`"strict": true` in `tsconfig.json`)
- Explicit type annotations on props and return types
- Interfaces for all data structures passed between components

**Python:**
- Type hints on all function signatures
- Pydantic models for request/response validation
- SQLAlchemy ORM models with typed column definitions

## Common Patterns

**State Management:**
- React: `useState` for component-level state
- No global state management (Redux, Zustand, etc.)
- Props drilling for data flow
- API calls trigger state updates in `useEffect` hooks

**Data Flow (React):**
```typescript
// 1. Props passed down with callbacks
<Sidebar
  selectedDisease={selectedDisease}
  onSelectDisease={setSelectedDisease}
  dateRange={dateRange}
  onDateRangeChange={setDateRangeChange}
/>

// 2. useEffect triggers API call
useEffect(() => {
  apiClient.getPeriodMetrics(...).then(setMetrics);
}, [dependencies]);

// 3. Results update state
```

**API Client Pattern:**
- Centralized client in `lib/api-client.ts` with static methods
- All HTTP calls through axios instance
- Interfaces define request/response shapes
- Example: `apiClient.getPeriodMetrics(disease, region, start, end)`

**Service Layer Pattern (Python):**
- Static methods in service classes
- Database Session injected as parameter
- Return None for missing data, Dict for results
- Example: `DiseaseService.get_metrics_for_period(db, disease, region, start, end)`

---

*Convention analysis: 2026-03-24*
