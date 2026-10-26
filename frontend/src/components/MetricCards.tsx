import type { Metrics } from '../lib/api'
import { mw, pct } from '../lib/format'

export function MetricCards({ metrics, horizon }: { metrics: Metrics | null | undefined; horizon: number }) {
  const cards = [
    { label: 'Mean absolute error', value: mw(metrics?.mae), hint: `${pct(metrics?.nmae_pct)} of mean output` },
    { label: 'Bias (actual − forecast)', value: mw(metrics?.bias), hint: !metrics ? '—' : metrics.bias < 0 ? 'Forecast runs high' : metrics.bias > 0 ? 'Forecast runs low' : 'No bias' },
    { label: 'P90 absolute error', value: mw(metrics?.p90_abs), hint: '9 in 10 hours stay within this' },
    { label: 'Worst hour', value: mw(metrics?.max_abs), hint: `RMSE ${mw(metrics?.rmse)}` },
  ]
  const buffer = metrics ? Math.max(0, -metrics.p10_error) : null
  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-2xl border border-line bg-panel p-4">
            <div className="text-xs text-muted">{c.label}</div>
            <div className="mt-2 font-mono text-xl font-medium sm:text-2xl">{c.value}</div>
            <div className="mt-1 text-xs text-muted">{c.hint}</div>
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-warn/30 bg-warn/5 p-4 text-sm leading-relaxed">
        <span className="font-semibold text-warn">Procurement buffer · </span>
        {buffer == null ? (
          'Not enough data in this range.'
        ) : (
          <>
            With forecasts taken <b>{horizon}h</b> ahead, actual wind fell short of the forecast by more than{' '}
            <b className="font-mono">{mw(buffer)}</b> only 10% of the time. Hedging that amount covers 90% of hours
            ({metrics?.count} hours compared).
          </>
        )}
      </div>
    </div>
  )
}
