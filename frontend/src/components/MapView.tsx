'use client';

import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

import type { CountryListItem } from '@/lib/api';
import { getGenreColor } from '@/lib/colors';

interface MapViewProps {
  countries: CountryListItem[];
  onCountrySelect?: (countryId: number) => void;
  flyToTarget?: { lng: number; lat: number } | null;
  onFlyToComplete?: () => void;
}

interface CountryFeatureProperties {
  id: number;
  name: string;
  track_count: number;
  artist_count: number;
  top_genre: string;
  genre_color: string;
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
        genre_color: getGenreColor(c.top_genre ?? ''),
      },
    }));

  return { type: 'FeatureCollection', features };
}


export default function MapView({ countries, onCountrySelect, flyToTarget, onFlyToComplete }: MapViewProps) {
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

    // Tooltip instance — created outside load callback, lives for map lifetime
    const tooltip = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: [0, -12],
    });

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
          'circle-radius': [
            'step', ['get', 'track_count'],
            4,
            10, 6,
            50, 10,
            150, 14,
            500, 18,
            1500, 22,
            3000, 26,
            5000, 30,
          ],
          'circle-color': ['get', 'genre_color'],
          'circle-opacity': 0.85,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-opacity': 0.3,
        },
      });

      // Hover tooltip
      map.current.on('mousemove', 'country-circles', (e) => {
        if (!map.current || !e.features || !e.features[0]) return;

        map.current.getCanvas().style.cursor = 'pointer';

        const rawFeature = e.features[0];
        const props = rawFeature.properties as CountryFeatureProperties;
        const coordinates = (rawFeature.geometry as GeoJSON.Point).coordinates as [number, number];

        const topGenre = props.top_genre ?? 'Unknown';
        const html = `
          <div style="font-weight:600;font-size:13px;margin-bottom:3px;color:#f1f5f9">${props.name}</div>
          <div style="font-size:11px;color:#94a3b8">${props.artist_count} artists &middot; ${topGenre}</div>
        `;

        tooltip.setLngLat(coordinates).setHTML(html).addTo(map.current);
      });

      map.current.on('mouseleave', 'country-circles', () => {
        if (map.current) map.current.getCanvas().style.cursor = '';
        tooltip.remove();
      });

      // Click-to-fly + country selection
      map.current.on('click', 'country-circles', (e) => {
        if (!map.current || !e.features || !e.features[0]) return;

        const rawFeature = e.features[0];
        const props = rawFeature.properties as CountryFeatureProperties;
        const coords = (rawFeature.geometry as GeoJSON.Point).coordinates as [number, number];

        map.current.flyTo({
          center: coords,
          zoom: Math.max(map.current.getZoom(), 4),
          duration: 1200,
        });

        onCountrySelect?.(props.id);
      });
    });

    return () => {
      tooltip.remove();
      map.current?.remove();
      map.current = null;
    };
    // countries is intentionally excluded — map is initialized once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map.current) return;
    const m = map.current;
    const data = toGeoJSON(countries);
    const apply = () => {
      const src = m.getSource('countries') as mapboxgl.GeoJSONSource | undefined;
      if (src) src.setData(data);
    };
    if (m.isStyleLoaded() && m.getSource('countries')) apply();
    else m.once('load', apply);
  }, [countries]);

  // Fly to a target when flyToTarget prop changes
  useEffect(() => {
    if (!flyToTarget || !map.current) return;
    const m = map.current;
    m.flyTo({
      center: [flyToTarget.lng, flyToTarget.lat],
      zoom: Math.max(m.getZoom(), 4),
      duration: 1200,
    });
    // Clear flyToTarget after animation completes to avoid stale state
    m.once('moveend', () => {
      onFlyToComplete?.();
    });
  }, [flyToTarget, onFlyToComplete]);

  return <div ref={mapContainer} className="w-full h-screen" />;
}
