import dynamic from 'next/dynamic';
import { fetchCountries } from '@/lib/api';
import type { CountryListItem } from '@/lib/api';

const MapView = dynamic(() => import('@/components/MapView'), {
  ssr: false,
  loading: () => <div className="w-full h-screen bg-gray-950" />,
});

export default async function Home() {
  let countries: CountryListItem[] = [];

  try {
    countries = await fetchCountries();
  } catch (err) {
    console.error('Failed to fetch countries for map:', err);
  }

  return (
    <main className="w-full h-screen">
      <MapView countries={countries} />
    </main>
  );
}
