'use client';

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  type PieLabelRenderProps,
} from 'recharts';
import { getGenreColor } from '@/lib/colors';

interface GenrePieChartProps {
  data: Record<string, number>;
}

interface ChartEntry {
  name: string;
  value: number;
}

interface TooltipPayloadItem {
  name: string;
  value: number;
  payload: ChartEntry;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0];
  return (
    <div className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm shadow-lg">
      <p className="text-gray-100 font-medium">{item.name}</p>
      <p className="text-gray-400">{item.value} artists</p>
    </div>
  );
}

export default function GenrePieChart({ data }: GenrePieChartProps) {
  const chartData: ChartEntry[] = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, value]) => ({ name, value }));

  if (chartData.length === 0) {
    return <p className="text-gray-500 text-sm">No genre data available</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={80}
          label={({ name, percent }: PieLabelRenderProps) =>
            `${name ?? ''} ${(((percent as number) ?? 0) * 100).toFixed(0)}%`
          }
          labelLine={false}
        >
          {chartData.map((entry, i) => (
            <Cell key={i} fill={getGenreColor(entry.name)} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  );
}
