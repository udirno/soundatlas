'use client';

import { useEffect, useState } from 'react';
import type { CountryDetail, CountryComparison } from '@/lib/api';
import { fetchCountryDetail, fetchCountryComparison } from '@/lib/api';

interface CountryPanelProps {
  countryId: number;
  onClose: () => void;
}

export default function CountryPanel({ countryId, onClose }: CountryPanelProps) {
  const [countryDetail, setCountryDetail] = useState<CountryDetail | null>(null);
  const [comparison, setComparison] = useState<CountryComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setCountryDetail(null);
    setComparison(null);

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
      <div className="p-6 space-y-6">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <span className="text-gray-400 text-sm">Loading...</span>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-md bg-red-900/30 border border-red-700 p-4">
            <p className="text-sm text-red-400">{error}</p>
            <button
              onClick={() => {
                // Re-trigger by resetting error — useEffect won't re-run unless countryId changes.
                // Force re-fetch by temporarily resetting state; parent can also re-click.
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
              }}
              className="mt-2 text-xs text-red-300 hover:text-red-100 underline"
            >
              Retry
            </button>
          </div>
        )}

        {countryDetail && !loading && (
          <>
            {/* Artists section */}
            <section>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Artists
              </h3>
              <p className="text-gray-400 text-sm">
                {countryDetail.artists.length} artists
              </p>
            </section>

            {/* Genre Breakdown section */}
            <section>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Genre Breakdown
              </h3>
              <p className="text-gray-500 text-sm italic">Genre chart coming soon</p>
            </section>

            {/* Audio Features section */}
            <section>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Audio Features
              </h3>
              <p className="text-gray-500 text-sm italic">Audio feature chart coming soon</p>
            </section>

            {/* Top Tracks section */}
            <section>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Top Tracks
              </h3>
              <p className="text-gray-500 text-sm italic">Top tracks coming soon</p>
            </section>
          </>
        )}
      </div>

      {/* comparison data available for Plan 03 charts (audio features, genre comparison) */}
      {/* comparison state is fetched but used in Phase 03 plans */}
    </div>
  );
}
