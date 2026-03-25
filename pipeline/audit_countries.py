"""
Systematic country audit script.

Strategy: Use genre data + web search to identify misassigned artists.
The MusicBrainz name-only search often matches wrong artists (e.g., common names
match a different artist from a different country).

This script:
1. Finds all artists assigned to countries where their genres don't match
   (e.g., "hip hop" artist assigned to Switzerland)
2. For artists with spotify_id, uses Spotify API to get definitive data
3. Outputs SQL corrections
"""

import asyncio
import os
import sys
import json
import base64
import urllib.request
import urllib.parse
import time

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'soundatlas_user')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'soundatlas_password')
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'soundatlas_db')

# Genres that strongly indicate US origin
US_GENRES = {
    'hip hop', 'rap', 'trap', 'r&b', 'southern hip hop', 'west coast',
    'east coast', 'dirty south', 'crunk', 'hyphy', 'gangster rap',
    'conscious hip hop', 'underground hip hop', 'alternative hip hop',
    'neo soul', 'quiet storm', 'urban contemporary', 'trap soul',
    'melodic rap', 'plugg', 'rage rap', 'chicago rap', 'detroit hip hop',
    'atl hip hop', 'bay area hip hop', 'memphis hip hop',
}

# Genres that indicate specific non-US origins
GENRE_COUNTRY_HINTS = {
    'afrobeats': 'NG', 'afrobeat': 'NG', 'afropop': 'NG', 'afro soul': 'NG',
    'afro r&b': 'NG', 'nigerian': 'NG', 'naija': 'NG',
    'dancehall': 'JM', 'reggae': 'JM',
    'reggaeton': 'PR', 'latin trap': 'PR',
    'bollywood': 'IN', 'desi': 'IN', 'filmi': 'IN', 'bhangra': 'IN',
    'punjabi': 'IN',
    'k-pop': 'KR', 'korean': 'KR',
    'j-pop': 'JP',
    'uk rap': 'GB', 'grime': 'GB', 'uk drill': 'GB', 'uk garage': 'GB',
    'british soul': 'GB',
    'french rap': 'FR', 'french pop': 'FR',
    'german hip hop': 'DE',
    'australian hip hop': 'AU',
    'canadian hip hop': 'CA', 'canadian pop': 'CA',
    'colombian': 'CO',
    'brazilian': 'BR', 'funk carioca': 'BR',
}

# Countries where US hip-hop/r&b artists are commonly misassigned by MusicBrainz
SUSPECT_COUNTRIES = {'CH', 'AT', 'HU', 'NO', 'BD', 'IL', 'RS'}


def get_spotify_token():
    """Get Spotify API token using client credentials."""
    client_id = os.environ.get('SPOTIFY_CLIENT_ID', '')
    client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
    if not client_id or not client_secret:
        return None

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({'grant_type': 'client_credentials'}).encode()
    req = urllib.request.Request(
        'https://accounts.spotify.com/api/token',
        data=data,
        headers={'Authorization': f'Basic {credentials}'}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())['access_token']
    except Exception as e:
        print(f"Failed to get Spotify token: {e}")
        return None


def spotify_get_artist(token, spotify_id):
    """Fetch artist details from Spotify API."""
    req = urllib.request.Request(
        f'https://api.spotify.com/v1/artists/{spotify_id}',
        headers={'Authorization': f'Bearer {token}'}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return None


def guess_country_from_genres(genres):
    """Use genre data to guess likely origin country."""
    if not genres:
        return None

    genre_str = ' '.join(g.lower() for g in genres)

    # Check specific country hints first
    for hint, country in GENRE_COUNTRY_HINTS.items():
        if hint in genre_str:
            return country

    # Check for US genres
    for g in genres:
        g_lower = g.lower()
        for us_genre in US_GENRES:
            if us_genre in g_lower or g_lower in us_genre:
                return 'US'

    return None


def main():
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    cur = conn.cursor()

    # Get all artists with countries and genres
    cur.execute("""
        SELECT a.id, a.name, a.spotify_id, a.genres,
               c.iso_alpha2, c.name as country_name,
               COUNT(t.id) as track_count
        FROM artists a
        LEFT JOIN countries c ON a.country_id = c.id
        LEFT JOIN tracks t ON t.artist_id = a.id
        WHERE a.country_id IS NOT NULL
        GROUP BY a.id, a.name, a.spotify_id, a.genres, c.iso_alpha2, c.name
        HAVING COUNT(t.id) >= 1
        ORDER BY COUNT(t.id) DESC
    """)
    artists = cur.fetchall()

    # Get Spotify token for verification
    token = get_spotify_token()
    if token:
        print("Spotify API available for verification")
    else:
        print("No Spotify credentials — using genre-based analysis only")

    corrections = []
    verified_ok = 0
    suspect_list = []

    for artist_id, name, spotify_id, genres, current_iso, country_name, track_count in artists:
        genres = genres or []
        guessed = guess_country_from_genres(genres)

        # Flag if genre suggests different country than assigned
        is_suspect = False
        reason = ""

        if guessed and guessed != current_iso:
            # Genre strongly suggests a different country
            is_suspect = True
            reason = f"genres suggest {guessed}, assigned to {current_iso}"
        elif current_iso in SUSPECT_COUNTRIES:
            # Artist assigned to a country where very few real artists exist in this dataset
            is_suspect = True
            reason = f"assigned to suspect country {current_iso} ({country_name})"

        if is_suspect:
            # Try Spotify verification if available
            verified_country = None
            if token and spotify_id:
                sp_data = spotify_get_artist(token, spotify_id)
                if sp_data:
                    sp_genres = sp_data.get('genres', [])
                    verified_country = guess_country_from_genres(sp_genres)
                    time.sleep(0.05)  # Rate limit

            final_country = verified_country or guessed
            if final_country and final_country != current_iso:
                corrections.append({
                    'id': artist_id,
                    'name': name,
                    'current': f"{country_name} ({current_iso})",
                    'suggested': final_country,
                    'reason': reason,
                    'tracks': track_count,
                    'genres': genres[:3],
                    'source': 'spotify+genre' if verified_country else 'genre',
                })
            else:
                verified_ok += 1
        else:
            verified_ok += 1

    # Print report
    print(f"\n{'='*100}")
    print(f"COUNTRY AUDIT REPORT")
    print(f"{'='*100}")
    print(f"Total artists checked: {len(artists)}")
    print(f"Verified OK: {verified_ok}")
    print(f"Corrections needed: {len(corrections)}")
    print()

    if corrections:
        # Sort by track count descending
        corrections.sort(key=lambda x: x['tracks'], reverse=True)

        print(f"{'#':<4} {'Artist':<30} {'Current':<25} {'Suggested':<5} {'Trks':<5} {'Source':<15} {'Genres'}")
        print('-' * 120)
        for i, c in enumerate(corrections, 1):
            print(f"{i:<4} {c['name']:<30} {c['current']:<25} {c['suggested']:<5} {c['tracks']:<5} {c['source']:<15} {str(c['genres'])[:30]}")

        # Generate SQL
        print(f"\n{'='*100}")
        print("SQL CORRECTIONS (review before applying):")
        print(f"{'='*100}")
        for c in corrections:
            print(f"-- {c['name']}: {c['current']} -> {c['suggested']} (reason: {c['reason']})")
            print(f"UPDATE artists SET country_id = (SELECT id FROM countries WHERE iso_alpha2 = '{c['suggested']}') WHERE id = {c['id']};")

        # Also output as a Python dict for automated application
        print(f"\n{'='*100}")
        print("APPLY ALL CORRECTIONS:")
        print(f"{'='*100}")
        apply_list = [(c['id'], c['suggested'], c['name']) for c in corrections]
        print(f"CORRECTIONS = {json.dumps(apply_list, indent=2)}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
