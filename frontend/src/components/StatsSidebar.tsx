'use client';

import { useEffect, useState } from 'react';
import { fetchDashboard, DashboardStats } from '@/lib/api';

interface StatsSidebarProps {
  onCountrySelect: (countryId: number) => void;
}

export default function StatsSidebar({ onCountrySelect }: StatsSidebarProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchDashboard()
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  const diversityDisplay = stats ? (stats.diversity_score * 10).toFixed(1) : null;
  const diversityColor = diversityDisplay
    ? parseFloat(diversityDisplay) >= 7
      ? 'text-green-400'
      : parseFloat(diversityDisplay) >= 4
        ? 'text-yellow-400'
        : 'text-red-400'
    : '';
  const diversityBarWidth = stats ? `${Math.min(stats.diversity_score * 10 * 10, 100)}%` : '0%';

  return (
    <aside className="fixed top-0 left-0 h-screen w-72 bg-gray-950/95 backdrop-blur-sm border-r border-gray-800 z-40 overflow-y-auto">
      <div className="p-5">
        {/* Header */}
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">
          Library Stats
        </h2>

        {loading && (
          <div className="space-y-3 animate-pulse">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 bg-gray-800 rounded" />
            ))}
          </div>
        )}

        {error && !loading && (
          <p className="text-gray-500 text-sm">Stats unavailable</p>
        )}

        {!loading && !error && stats && (
          <>
            {/* Key Metrics */}
            <div className="grid grid-cols-3 gap-2 mb-6">
              <div className="bg-gray-900 rounded-lg p-2.5 text-center">
                <div className="text-white font-bold text-sm leading-none">
                  {stats.country_count}
                </div>
                <div className="text-gray-500 text-[10px] mt-1.5 leading-none">Countries</div>
              </div>
              <div className="bg-gray-900 rounded-lg p-2.5 text-center">
                <div className="text-white font-bold text-sm leading-none">
                  {stats.artist_count.toLocaleString()}
                </div>
                <div className="text-gray-500 text-[10px] mt-1.5 leading-none">Artists</div>
              </div>
              <div className="bg-gray-900 rounded-lg p-2.5 text-center">
                <div className="text-white font-bold text-sm leading-none">
                  {stats.track_count.toLocaleString()}
                </div>
                <div className="text-gray-500 text-[10px] mt-1.5 leading-none">Tracks</div>
              </div>
            </div>

            {/* Top Genre */}
            {stats.top_genres.length > 0 && (
              <div className="mb-5">
                <div className="text-gray-500 text-xs uppercase tracking-wider mb-2">Top Genre</div>
                <div className="text-white text-sm capitalize">
                  {stats.top_genres[0].genre}
                </div>
              </div>
            )}

            {/* Diversity Score */}
            <div className="mb-6">
              <div className="text-gray-500 text-xs uppercase tracking-wider mb-2">Geographic Diversity</div>
              <div className="flex items-baseline gap-2">
                <span className={`text-2xl font-bold ${diversityColor}`}>
                  {diversityDisplay}
                </span>
                <span className="text-gray-600 text-sm">/ 10</span>
              </div>
              <div className="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    parseFloat(diversityDisplay ?? '0') >= 7
                      ? 'bg-green-400'
                      : parseFloat(diversityDisplay ?? '0') >= 4
                        ? 'bg-yellow-400'
                        : 'bg-red-400'
                  }`}
                  style={{ width: diversityBarWidth }}
                />
              </div>
              <p className="text-gray-600 text-[10px] mt-2 leading-relaxed">
                {parseFloat(diversityDisplay ?? '0') >= 7
                  ? 'Your library spans a wide range of countries — highly diverse!'
                  : parseFloat(diversityDisplay ?? '0') >= 4
                    ? `Your music comes from ${stats.country_count} countries. Explore beyond your top regions to increase this.`
                    : 'Most of your music is concentrated in a few countries.'}
              </p>
            </div>

            {/* Top 5 Countries */}
            <div>
              <div className="text-gray-500 text-xs uppercase tracking-wider mb-3">Top Countries</div>
              <ol className="space-y-1">
                {stats.top_countries.slice(0, 5).map((country, index) => (
                  <li key={country.id}>
                    <button
                      onClick={() => onCountrySelect(country.id)}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors text-left group"
                    >
                      <span className="text-gray-600 text-xs w-4 flex-shrink-0 text-right">
                        {index + 1}
                      </span>
                      <span className="text-gray-300 text-sm flex-1 truncate group-hover:text-white transition-colors">
                        {country.name}
                      </span>
                      <span className="text-gray-500 text-xs flex-shrink-0">
                        {country.artist_count}
                      </span>
                    </button>
                  </li>
                ))}
              </ol>
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
