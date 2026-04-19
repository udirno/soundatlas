'use client';

import { useEffect, useState } from 'react';
import type { CountryDetail, CountryComparison, ArtistListItem } from '@/lib/api';
import { fetchCountryDetail, fetchCountryComparison } from '@/lib/api';
import GenrePieChart from '@/components/GenrePieChart';
import AudioFeatureChart from '@/components/AudioFeatureChart';

interface CountryPanelProps {
  countryId: number;
  onClose: () => void;
}

function ArtistRow({ artist }: { artist: ArtistListItem }) {
  const genres = artist.genres?.slice(0, 3) ?? [];
  const initial = artist.name.charAt(0).toUpperCase();

  return (
    <div className="flex items-center gap-3 py-2">
      {/* Avatar */}
      <div className="flex-shrink-0">
        {artist.image_url ? (
          <img
            src={artist.image_url}
            alt={artist.name}
            className="w-10 h-10 rounded-full object-cover"
          />
        ) : (
          <div className="w-10 h-10 rounded-full bg-gray-800 flex items-center justify-center text-gray-400 text-sm font-semibold">
            {initial}
          </div>
        )}
      </div>

      {/* Name + genres */}
      <div className="flex-1 min-w-0">
        <p className="text-gray-100 font-medium text-sm truncate">{artist.name}</p>
        {genres.length > 0 && (
          <p className="text-gray-500 text-xs truncate">{genres.join(', ')}</p>
        )}
      </div>

      {/* Track count badge */}
      <div className="flex-shrink-0">
        <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full whitespace-nowrap">
          {artist.track_count} {artist.track_count === 1 ? 'track' : 'tracks'}
        </span>
      </div>
    </div>
  );
}

export default function CountryPanel({ countryId, onClose }: CountryPanelProps) {
  const [countryDetail, setCountryDetail] = useState<CountryDetail | null>(null);
  const [comparison, setComparison] = useState<CountryComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAllArtists, setShowAllArtists] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setCountryDetail(null);
    setComparison(null);
    setShowAllArtists(false);

    Promise.all([
      fetchCountryDetail(countryId),
      fetchCountryComparison(countryId),
    ])
      .then(([detail, comp]) => {
        setCountryDetail(detail);
        setComparison(comp);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Failed to load country data';
        setError(message);
        console.error('CountryPanel fetch error:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [countryId]);

  function doRetry() {
    setError(null);
    setLoading(true);
    Promise.all([
      fetchCountryDetail(countryId),
      fetchCountryComparison(countryId),
    ])
      .then(([detail, comp]) => {
        setCountryDetail(detail);
        setComparison(comp);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Failed to load country data';
        setError(message);
      })
      .finally(() => setLoading(false));
  }

  return (
    <div className="fixed top-0 right-0 h-screen w-96 bg-gray-950 border-l border-gray-800 overflow-y-auto z-50 shadow-2xl">
      {/* Header */}
      <div className="flex items-start justify-between p-6 border-b border-gray-800">
        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="h-7 w-32 bg-gray-800 animate-pulse rounded" />
          ) : (
            <>
              <h2 className="text-xl font-bold text-gray-100 truncate">
                {countryDetail?.name ?? 'Country'}
              </h2>
              {countryDetail?.region && (
                <p className="text-sm text-gray-400 mt-0.5">{countryDetail.region}</p>
              )}
              {countryDetail?.iso_alpha2 && (
                <span className="inline-block mt-1 px-2 py-0.5 text-xs font-mono bg-gray-800 text-gray-300 rounded">
                  {countryDetail.iso_alpha2}
                </span>
              )}
            </>
          )}
        </div>
        <button
          onClick={onClose}
          aria-label="Close panel"
          className="ml-4 flex-shrink-0 p-1.5 text-gray-400 hover:text-gray-100 hover:bg-gray-800 rounded transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="p-5 space-y-6">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <span className="text-gray-400 text-sm">Loading...</span>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-md bg-red-900/30 border border-red-700 p-4">
            <p className="text-sm text-red-400">{error}</p>
            <button
              onClick={doRetry}
              className="mt-2 text-xs text-red-300 hover:text-red-100 underline"
            >
              Retry
            </button>
          </div>
        )}

        {countryDetail && !loading && (
          <>
            {/* ---- Artist List (CTRY-02) ---- */}
            <section>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Artists ({countryDetail.artists.length})
              </h3>
              {(() => {
                const sortedArtists = [...countryDetail.artists].sort(
                  (a, b) => (b.track_count ?? 0) - (a.track_count ?? 0)
                );
                const displayArtists = showAllArtists
                  ? sortedArtists
                  : sortedArtists.slice(0, 10);

                return (
                  <>
                    <div>
                      {displayArtists.map((artist) => (
                        <ArtistRow key={artist.id} artist={artist} />
                      ))}
                    </div>
                    {sortedArtists.length > 10 && (
                      <button
                        onClick={() => setShowAllArtists((prev) => !prev)}
                        className="mt-2 text-xs text-gray-400 hover:text-gray-200 underline"
                      >
                        {showAllArtists
                          ? 'Show fewer artists'
                          : `Show all ${sortedArtists.length} artists`}
                      </button>
                    )}
                  </>
                );
              })()}
            </section>

            {/* ---- Genre Breakdown (CTRY-03) ---- */}
            <section className="border-t border-gray-800 pt-4 mt-4">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Genre Breakdown
              </h3>
              <GenrePieChart data={countryDetail.genre_breakdown} />
            </section>

            {/* ---- Audio Features (CTRY-04) ---- */}
            <section className="border-t border-gray-800 pt-4 mt-4">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Audio Features
              </h3>
              {comparison ? (
                <AudioFeatureChart
                  countryAverages={comparison.country_averages}
                  globalAverages={comparison.global_averages}
                />
              ) : (
                <div className="flex items-center justify-center h-16 text-gray-500 text-sm">
                  Loading audio features...
                </div>
              )}
            </section>

            {/* ---- Top Tracks (CTRY-05) ---- */}
            <section className="border-t border-gray-800 pt-4 mt-4">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Top Tracks
              </h3>
              {countryDetail.top_tracks.length === 0 ? (
                <p className="text-gray-500 text-sm">No tracks available for this country.</p>
              ) : (
                <ul className="space-y-3">
                  {countryDetail.top_tracks.map((track) => (
                    <li key={track.id} className="flex flex-col">
                      <span className="text-gray-100 text-sm font-medium leading-snug">
                        {track.name}
                      </span>
                      {track.album_name && track.album_name !== track.name && (
                        <span className="text-gray-400 text-xs mt-0.5">
                          {track.album_name}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
