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

const RADIAN = Math.PI / 180;
const MIN_LABEL_PERCENT = 0.05;

function renderLabel(props: PieLabelRenderProps): JSX.Element | null {
  const { cx, cy, midAngle, outerRadius, name, percent } = props;
  if ((percent as number) < MIN_LABEL_PERCENT) return null;
  const radius = (outerRadius as number) + 20;
  const x = (cx as number) + radius * Math.cos(-(midAngle as number) * RADIAN);
  const y = (cy as number) + radius * Math.sin(-(midAngle as number) * RADIAN);
  return (
    <text
      x={x}
      y={y}
      fill="#9ca3af"
      fontSize={11}
      dominantBaseline="central"
      textAnchor={x > (cx as number) ? 'start' : 'end'}
    >
      {name as string}
    </text>
  );
}

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
          label={renderLabel}
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
