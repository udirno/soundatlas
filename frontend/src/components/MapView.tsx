'use client';

import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

import type { CountryListItem } from '@/lib/api';
import { GENRE_COLORS, FALLBACK_COLOR } from '@/lib/colors';

interface MapViewProps {
  countries: CountryListItem[];
  onCountrySelect?: (countryId: number) => void;
}

interface CountryFeatureProperties {
  id: number;
  name: string;
  track_count: number;
  artist_count: number;
  top_genre: string;
}

function toGeoJSON(
  countries: CountryListItem[]
): GeoJSON.FeatureCollection<GeoJSON.Point, CountryFeatureProperties> {
  const features: GeoJSON.Feature<GeoJSON.Point, CountryFeatureProperties>[] = countries
    .filter((c) => c.latitude != null && c.longitude != null)
    .map((c) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [c.longitude as number, c.latitude as number],
      },
      properties: {
        id: c.id,
        name: c.name,
        track_count: c.track_count,
        artist_count: c.artist_count,
        top_genre: c.top_genre ?? 'Unknown',
      },
    }));

  return { type: 'FeatureCollection', features };
}

/**
 * Build a Mapbox match expression for circle-color from GENRE_COLORS.
 * Adding a genre to colors.ts automatically updates the map layer.
 */
function buildCircleColorExpression(): mapboxgl.Expression {
  const expr: unknown[] = ['match', ['get', 'top_genre']];
  for (const [genre, color] of Object.entries(GENRE_COLORS)) {
    expr.push(genre, color);
  }
  expr.push(FALLBACK_COLOR);
  return expr as mapboxgl.Expression;
}

export default function MapView({ countries, onCountrySelect }: MapViewProps) {
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
      projection: { name: 'mercator' },
    });

    const geojson = toGeoJSON(countries);

    map.current.on('load', () => {
      if (!map.current) return;

      map.current.addSource('countries', {
        type: 'geojson',
        data: geojson,
      });

      map.current.addLayer({
        id: 'country-circles',
        type: 'circle',
        source: 'countries',
        paint: {
          // Radius proportional to sqrt(track_count): sqrt scaling keeps large countries visible
          // without completely overwhelming small ones
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['sqrt', ['get', 'track_count']],
            0, 4,
            Math.sqrt(50), 12,
            Math.sqrt(100), 20,
            Math.sqrt(500), 36,
          ],
          'circle-color': buildCircleColorExpression(),
          'circle-opacity': 0.85,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-opacity': 0.3,
        },
      });

      // Click handler
      if (onCountrySelect) {
        map.current.on('click', 'country-circles', (e) => {
          if (e.features && e.features[0]) {
            const props = e.features[0].properties as CountryFeatureProperties;
            onCountrySelect(props.id);
          }
        });

        map.current.on('mouseenter', 'country-circles', () => {
          if (map.current) map.current.getCanvas().style.cursor = 'pointer';
        });

        map.current.on('mouseleave', 'country-circles', () => {
          if (map.current) map.current.getCanvas().style.cursor = '';
        });
      }
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
    // countries is intentionally excluded — map is initialized once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={mapContainer} className="w-full h-screen" />;
}
