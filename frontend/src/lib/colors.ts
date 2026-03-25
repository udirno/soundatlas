export const GENRE_COLORS: Record<string, string> = {
  'pop': '#f43f5e',
  'hip hop': '#f97316',
  'rap': '#f97316',
  'trap': '#f97316',
  'grime': '#f97316',
  'rock': '#8b5cf6',
  'electronic': '#06b6d4',
  'edm': '#06b6d4',
  'house': '#06b6d4',
  'techno': '#06b6d4',
  'bass': '#06b6d4',
  'r&b': '#10b981',
  'soul': '#facc15',
  'latin': '#eab308',
  'reggaeton': '#eab308',
  'reggae': '#eab308',
  'soca': '#eab308',
  'afrobeats': '#f59e0b',
  'afro': '#f59e0b',
  'bhangra': '#e879f9',
  'bollywood': '#e879f9',
  'sufi': '#e879f9',
  'country': '#a3e635',
  'folk': '#a3e635',
  'metal': '#dc2626',
  'punk': '#dc2626',
  'jazz': '#d946ef',
  'classical': '#2dd4bf',
  'indie': '#fb923c',
  'funk': '#8b5cf6',
};

export const FALLBACK_COLOR = '#94a3b8';

export function getGenreColor(genre: string): string {
  const lower = genre.toLowerCase();
  for (const [key, color] of Object.entries(GENRE_COLORS)) {
    if (lower.includes(key)) return color;
  }
  return FALLBACK_COLOR;
}

/**
 * Builds a Mapbox `match` expression for circle-color based on GENRE_COLORS.
 * Usage in layer paint: 'circle-color': buildMapboxColorExpression()
 */
export function buildMapboxColorExpression(): unknown[] {
  const expr: unknown[] = ['match', ['get', 'top_genre']];
  for (const [genre, color] of Object.entries(GENRE_COLORS)) {
    expr.push(genre, color);
  }
  // fallback color
  expr.push(FALLBACK_COLOR);
  return expr;
}
