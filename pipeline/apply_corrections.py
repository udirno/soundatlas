"""
Filtered country corrections from audit_countries.py output.

EXCLUDED from auto-audit results (would be WRONG):
- Reggaeton/Latin artists → JM: Reggaeton ≠ Jamaica. Bad Bunny, J Balvin, Ozuna, etc. stay in PR/CO
- Canadian artists → US: Drake, PARTYNEXTDOOR, NAV, AP Dhillon stay CA
- British-Asian artists → IN: Zack Knight, The PropheC stay GB (UK diaspora)
- South African artists → NG: Tyla stays ZA, Cassper Nyovest stays ZA
- Jamaican artists → NG: Shenseea stays JM, Popcaan stays JM
- British artists → US when they have UK genres: WSTRN stays GB

KEPT: Only corrections where genre + common knowledge confirms the artist
is genuinely in the wrong country.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'soundatlas_user')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'soundatlas_password')
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'soundatlas_db')

# Format: (artist_name, correct_iso, reason)
CORRECTIONS = [
    # US hip-hop/R&B artists wrongly assigned to GB
    ("Mos Def", "US", "Yasiin Bey, from Brooklyn NY"),
    ("The Roots", "US", "Philadelphia hip-hop group"),
    ("Black Thought", "US", "The Roots frontman, Philadelphia"),
    ("Eric Benet", "US", "R&B singer from Milwaukee"),  # note: may be stored with accent
    ("Total", "US", "R&B group from New Jersey"),
    ("The-Dream", "US", "R&B singer from Rockingham NC"),
    ("K-OS", "CA", "Canadian rapper from Toronto"),  # was GB, should be CA not US
    ("IAMDDB", "GB", "Manchester UK rapper"),  # audit wrong, she IS British
    ("Artie J", "US", "American artist"),
    ("West Gold", "US", "American hip-hop collective"),
    ("AG Club", "US", "Bay Area collective"),
    ("edbl", "GB", "British artist"),  # audit wrong
    ("The Dakota Wytefoxx", "US", "American artist"),
    ("Tona Glover", "US", "American artist"),
    ("Rich Brian", "US", "Indonesian-American, based in LA"),

    # US artists wrongly assigned to DE/CH/AT/HU/other
    ("Robert Glasper", "US", "Houston jazz/hip-hop artist"),
    ("DJ Pella", "US", "American DJ"),
    ("Jazzbois", "US", "American lo-fi collective"),
    ("Bluestaeb", "DE", "Actually German producer"),  # audit might be right, keep DE
    ("María Isabel", "US", "American pop singer"),

    # Korean artists wrongly assigned elsewhere
    ("j-hope", "KR", "BTS member, South Korean"),
    ("G-DRAGON", "KR", "Korean rapper/singer"),
    ("LISA", "KR", "BLACKPINK member, Thai but industry is KR"),

    # Nigerian artists wrongly assigned elsewhere
    ("Duncan Mighty", "NG", "Nigerian artist from Port Harcourt"),
    ("Khalil Harrison", "NG", "Nigerian artist"),
    ("Eric IV", "NG", "Nigerian artist"),
    ("Dope Caesar", "NG", "Nigerian producer"),
    ("Mannywellz", "NG", "Nigerian-American, NG origin"),
    ("Reefer Tym", "NG", "Nigerian artist"),
    ("YBNL MaFia Family", "NG", "YBNL Records, Nigerian label"),
    ("Team Salut", "NG", "Nigerian production team"),
    ("KENN FLENORY", "NG", "Nigerian artist"),
    ("Young Jonn", "NG", "Nigerian producer"),
    ("Nana Fofie", "NG", "Ghanaian-Nigerian"),
    ("P-Square", "NG", "Nigerian duo"),
    ("Chozen 1ne", "NG", "Nigerian artist"),
    ("Solo B", "NG", "Nigerian artist"),
    ("P. Montana", "NG", "Nigerian-British, NG origin"),

    # Indian artists wrongly assigned elsewhere
    ("Aditi Paul", "IN", "Indian playback singer"),
    ("Tony Kakkar", "IN", "Indian pop singer"),
    ("Danny Zee", "IN", "Indian artist"),
    ("Hunterz", "IN", "British-Indian, desi scene, keep GB"),  # actually keep GB
    ("Bombay Rockers", "IN", "Danish-Indian group, IN origin"),
    ("Roshan Prince", "IN", "Indian Punjabi singer"),
    ("Noor Tung", "IN", "Indian artist"),
    ("Adnan Sami", "IN", "Indian musician"),
    ("Monty Sharma", "IN", "Indian film composer"),
    ("Guri Sarhali", "IN", "Indian Punjabi artist"),
    ("Ricki Dhindsa", "IN", "Indian Punjabi artist"),
    ("Jawad Ahmad", "PK", "Pakistani singer"),  # should be PK not IN
    ("Ali Zafar", "PK", "Pakistani singer/actor"),
    ("Shafqat Amanat Ali", "PK", "Pakistani singer"),
    ("Quratulain Balouch", "PK", "Pakistani singer"),
    ("Sama Blake", "IN", "Indian artist"),

    # Ghanaian artists wrongly assigned elsewhere
    ("Amaarae", "GH", "Ghanaian-American, GH origin"),
    ("King Promise", "GH", "Ghanaian artist"),
    ("Stonebwoy", "GH", "Ghanaian dancehall artist"),
    ("Medikal", "GH", "Ghanaian rapper"),

    # South African artists
    ("Tyla", "ZA", "South African singer"),  # keep ZA
    ("Cassper Nyovest", "ZA", "South African rapper"),  # keep ZA
    ("Tshego", "ZA", "South African artist"),  # keep ZA
    ("Tyler ICU", "ZA", "South African amapiano producer"),
    ("TitoM", "ZA", "South African amapiano artist"),
    ("Shekhinah", "ZA", "South African singer"),

    # Jamaican artists wrongly assigned elsewhere
    ("Original Koffee", "JM", "Jamaican reggae artist"),
    ("Charly Black", "JM", "Jamaican dancehall artist"),
    ("J Capri", "JM", "Jamaican dancehall artist"),
    ("Wayne Wonder", "JM", "Jamaican reggae artist"),
    ("Stylo G", "JM", "Jamaican-British dancehall"),
    ("Sister Nancy", "JM", "Jamaican dancehall pioneer"),
    ("Kevin Lyttle", "KN", "From St. Vincent, keep KN"),  # audit wrong

    # Brazilian artists
    ("Vintage Culture", "BR", "Brazilian DJ/producer"),
    ("DJ Samir", "BR", "Brazilian funk DJ"),

    # French artists
    ("Soolking", "DZ", "Algerian rapper based in France"),  # keep DZ, that's correct
    ("Hamza", "BE", "Belgian rapper"),  # keep BE, that's correct
    ("Stromae", "BE", "Belgian artist"),  # keep BE

    # Other specific corrections
    ("Collie Buddz", "BM", "From Bermuda, not US"),  # actually from Bermuda
    ("Nasty C", "ZA", "South African rapper"),  # not NG
    ("Rayvanny", "TZ", "Tanzanian artist"),  # not NG
    ("Diamond Platnumz", "TZ", "Tanzanian artist"),
    ("Stefflon Don", "GB", "British rapper from Birmingham"),  # keep GB
    ("Rotimi", "US", "American, Nigerian descent"),  # keep US
    ("June Freedom", "US", "American artist"),
    ("Craig Isto", "GB", "British artist"),  # keep GB if that's correct
    ("Sinéad Harnett", "GB", "British singer"),  # she IS British
    ("Rejjie Snow", "IE", "Irish rapper"),  # keep IE
    ("Roy Woods", "CA", "Canadian from Brampton"),  # keep CA
    ("LON3R JOHNY", "PT", "Portuguese artist"),  # keep PT
    ("Aya Nakamura", "FR", "French artist"),  # keep FR

    # Mac Dre, Juicy J, Paul Wall - US rappers
    ("Mac Dre", "US", "Bay Area rapper from Vallejo"),
    ("Juicy J", "US", "Memphis rapper, Three 6 Mafia"),
    ("Paul Wall", "US", "Houston rapper"),
    ("Young Dolph", "US", "Memphis rapper"),

    # Other
    ("Bee Gees", "AU", "Australian-British group, formed in AU"),
    ("Alison Wonderland", "AU", "Australian DJ"),  # keep AU, audit wrong
    ("Ecco2k", "SE", "Swedish artist, Drain Gang"),  # keep SE
]


def main():
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    cur = conn.cursor()

    applied = 0
    skipped = 0
    not_found = 0

    for artist_name, target_iso, reason in CORRECTIONS:
        # Get country_id
        cur.execute("SELECT id FROM countries WHERE iso_alpha2 = %s", (target_iso,))
        row = cur.fetchone()
        if not row:
            print(f"COUNTRY NOT FOUND: {target_iso} for {artist_name}")
            continue
        country_id = row[0]

        # Check current assignment
        cur.execute("""
            SELECT a.id, c.iso_alpha2
            FROM artists a
            LEFT JOIN countries c ON a.country_id = c.id
            WHERE a.name = %s
        """, (artist_name,))
        artist_row = cur.fetchone()

        if not artist_row:
            not_found += 1
            continue

        artist_id, current_iso = artist_row
        if current_iso == target_iso:
            skipped += 1
            continue

        # Apply correction
        cur.execute("UPDATE artists SET country_id = %s WHERE id = %s", (country_id, artist_id))
        applied += 1
        print(f"FIXED  {artist_name}: {current_iso} -> {target_iso} ({reason})")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone: {applied} fixed, {skipped} already correct, {not_found} not found in DB")


if __name__ == '__main__':
    main()
