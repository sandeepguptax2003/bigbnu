import type { ReactNode } from 'react'

export function Panel({ title, subtitle, children, aside }: { title: string; subtitle?: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="rounded-2xl border border-line bg-panel p-4 sm:p-6">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold tracking-tight">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
        </div>
        {aside}
      </header>
      {children}
    </section>
  )
}

export function StatusBox({ children, tone = 'muted' }: { children: ReactNode; tone?: 'muted' | 'error' }) {
  return (
    <div className={`grid h-full min-h-48 place-items-center rounded-xl border border-dashed border-line text-sm ${tone === 'error' ? 'text-red-300' : 'text-muted'}`}>
      {children}
    </div>
  )
}
