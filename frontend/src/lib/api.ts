// Server-side (Node.js in Docker): use internal Docker service name
// Client-side (browser): use localhost
function getBaseUrl(): string {
  if (typeof window === 'undefined') {
    // Server-side: prefer internal Docker URL, fall back to localhost
    return process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  }
  // Client-side: always use the public URL
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
}

export interface ArtistListItem {
  id: number;
  name: string;
  spotify_id: string | null;
  country_id: number | null;
  genres: string[] | null;
  popularity: number | null;
  image_url: string | null;
  track_count: number;
}

export interface TrackListItem {
  id: number;
  name: string;
  spotify_id: string;
  album_name: string | null;
  energy: number | null;
  danceability: number | null;
  valence: number | null;
  tempo: number | null;
  acousticness: number | null;
}

export interface CountryListItem {
  id: number;
  name: string;
  iso_alpha2: string;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  artist_count: number;
  track_count: number;
  top_genre: string | null;
}

export interface CountryDetail {
  id: number;
  name: string;
  iso_alpha2: string;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  artists: ArtistListItem[];
  genre_breakdown: Record<string, number>;
  audio_feature_averages: Record<string, number | null>;
  top_tracks: TrackListItem[];
}

export interface CountryComparison {
  id: number;
  name: string;
  iso_alpha2: string;
  country_averages: Record<string, number | null>;
  global_averages: Record<string, number | null>;
}

export async function fetchCountries(): Promise<CountryListItem[]> {
  const res = await fetch(`${getBaseUrl()}/api/countries`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch countries: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<CountryListItem[]>;
}

export async function fetchCountryDetail(id: number): Promise<CountryDetail> {
  const res = await fetch(`${getBaseUrl()}/api/countries/${id}`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch country detail for id ${id}: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<CountryDetail>;
}

export async function fetchCountryComparison(id: number): Promise<CountryComparison> {
  const res = await fetch(`${getBaseUrl()}/api/countries/${id}/comparison`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch country comparison for id ${id}: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<CountryComparison>;
}
