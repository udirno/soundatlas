'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import type { CountryListItem } from '@/lib/api';
import CountryPanel from './CountryPanel';

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

  return (
    <main className="w-full h-screen">
      <MapView countries={countries} onCountrySelect={setSelectedCountryId} />
      {selectedCountryId !== null && (
        <CountryPanel
          countryId={selectedCountryId}
          onClose={() => setSelectedCountryId(null)}
        />
      )}
    </main>
  );
}
