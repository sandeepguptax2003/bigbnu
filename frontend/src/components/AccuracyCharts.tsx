import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AccuracyResponse } from '../lib/api'
import { gw, mw } from '../lib/format'

const tooltipStyle = { background: 'var(--color-ink)', border: '1px solid var(--color-line)', borderRadius: 8, fontSize: 12 }

export function HorizonChart({ data, horizon, onSelect }: { data: AccuracyResponse; horizon: number; onSelect: (h: number) => void }) {
  const fullCoverage = Math.max(0, ...data.by_horizon.map((r) => r.metrics?.count ?? 0))
  const rows = data.by_horizon
    .filter((r) => r.metrics && r.metrics.count >= 0.9 * fullCoverage)
    .map((r) => ({ h: r.horizon_hours, mae: r.metrics!.mae, p90: r.metrics!.p90_abs, bias: r.metrics!.bias }))
  return (
    <div className="h-64">
      <ResponsiveContainer>
        <LineChart
          data={rows}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
          onClick={(e) => e?.activeLabel != null && onSelect(Number(e.activeLabel))}
          className="cursor-pointer"
        >
          <CartesianGrid stroke="var(--color-line)" vertical={false} />
          <XAxis dataKey="h" type="number" domain={['dataMin', 'dataMax']} allowDecimals={false} stroke="var(--color-muted)" fontSize={12} tickFormatter={(h) => `${h}h`} />
          <YAxis tickFormatter={gw} stroke="var(--color-muted)" fontSize={12} width={64} />
          <Tooltip contentStyle={tooltipStyle} labelFormatter={(h) => `${h}h ahead`} formatter={(v: number) => mw(v)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine x={horizon} stroke="var(--color-warn)" strokeDasharray="4 4" />
          <Line name="MAE" dataKey="mae" stroke="var(--color-forecast)" dot={false} strokeWidth={2} isAnimationActive={false} />
          <Line name="P90 |error|" dataKey="p90" stroke="var(--color-actual)" dot={false} strokeWidth={2} isAnimationActive={false} />
          <Line name="Bias" dataKey="bias" stroke="var(--color-warn)" dot={false} strokeWidth={1.5} strokeDasharray="3 3" isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function HourChart({ data }: { data: AccuracyResponse }) {
  const rows = data.by_hour_of_day.map((r) => ({ hour: `${String(r.hour).padStart(2, '0')}:00`, mae: r.metrics?.mae ?? null }))
  return (
    <div className="h-64">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--color-line)" vertical={false} />
          <XAxis dataKey="hour" stroke="var(--color-muted)" fontSize={12} interval={2} />
          <YAxis tickFormatter={gw} stroke="var(--color-muted)" fontSize={12} width={64} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.04)' }} formatter={(v: number) => mw(v)} />
          <Bar name="MAE" dataKey="mae" fill="var(--color-forecast)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
