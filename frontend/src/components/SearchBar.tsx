'use client';

import { useEffect, useRef, useState } from 'react';
import { fetchSearch } from '@/lib/api';
import type { SearchArtistHit, SearchTrackHit } from '@/lib/api';

interface SearchBarProps {
  onSelect: (countryId: number) => void;
}

export default function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [artists, setArtists] = useState<SearchArtistHit[]>([]);
  const [tracks, setTracks] = useState<SearchTrackHit[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [unmappedId, setUnmappedId] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setArtists([]);
      setTracks([]);
      setHasSearched(false);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    const timer = setTimeout(async () => {
      try {
        const result = await fetchSearch(query.trim());
        setArtists(result.artists);
        setTracks(result.tracks);
        setHasSearched(true);
      } catch {
        setArtists([]);
        setTracks([]);
        setHasSearched(true);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Close on outside click
  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setQuery('');
        setArtists([]);
        setTracks([]);
        setHasSearched(false);
        setUnmappedId(null);
      }
    }
    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, []);

  function handleArtistClick(hit: SearchArtistHit) {
    if (hit.country_id === null) {
      setUnmappedId(hit.id);
      return;
    }
    onSelect(hit.country_id);
    setQuery('');
    setArtists([]);
    setTracks([]);
    setHasSearched(false);
    setUnmappedId(null);
  }

  function handleTrackClick(hit: SearchTrackHit) {
    if (!hit.in_library) return;
    if (hit.country_id === null) {
      setUnmappedId(hit.id);
      return;
    }
    onSelect(hit.country_id);
    setQuery('');
    setArtists([]);
    setTracks([]);
    setHasSearched(false);
    setUnmappedId(null);
  }

  const showDropdown = query.trim().length > 0;
  const hasResults = artists.length > 0 || tracks.length > 0;

  return (
    <div
      ref={containerRef}
      className="absolute top-4 left-1/2 -translate-x-1/2 z-50 w-96"
    >
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search artists or tracks..."
        className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gray-500 focus:ring-1 focus:ring-gray-600 text-sm"
      />

      {showDropdown && (
        <div className="absolute top-full mt-1 left-0 w-full bg-gray-900 border border-gray-700 rounded-lg shadow-lg max-h-80 overflow-y-auto z-50">
          {isLoading && (
            <div className="px-4 py-3 text-gray-400 text-sm">Searching...</div>
          )}

          {!isLoading && hasSearched && !hasResults && (
            <div className="px-4 py-3 text-gray-400 text-sm">No results found</div>
          )}

          {!isLoading && artists.length > 0 && (
            <div>
              <div className="px-4 py-2 text-gray-400 text-xs font-semibold uppercase tracking-wider border-b border-gray-800">
                Artists
              </div>
              {artists.map((hit) => (
                <button
                  key={hit.id}
                  type="button"
                  onClick={() => handleArtistClick(hit)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-800 transition-colors text-left"
                >
                  {hit.image_url && (
                    <img
                      src={hit.image_url}
                      alt={hit.name}
                      className="w-8 h-8 rounded-full object-cover flex-shrink-0"
                    />
                  )}
                  {!hit.image_url && (
                    <div className="w-8 h-8 rounded-full bg-gray-700 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-white text-sm truncate">{hit.name}</div>
                    {hit.genres && hit.genres.length > 0 && (
                      <div className="text-gray-500 text-xs truncate">{hit.genres[0]}</div>
                    )}
                  </div>
                  {unmappedId === hit.id && (
                    <span className="text-yellow-500 text-xs flex-shrink-0">Country not mapped</span>
                  )}
                </button>
              ))}
            </div>
          )}

          {!isLoading && tracks.length > 0 && (
            <div>
              <div className="px-4 py-2 text-gray-400 text-xs font-semibold uppercase tracking-wider border-b border-gray-800">
                Tracks
              </div>
              {tracks.map((hit) => (
                <button
                  key={hit.id}
                  type="button"
                  onClick={() => handleTrackClick(hit)}
                  disabled={!hit.in_library}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                    hit.in_library
                      ? 'hover:bg-gray-800 cursor-pointer'
                      : 'opacity-50 cursor-default'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-white text-sm truncate">{hit.name}</div>
                    {hit.album_name && (
                      <div className="text-gray-500 text-xs truncate">{hit.album_name}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {!hit.in_library && (
                      <span className="text-gray-500 text-xs">Not in your library</span>
                    )}
                    {unmappedId === hit.id && (
                      <span className="text-yellow-500 text-xs">Country not mapped</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
