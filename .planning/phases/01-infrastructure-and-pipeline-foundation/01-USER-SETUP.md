# Phase 1: User Setup Required

## Status: Incomplete

## Spotify API Credentials

**Why needed:** Audio features validation and Phase 2 data enrichment require Spotify API access.

### Environment Variables

| Variable | Source | Status |
|----------|--------|--------|
| SPOTIFY_CLIENT_ID | Spotify Developer Dashboard -> Create App -> Client ID | Not set |
| SPOTIFY_CLIENT_SECRET | Spotify Developer Dashboard -> Create App -> Client Secret | Not set |

### Setup Steps

1. Go to https://developer.spotify.com/dashboard
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in app details (any name/description)
5. Copy the Client ID and Client Secret
6. Add to `.env`:
   ```
   SPOTIFY_CLIENT_ID=<your client id>
   SPOTIFY_CLIENT_SECRET=<your client secret>
   ```

### Verification

```bash
python3 pipeline/validate_audio_features.py
```

Expected: Either "AVAILABLE" or "403 Forbidden" (both are valid outcomes).

**Note on 403:** Apps registered after November 2024 receive 403 on the audio features endpoint. This is expected and handled gracefully — Phase 2 will skip audio feature fetching and the pipeline will proceed without it. The flag file at `pipeline/.audio_features_available` records the result.
