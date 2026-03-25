export const GENRE_COLORS: Record<string, string> = {
  'pop': '#f43f5e',
  'hip hop': '#f97316',
  'rock': '#8b5cf6',
  'electronic': '#06b6d4',
  'r&b': '#10b981',
  'latin': '#eab308',
  'country': '#a3e635',
  'metal': '#dc2626',
  'jazz': '#d946ef',
  'classical': '#2dd4bf',
  'indie': '#fb923c',
  'soul': '#facc15',
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
