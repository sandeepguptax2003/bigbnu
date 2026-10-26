const UTC = 'UTC'

export const mw = (value: number | null | undefined) =>
  value == null ? '—' : `${Math.round(value).toLocaleString('en-GB')} MW`

export const gw = (value: number) => `${(value / 1000).toFixed(1)} GW`

export const pct = (value: number | null | undefined) => (value == null ? '—' : `${value.toFixed(1)}%`)

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString('en-GB', { timeZone: UTC, day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

export const axisTime = (iso: string, spanHours: number) =>
  new Date(iso).toLocaleString('en-GB', {
    timeZone: UTC,
    ...(spanHours > 48 ? { day: '2-digit', month: 'short' } : { hour: '2-digit', minute: '2-digit' }),
  })

export const toInputValue = (iso: string) => iso.slice(0, 16)

export const fromInputValue = (value: string) => `${value}:00Z`
