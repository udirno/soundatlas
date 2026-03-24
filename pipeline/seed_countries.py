#!/usr/bin/env python3
"""
seed_countries.py — Seed the countries table from pycountry data.

Inserts all pycountry entries (~249) into the countries table with
ISO alpha-2 codes and approximate centroid coordinates for UN member
states and common territories.

Usage:
    python pipeline/seed_countries.py [--env-file /path/to/.env]

Run from the project root directory.

If a local PostgreSQL is running on port 5432 and shadowing the Docker instance,
use the POSTGRES_HOST environment variable to override:

    POSTGRES_HOST=postgres docker run --rm --network soundatlas_soundatlas_network \\
        -e POSTGRES_USER=soundatlas_user \\
        -e POSTGRES_PASSWORD=soundatlas_password \\
        -e POSTGRES_HOST=postgres \\
        -e POSTGRES_DB=soundatlas_db \\
        python:3.11-slim bash -c "pip install pycountry psycopg2-binary python-dotenv && python seed_countries.py"

Or set SYNC_DATABASE_URL to point directly to the Docker postgres.
"""

import argparse
import os
import sys

import psycopg2
from dotenv import load_dotenv

# Approximate geographic centroids (latitude, longitude) for countries.
# Covers all 193 UN member states plus common territories that appear in music libraries.
# Coordinates rounded to 2 decimal places — intended for map marker placement, not precision.
COUNTRY_CENTROIDS = {
    "AD": (42.55, 1.57),     # Andorra
    "AE": (24.00, 54.00),    # United Arab Emirates
    "AF": (33.00, 65.00),    # Afghanistan
    "AG": (17.05, -61.80),   # Antigua and Barbuda
    "AI": (18.22, -63.05),   # Anguilla
    "AL": (41.00, 20.00),    # Albania
    "AM": (40.00, 45.00),    # Armenia
    "AO": (-11.20, 17.87),   # Angola
    "AQ": (-75.25, -0.07),   # Antarctica
    "AR": (-34.00, -64.00),  # Argentina
    "AS": (-14.33, -170.00), # American Samoa
    "AT": (47.33, 13.33),    # Austria
    "AU": (-25.00, 135.00),  # Australia
    "AW": (12.52, -69.97),   # Aruba
    "AZ": (40.50, 47.50),    # Azerbaijan
    "BA": (44.00, 17.00),    # Bosnia and Herzegovina
    "BB": (13.17, -59.53),   # Barbados
    "BD": (24.00, 90.00),    # Bangladesh
    "BE": (50.83, 4.00),     # Belgium
    "BF": (13.00, -2.00),    # Burkina Faso
    "BG": (43.00, 25.00),    # Bulgaria
    "BH": (26.00, 50.55),    # Bahrain
    "BI": (-3.50, 30.00),    # Burundi
    "BJ": (9.50, 2.25),      # Benin
    "BL": (17.90, -62.83),   # Saint Barthelemy
    "BM": (32.33, -64.75),   # Bermuda
    "BN": (4.50, 114.67),    # Brunei
    "BO": (-17.00, -65.00),  # Bolivia
    "BQ": (12.18, -68.25),   # Bonaire, Sint Eustatius and Saba
    "BR": (-10.00, -55.00),  # Brazil
    "BS": (24.25, -76.00),   # Bahamas
    "BT": (27.50, 90.50),    # Bhutan
    "BV": (-54.43, 3.40),    # Bouvet Island
    "BW": (-22.00, 24.00),   # Botswana
    "BY": (53.00, 28.00),    # Belarus
    "BZ": (17.25, -88.75),   # Belize
    "CA": (60.00, -95.00),   # Canada
    "CC": (-12.17, 96.83),   # Cocos (Keeling) Islands
    "CD": (-2.50, 23.83),    # Congo, Democratic Republic
    "CF": (7.00, 21.00),     # Central African Republic
    "CG": (-1.00, 15.00),    # Congo
    "CH": (47.00, 8.00),     # Switzerland
    "CI": (8.00, -5.00),     # Ivory Coast
    "CK": (-21.23, -159.78), # Cook Islands
    "CL": (-30.00, -71.00),  # Chile
    "CM": (6.00, 12.00),     # Cameroon
    "CN": (35.00, 105.00),   # China
    "CO": (4.00, -72.00),    # Colombia
    "CR": (10.00, -84.00),   # Costa Rica
    "CU": (22.00, -79.50),   # Cuba
    "CV": (16.00, -24.00),   # Cape Verde
    "CW": (12.17, -68.93),   # Curacao
    "CX": (-10.50, 105.67),  # Christmas Island
    "CY": (35.00, 33.00),    # Cyprus
    "CZ": (49.75, 15.50),    # Czech Republic
    "DE": (51.00, 9.00),     # Germany
    "DJ": (11.50, 43.00),    # Djibouti
    "DK": (56.00, 10.00),    # Denmark
    "DM": (15.42, -61.33),   # Dominica
    "DO": (19.00, -70.67),   # Dominican Republic
    "DZ": (28.00, 3.00),     # Algeria
    "EC": (-2.00, -77.50),   # Ecuador
    "EE": (59.00, 26.00),    # Estonia
    "EG": (27.00, 30.00),    # Egypt
    "EH": (24.50, -13.00),   # Western Sahara
    "ER": (15.00, 39.00),    # Eritrea
    "ES": (40.00, -4.00),    # Spain
    "ET": (8.00, 38.00),     # Ethiopia
    "FI": (64.00, 26.00),    # Finland
    "FJ": (-18.00, 175.00),  # Fiji
    "FK": (-51.75, -59.17),  # Falkland Islands
    "FM": (6.92, 158.18),    # Micronesia
    "FO": (62.00, -7.00),    # Faroe Islands
    "FR": (46.00, 2.00),     # France
    "GA": (-1.00, 11.75),    # Gabon
    "GB": (54.00, -2.00),    # United Kingdom
    "GD": (12.12, -61.67),   # Grenada
    "GE": (42.00, 43.50),    # Georgia
    "GF": (4.00, -53.00),    # French Guiana
    "GG": (49.47, -2.57),    # Guernsey
    "GH": (8.00, -2.00),     # Ghana
    "GI": (36.14, -5.35),    # Gibraltar
    "GL": (72.00, -40.00),   # Greenland
    "GM": (13.47, -16.57),   # Gambia
    "GN": (11.00, -10.00),   # Guinea
    "GP": (16.25, -61.58),   # Guadeloupe
    "GQ": (2.00, 10.00),     # Equatorial Guinea
    "GR": (39.00, 22.00),    # Greece
    "GS": (-54.50, -37.00),  # S. Georgia and S. Sandwich Islands
    "GT": (15.50, -90.25),   # Guatemala
    "GU": (13.47, 144.78),   # Guam
    "GW": (12.00, -15.00),   # Guinea-Bissau
    "GY": (5.00, -59.00),    # Guyana
    "HK": (22.25, 114.17),   # Hong Kong
    "HM": (-53.10, 72.52),   # Heard Island and McDonald Islands
    "HN": (15.00, -86.50),   # Honduras
    "HR": (45.17, 15.50),    # Croatia
    "HT": (19.00, -72.42),   # Haiti
    "HU": (47.00, 20.00),    # Hungary
    "ID": (-5.00, 120.00),   # Indonesia
    "IE": (53.00, -8.00),    # Ireland
    "IL": (31.50, 34.75),    # Israel
    "IM": (54.25, -4.50),    # Isle of Man
    "IN": (20.00, 77.00),    # India
    "IO": (-6.00, 71.50),    # British Indian Ocean Territory
    "IQ": (33.00, 44.00),    # Iraq
    "IR": (32.00, 53.00),    # Iran
    "IS": (65.00, -18.00),   # Iceland
    "IT": (42.83, 12.83),    # Italy
    "JE": (49.22, -2.13),    # Jersey
    "JM": (18.25, -77.50),   # Jamaica
    "JO": (31.00, 36.00),    # Jordan
    "JP": (36.00, 138.00),   # Japan
    "KE": (1.00, 38.00),     # Kenya
    "KG": (41.00, 75.00),    # Kyrgyzstan
    "KH": (13.00, 105.00),   # Cambodia
    "KI": (1.42, 173.00),    # Kiribati
    "KM": (-12.17, 44.25),   # Comoros
    "KN": (17.33, -62.75),   # Saint Kitts and Nevis
    "KP": (40.00, 127.00),   # North Korea
    "KR": (37.00, 127.50),   # South Korea
    "KW": (29.34, 47.66),    # Kuwait
    "KY": (19.50, -80.50),   # Cayman Islands
    "KZ": (48.00, 68.00),    # Kazakhstan
    "LA": (18.00, 105.00),   # Laos
    "LB": (33.83, 35.83),    # Lebanon
    "LC": (13.88, -60.97),   # Saint Lucia
    "LI": (47.17, 9.53),     # Liechtenstein
    "LK": (7.00, 81.00),     # Sri Lanka
    "LR": (6.50, -9.50),     # Liberia
    "LS": (-29.50, 28.50),   # Lesotho
    "LT": (56.00, 24.00),    # Lithuania
    "LU": (49.75, 6.17),     # Luxembourg
    "LV": (57.00, 25.00),    # Latvia
    "LY": (25.00, 17.00),    # Libya
    "MA": (32.00, -5.00),    # Morocco
    "MC": (43.73, 7.40),     # Monaco
    "MD": (47.00, 29.00),    # Moldova
    "ME": (42.50, 19.30),    # Montenegro
    "MF": (18.08, -63.95),   # Saint Martin (French part)
    "MG": (-20.00, 47.00),   # Madagascar
    "MH": (9.00, 168.00),    # Marshall Islands
    "MK": (41.83, 22.00),    # North Macedonia
    "ML": (17.00, -4.00),    # Mali
    "MM": (22.00, 98.00),    # Myanmar
    "MN": (46.00, 105.00),   # Mongolia
    "MO": (22.17, 113.55),   # Macao
    "MP": (15.20, 145.75),   # Northern Mariana Islands
    "MQ": (14.67, -61.00),   # Martinique
    "MR": (20.00, -12.00),   # Mauritania
    "MS": (16.75, -62.20),   # Montserrat
    "MT": (35.83, 14.58),    # Malta
    "MU": (-20.28, 57.55),   # Mauritius
    "MV": (3.25, 73.00),     # Maldives
    "MW": (-13.50, 34.00),   # Malawi
    "MX": (23.00, -102.00),  # Mexico
    "MY": (2.50, 112.50),    # Malaysia
    "MZ": (-18.25, 35.00),   # Mozambique
    "NA": (-22.00, 17.00),   # Namibia
    "NC": (-21.50, 165.50),  # New Caledonia
    "NE": (16.00, 8.00),     # Niger
    "NF": (-29.04, 167.95),  # Norfolk Island
    "NG": (10.00, 8.00),     # Nigeria
    "NI": (13.00, -85.00),   # Nicaragua
    "NL": (52.25, 5.75),     # Netherlands
    "NO": (62.00, 10.00),    # Norway
    "NP": (28.00, 84.00),    # Nepal
    "NR": (-0.53, 166.92),   # Nauru
    "NU": (-19.02, -169.87), # Niue
    "NZ": (-41.00, 174.00),  # New Zealand
    "OM": (22.00, 58.00),    # Oman
    "PA": (9.00, -80.00),    # Panama
    "PE": (-10.00, -76.00),  # Peru
    "PF": (-15.00, -140.00), # French Polynesia
    "PG": (-6.00, 147.00),   # Papua New Guinea
    "PH": (13.00, 122.00),   # Philippines
    "PK": (30.00, 70.00),    # Pakistan
    "PL": (52.00, 20.00),    # Poland
    "PM": (46.83, -56.33),   # Saint Pierre and Miquelon
    "PN": (-25.07, -130.10), # Pitcairn
    "PR": (18.25, -66.50),   # Puerto Rico
    "PS": (32.00, 35.25),    # Palestinian Territory
    "PT": (39.50, -8.00),    # Portugal
    "PW": (7.50, 134.50),    # Palau
    "PY": (-23.00, -58.00),  # Paraguay
    "QA": (25.50, 51.25),    # Qatar
    "RE": (-21.12, 55.53),   # Reunion
    "RO": (46.00, 25.00),    # Romania
    "RS": (44.00, 21.00),    # Serbia
    "RU": (60.00, 100.00),   # Russia
    "RW": (-2.00, 30.00),    # Rwanda
    "SA": (25.00, 45.00),    # Saudi Arabia
    "SB": (-8.00, 159.00),   # Solomon Islands
    "SC": (-4.68, 55.47),    # Seychelles
    "SD": (15.00, 30.00),    # Sudan
    "SE": (62.00, 15.00),    # Sweden
    "SG": (1.37, 103.80),    # Singapore
    "SH": (-15.93, -5.72),   # Saint Helena
    "SI": (46.12, 14.82),    # Slovenia
    "SJ": (78.00, 20.00),    # Svalbard and Jan Mayen
    "SK": (48.67, 19.50),    # Slovakia
    "SL": (8.50, -11.50),    # Sierra Leone
    "SM": (43.94, 12.46),    # San Marino
    "SN": (14.00, -14.00),   # Senegal
    "SO": (10.00, 49.00),    # Somalia
    "SR": (4.00, -56.00),    # Suriname
    "SS": (8.00, 30.00),     # South Sudan
    "ST": (1.00, 7.00),      # Sao Tome and Principe
    "SV": (13.83, -88.92),   # El Salvador
    "SX": (18.03, -63.07),   # Sint Maarten
    "SY": (35.00, 38.00),    # Syria
    "SZ": (-26.50, 31.50),   # Eswatini
    "TC": (21.75, -71.58),   # Turks and Caicos Islands
    "TD": (15.00, 19.00),    # Chad
    "TF": (-49.25, 69.17),   # French Southern Territories
    "TG": (8.00, 1.17),      # Togo
    "TH": (15.00, 101.00),   # Thailand
    "TJ": (39.00, 71.00),    # Tajikistan
    "TK": (-9.00, -171.84),  # Tokelau
    "TL": (-8.55, 125.58),   # Timor-Leste
    "TM": (40.00, 60.00),    # Turkmenistan
    "TN": (34.00, 9.00),     # Tunisia
    "TO": (-20.00, -175.00), # Tonga
    "TR": (39.00, 35.00),    # Turkey
    "TT": (11.00, -61.00),   # Trinidad and Tobago
    "TV": (-8.00, 178.00),   # Tuvalu
    "TW": (23.50, 121.00),   # Taiwan
    "TZ": (-6.00, 35.00),    # Tanzania
    "UA": (49.00, 32.00),    # Ukraine
    "UG": (1.00, 32.00),     # Uganda
    "UM": (19.28, 166.60),   # U.S. Minor Outlying Islands
    "US": (38.00, -97.00),   # United States
    "UY": (-33.00, -56.00),  # Uruguay
    "UZ": (41.00, 64.00),    # Uzbekistan
    "VA": (41.90, 12.45),    # Vatican City
    "VC": (13.25, -61.20),   # Saint Vincent and the Grenadines
    "VE": (8.00, -66.00),    # Venezuela
    "VG": (18.43, -64.62),   # British Virgin Islands
    "VI": (18.34, -64.93),   # U.S. Virgin Islands
    "VN": (16.17, 107.83),   # Vietnam
    "VU": (-16.00, 167.00),  # Vanuatu
    "WF": (-13.30, -176.20), # Wallis and Futuna
    "WS": (-13.58, -172.33), # Samoa
    "XK": (42.67, 21.17),    # Kosovo (not in pycountry as sovereign, but common)
    "YE": (15.00, 48.00),    # Yemen
    "YT": (-12.83, 45.17),   # Mayotte
    "ZA": (-29.00, 25.00),   # South Africa
    "ZM": (-14.00, 28.00),   # Zambia
    "ZW": (-20.00, 30.00),   # Zimbabwe
}


def build_sync_db_url(env_file: str) -> str:
    """Build a psycopg2-compatible sync connection URL from environment."""
    load_dotenv(env_file, override=False)

    # Try SYNC_DATABASE_URL override first
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    # Build from individual components (preferred)
    user = os.getenv("POSTGRES_USER", "soundatlas_user")
    password = os.getenv("POSTGRES_PASSWORD", "soundatlas_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "soundatlas_db")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def seed_countries(db_url: str) -> None:
    """Seed the countries table from pycountry data."""
    try:
        import pycountry
    except ImportError:
        print("Error: pycountry not installed. Run: pip install pycountry", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    conn.autocommit = False

    try:
        cur = conn.cursor()

        countries = list(pycountry.countries)
        new_count = 0
        existing_count = 0

        for country in countries:
            name = country.name
            iso_alpha2 = country.alpha_2
            centroid = COUNTRY_CENTROIDS.get(iso_alpha2)
            latitude = centroid[0] if centroid else None
            longitude = centroid[1] if centroid else None

            cur.execute(
                """
                INSERT INTO countries (name, iso_alpha2, latitude, longitude)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (iso_alpha2) DO NOTHING
                """,
                (name, iso_alpha2, latitude, longitude),
            )

            if cur.rowcount == 1:
                new_count += 1
            else:
                existing_count += 1

        conn.commit()
        total = new_count + existing_count
        print(f"Seeded {total} countries ({new_count} new, {existing_count} existing)")

    except Exception as e:
        conn.rollback()
        print(f"Error seeding countries: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed countries table from pycountry data")
    parser.add_argument(
        "--env-file",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        help="Path to .env file (defaults to project root .env)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.env_file):
        print(f"Warning: .env file not found at {args.env_file}", file=sys.stderr)

    db_url = build_sync_db_url(args.env_file)
    seed_countries(db_url)


if __name__ == "__main__":
    main()
