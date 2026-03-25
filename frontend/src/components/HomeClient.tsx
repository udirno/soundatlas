'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import type { CountryListItem } from '@/lib/api';
import CountryPanel from './CountryPanel';
import StatsSidebar from './StatsSidebar';
import SearchBar from './SearchBar';

// Dynamic import with ssr:false must be in a client component context
const MapView = dynamic(() => import('@/components/MapView'), {
  ssr: false,
  loading: () => <div className="w-full h-screen bg-gray-950" />,
});

interface HomeClientProps {
  countries: CountryListItem[];
}

export default function HomeClient({ countries }: HomeClientProps) {
  const [selectedCountryId, setSelectedCountryId] = useState<number | null>(null);
  const [flyToTarget, setFlyToTarget] = useState<{ lng: number; lat: number } | null>(null);

  const handleSearchSelect = useCallback((countryId: number) => {
    const country = countries.find((c) => c.id === countryId);
    if (country && country.latitude != null && country.longitude != null) {
      setFlyToTarget({ lng: country.longitude, lat: country.latitude });
    }
    setSelectedCountryId(countryId);
  }, [countries]);

  const handleFlyToComplete = useCallback(() => {
    setFlyToTarget(null);
  }, []);

  return (
    <main className="w-full h-screen relative">
      <StatsSidebar onCountrySelect={setSelectedCountryId} />
      <SearchBar onSelect={handleSearchSelect} />
      <MapView
        countries={countries}
        onCountrySelect={setSelectedCountryId}
        flyToTarget={flyToTarget}
        onFlyToComplete={handleFlyToComplete}
      />
      {selectedCountryId !== null && (
        <CountryPanel
          countryId={selectedCountryId}
          onClose={() => setSelectedCountryId(null)}
        />
      )}
    </main>
  );
}
