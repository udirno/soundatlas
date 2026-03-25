'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { MessageSquare } from 'lucide-react';
import type { CountryListItem } from '@/lib/api';
import CountryPanel from './CountryPanel';
import StatsSidebar from './StatsSidebar';
import SearchBar from './SearchBar';
import AIChatPanel from './AIChatPanel';

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
  const [isChatOpen, setIsChatOpen] = useState(false);

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
      {isChatOpen ? (
        <AIChatPanel onClose={() => setIsChatOpen(false)} />
      ) : (
        <button
          onClick={() => setIsChatOpen(true)}
          className="fixed bottom-4 right-4 z-40 w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg flex items-center justify-center transition-colors"
          aria-label="Open AI chat"
        >
          <MessageSquare size={24} />
        </button>
      )}
    </main>
  );
}
