import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SeriesPoint } from '../lib/api'
import { axisTime, dateTime, gw, mw } from '../lib/format'

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { payload: SeriesPoint }[] }) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null
  return (
    <div className="rounded-lg border border-line bg-ink/95 px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 font-medium">{dateTime(point.time)} UTC</div>
      <div className="text-actual">Actual {mw(point.actual)}</div>
      <div className="text-forecast">Forecast {mw(point.forecast)}</div>
      {point.forecast_published && <div className="mt-1 text-muted">Published {dateTime(point.forecast_published)}</div>}
    </div>
  )
}

export function GenerationChart({ points, spanHours }: { points: SeriesPoint[]; spanHours: number }) {
  return (
    <div className="h-72 sm:h-96">
      <ResponsiveContainer>
        <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--color-line)" vertical={false} />
          <XAxis
            dataKey="time"
            tickFormatter={(t) => axisTime(t, spanHours)}
            stroke="var(--color-muted)"
            fontSize={12}
            minTickGap={40}
          />
          <YAxis tickFormatter={gw} stroke="var(--color-muted)" fontSize={12} width={64} />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line name="Actual" dataKey="actual" stroke="var(--color-actual)" dot={false} strokeWidth={2} connectNulls isAnimationActive={false} />
          <Line name="Forecast" dataKey="forecast" stroke="var(--color-forecast)" dot={false} strokeWidth={2} connectNulls isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
