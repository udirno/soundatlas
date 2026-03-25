# User Setup Required

This document lists external services and environment variables that require manual setup before running the application.

---

## Mapbox Access Token

**Required for:** Map rendering in the frontend

**Why:** The MapView component uses the Mapbox GL JS SDK to render the world map. A valid Mapbox access token is required.

### Steps

1. Visit [https://account.mapbox.com/access-tokens/](https://account.mapbox.com/access-tokens/)
2. Create a free account if you do not have one
3. Copy the **Default public token** (starts with `pk.`)

### Configure

Add the token to `frontend/.env.local` (create this file if it does not exist):

```
NEXT_PUBLIC_MAPBOX_TOKEN=pk.your_token_here
```

**Note:** The `NEXT_PUBLIC_` prefix is required — Next.js only exposes environment variables with this prefix to the browser.

### Verification

After setting the token, start the frontend:

```bash
cd frontend && npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) — you should see a full-screen dark world map with colored circle markers at country positions.

---

## Backend API URL (Optional)

The frontend defaults to `http://localhost:8000` for the backend API. To override (e.g., for a deployed backend), set:

```
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

Add this to `frontend/.env.local` as well.
