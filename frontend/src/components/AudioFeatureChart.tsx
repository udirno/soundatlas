'use client';

import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
} from 'recharts';

interface AudioFeatureChartProps {
  countryAverages: Record<string, number | null>;
  globalAverages: Record<string, number | null>;
}

// Exclude tempo — BPM scale (60-200) distorts the 0-1 radar chart
const FEATURES = ['energy', 'danceability', 'valence', 'acousticness'];

function hasAnyData(features: Record<string, number | null>): boolean {
  return FEATURES.some((f) => features[f] !== null && features[f] !== undefined);
}

export default function AudioFeatureChart({
  countryAverages,
  globalAverages,
}: AudioFeatureChartProps) {
  if (!hasAnyData(countryAverages) && !hasAnyData(globalAverages)) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500 text-sm border border-gray-800 rounded-lg">
        Audio feature data is currently unavailable.
      </div>
    );
  }

  const chartData = FEATURES.map((f) => ({
    feature: f.charAt(0).toUpperCase() + f.slice(1),
    country: countryAverages[f] ?? 0,
    global: globalAverages[f] ?? 0,
  }));

  // If tempo data exists (non-null), show it as a text stat below the chart
  const tempo = countryAverages['tempo'];

  return (
    <div>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={chartData}>
          <PolarGrid stroke="#374151" />
          <PolarAngleAxis
            dataKey="feature"
            tick={{ fill: '#9ca3af', fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 1]}
            tick={{ fill: '#6b7280', fontSize: 10 }}
          />
          <Radar
            name="This Country"
            dataKey="country"
            stroke="#f43f5e"
            fill="#f43f5e"
            fillOpacity={0.3}
          />
          <Radar
            name="Global Avg"
            dataKey="global"
            stroke="#94a3b8"
            fill="#94a3b8"
            fillOpacity={0.2}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }}
          />
        </RadarChart>
      </ResponsiveContainer>
      {tempo !== null && tempo !== undefined && (
        <p className="text-gray-400 text-sm text-center mt-1">
          Avg Tempo: {tempo.toFixed(0)} BPM
        </p>
      )}
    </div>
  );
}
