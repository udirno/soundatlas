import { fetchCountries } from '@/lib/api';
import type { CountryListItem } from '@/lib/api';
import HomeClient from '@/components/HomeClient';

export default async function Home() {
  let countries: CountryListItem[] = [];

  try {
    countries = await fetchCountries();
  } catch (err) {
    console.error('Failed to fetch countries for map:', err);
  }

  return <HomeClient countries={countries} />;
}
