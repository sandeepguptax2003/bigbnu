import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useDeferredValue, useEffect, useState } from 'react'
import { HorizonChart, HourChart } from './components/AccuracyCharts'
import { Controls } from './components/Controls'
import { GenerationChart } from './components/GenerationChart'
import { MetricCards } from './components/MetricCards'
import { Panel, StatusBox } from './components/Panel'
import { api } from './lib/api'
import { dateTime } from './lib/format'

interface Selection {
  start: string
  end: string
  horizon: number
}

const DEFAULTS: Selection = { start: '2026-01-10T00:00:00Z', end: '2026-01-17T00:00:00Z', horizon: 24 }

const MAX_HORIZON = 48

function isoOrNull(value: string | null) {
  const time = value ? Date.parse(value) : NaN
  return Number.isNaN(time) ? null : new Date(time).toISOString().replace('.000Z', 'Z')
}

function readUrl(): Selection {
  const params = new URLSearchParams(window.location.search)
  const start = isoOrNull(params.get('start'))
  const end = isoOrNull(params.get('end'))
  const horizon = Number(params.get('horizon') || NaN)
  const validRange = start !== null && end !== null && start < end
  return {
    start: validRange ? start : DEFAULTS.start,
    end: validRange ? end : DEFAULTS.end,
    horizon: Number.isInteger(horizon) && horizon >= 0 && horizon <= MAX_HORIZON ? horizon : DEFAULTS.horizon,
  }
}

export default function App() {
  const [selection, setSelection] = useState<Selection>(readUrl)
  const { start, end, horizon } = useDeferredValue(selection)

  useEffect(() => {
    const params = new URLSearchParams({ start: selection.start, end: selection.end, horizon: String(selection.horizon) })
    window.history.replaceState(null, '', `?${params}`)
  }, [selection])

  const meta = useQuery({ queryKey: ['meta'], queryFn: ({ signal }) => api.meta(signal) })
  const series = useQuery({
    queryKey: ['series', start, end, horizon],
    queryFn: ({ signal }) => api.series(start, end, horizon, signal),
    placeholderData: keepPreviousData,
  })
  const accuracy = useQuery({
    queryKey: ['accuracy', horizon],
    queryFn: ({ signal }) => api.accuracy(horizon, signal),
    placeholderData: keepPreviousData,
  })

  const spanHours = (Date.parse(end) - Date.parse(start)) / 3_600_000
  const update = (next: Partial<Selection>) => setSelection((s) => ({ ...s, ...next }))

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-10">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-forecast">GB national wind · Elexon BMRS</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Wind Forecast Monitor</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            What the latest wind forecast said at decision time, how it compared with what was actually generated, and
            how much error to plan for when buying from the day-ahead market.
          </p>
        </div>
        {meta.data && (
          <div className="font-mono text-xs text-muted">
            Data window {dateTime(meta.data.window_start)} – {dateTime(meta.data.window_end)} · refreshed {dateTime(meta.data.loaded_at)}
          </div>
        )}
      </header>

      <main className="grid gap-6">
        <Controls
          {...selection}
          min={meta.data?.window_start ?? '2026-01-01T00:00:00Z'}
          max={meta.data?.window_end ?? '2026-02-01T00:00:00Z'}
          maxHorizon={meta.data?.max_horizon_hours ?? MAX_HORIZON}
          onChange={update}
        />

        <Panel
          title="Actual vs forecast generation"
          subtitle={`Each forecast point is the latest one published at least ${horizon}h before its delivery time.`}
          aside={series.isFetching && <span className="text-xs text-muted">Updating…</span>}
        >
          {series.isError ? (
            <StatusBox tone="error">{series.error.message}</StatusBox>
          ) : !series.data ? (
            <StatusBox>Loading generation data…</StatusBox>
          ) : series.data.points.length === 0 ? (
            <StatusBox>No data in the selected range.</StatusBox>
          ) : (
            <GenerationChart points={series.data.points} spanHours={spanHours} />
          )}
        </Panel>

        <MetricCards metrics={series.data?.metrics} horizon={series.data?.horizon_hours ?? horizon} />

        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Error grows with lead time" subtitle="Whole data window. Horizons where under 90% of hours have a forecast are hidden. Click to pick a horizon.">
            {accuracy.data ? <HorizonChart data={accuracy.data} horizon={horizon} onSelect={(h) => update({ horizon: h })} /> : <StatusBox>{accuracy.isError ? accuracy.error.message : 'Loading…'}</StatusBox>}
          </Panel>
          <Panel title="Error by hour of day" subtitle={`Mean absolute error at ${accuracy.data?.horizon_hours ?? horizon}h ahead, whole data window (UTC).`}>
            {accuracy.data ? <HourChart data={accuracy.data} /> : <StatusBox>{accuracy.isError ? accuracy.error.message : 'Loading…'}</StatusBox>}
          </Panel>
        </div>
      </main>

      <footer className="mt-10 text-xs text-muted">
        Actuals: FUELHH (fuelType WIND). Forecasts: WINDFOR. Forecasts more than 48h before delivery are excluded.
      </footer>
    </div>
  )
}
