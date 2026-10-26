export interface Metrics {
  count: number
  mae: number
  rmse: number
  bias: number
  nmae_pct: number | null
  p50_abs: number
  p90_abs: number
  p99_abs: number
  max_abs: number
  p10_error: number
}

export interface Meta {
  window_start: string
  window_end: string
  max_horizon_hours: number
  loaded_at: string
  actual_points: number
  forecast_targets: number
}

export interface SeriesPoint {
  time: string
  actual: number | null
  forecast: number | null
  forecast_published: string | null
}

export interface SeriesResponse {
  start: string
  end: string
  horizon_hours: number
  points: SeriesPoint[]
  metrics: Metrics | null
}

export interface AccuracyResponse {
  horizon_hours: number
  by_horizon: { horizon_hours: number; metrics: Metrics | null }[]
  by_hour_of_day: { hour: number; metrics: Metrics | null }[]
}

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function get<T>(path: string, params: Record<string, string | number> = {}, signal?: AbortSignal): Promise<T> {
  const query = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]))
  const response = await fetch(`${BASE}${path}${query.size ? `?${query}` : ''}`, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : body?.detail?.[0]?.msg
    throw new Error(detail ?? `Request failed (${response.status})`)
  }
  return response.json()
}

export const api = {
  meta: (signal?: AbortSignal) => get<Meta>('/api/meta', {}, signal),
  series: (start: string, end: string, horizon: number, signal?: AbortSignal) =>
    get<SeriesResponse>('/api/series', { start, end, horizon }, signal),
  accuracy: (horizon: number, signal?: AbortSignal) => get<AccuracyResponse>('/api/accuracy', { horizon }, signal),
}
