import { fromInputValue, toInputValue } from '../lib/format'

interface Props {
  start: string
  end: string
  horizon: number
  min: string
  max: string
  maxHorizon: number
  onChange: (next: { start?: string; end?: string; horizon?: number }) => void
}

const PRESETS = [
  { label: 'Day-ahead (24h)', hours: 24 },
  { label: 'Intraday (4h)', hours: 4 },
  { label: 'Two-day (36h)', hours: 36 },
]

export function Controls({ start, end, horizon, min, max, maxHorizon, onChange }: Props) {
  const field = 'mt-1 w-full rounded-lg border border-line bg-ink px-3 py-2 font-mono text-sm outline-none focus:border-forecast'
  return (
    <div className="grid gap-4 rounded-2xl border border-line bg-panel p-4 sm:p-6 lg:grid-cols-[1fr_1fr_2fr]">
      <label className="text-xs font-medium uppercase tracking-wider text-muted">
        Start (UTC)
        <input
          type="datetime-local"
          className={field}
          value={toInputValue(start)}
          min={toInputValue(min)}
          max={toInputValue(end)}
          onChange={(e) => e.target.value && onChange({ start: fromInputValue(e.target.value) })}
        />
      </label>
      <label className="text-xs font-medium uppercase tracking-wider text-muted">
        End (UTC)
        <input
          type="datetime-local"
          className={field}
          value={toInputValue(end)}
          min={toInputValue(start)}
          max={toInputValue(max)}
          onChange={(e) => e.target.value && onChange({ end: fromInputValue(e.target.value) })}
        />
      </label>
      <div>
        <div className="flex items-center justify-between text-xs font-medium uppercase tracking-wider text-muted">
          <label htmlFor="horizon">Forecast horizon</label>
          <span className="font-mono text-sm normal-case tracking-normal text-forecast">{horizon}h before delivery</span>
        </div>
        <input
          id="horizon"
          type="range"
          min={0}
          max={maxHorizon}
          step={1}
          value={horizon}
          onChange={(e) => onChange({ horizon: Number(e.target.value) })}
          className="mt-3 w-full"
        />
        <div className="mt-2 flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.hours}
              type="button"
              onClick={() => onChange({ horizon: p.hours })}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${horizon === p.hours ? 'border-forecast bg-forecast/10 text-forecast' : 'border-line text-muted hover:text-slate-100'}`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
