# Wind Forecast Monitor

A web app for a UK utility's day-ahead power desk. For any period in January 2026 it shows the national wind forecast that was available at decision time, compares it with actual generation, and turns the measured error into a procurement buffer.

**Live app:** _&lt;deployment URL&gt;_

![stack](https://img.shields.io/badge/React-19-61dafb) ![stack](https://img.shields.io/badge/FastAPI-0.115-009688) ![stack](https://img.shields.io/badge/Python-3.12-3776ab) ![stack](https://img.shields.io/badge/Docker-ready-2496ed)

## What it does

| Need (from the brief) | How the app answers it |
|---|---|
| See the latest forecast available when the buying decision is made | Pick a date range and a **forecast horizon** (0–48h). Each target hour shows the latest `WINDFOR` forecast published at least *horizon* hours before delivery, plotted against actual `FUELHH` wind generation. |
| Quantify forecast accuracy | Live MAE, RMSE, bias, nMAE, P90 absolute error and worst hour for the selection, plus month-wide error-vs-horizon and error-by-hour-of-day charts. |
| Act on the error | A **procurement buffer** (P10 of actual − forecast): the MW shortfall that covers 90% of hours at the chosen horizon. |

Key finding (see [`analysis/forecast_error_analysis.ipynb`](analysis/forecast_error_analysis.ipynb)): in January 2026 the day-ahead wind forecast over-predicted by **~1.85 GW on average** and came in high in **87% of hours**. The bias grows with wind level, so it is not random noise.

## Repository layout

```
.
├── backend/                  FastAPI service (Python 3.12)
│   ├── app/
│   │   ├── main.py           HTTP layer: routes, validation, caching headers, error mapping, static hosting
│   │   ├── service.py        DataStore (TTL cache, single-flight refresh, stale-on-error) + Snapshot queries
│   │   ├── domain.py         Pure logic: ForecastIndex (horizon lookup by binary search) and error metrics
│   │   ├── elexon.py         Elexon BMRS client: chunked concurrent fetches, parsing, de-duplication
│   │   ├── schemas.py        Response models (OpenAPI docs at /docs)
│   │   └── config.py         All tunables from environment variables
│   ├── tests/                pytest: domain logic + API with a mocked Elexon
│   ├── pytest.ini            Test discovery config
│   ├── requirements.txt      Runtime dependencies (pinned)
│   └── requirements-dev.txt  + test dependencies
├── frontend/                 React 19 + TypeScript + Vite
│   └── src/
│       ├── App.tsx           Page composition, URL-synced state, data queries
│       ├── components/       Controls, GenerationChart, MetricCards, AccuracyCharts, Panel
│       └── lib/              Typed API client and formatters
├── analysis/
│   └── forecast_error_analysis.ipynb   Independent pandas analysis of forecast error + conclusions
├── api/index.py              Vercel serverless entry point (re-exports the FastAPI app)
├── Dockerfile                Multi-stage: builds the frontend, serves it and the API from one container
├── docker-compose.yml        One-command local run
├── vercel.json               Vercel build + routing config
└── .github/workflows/ci.yml  Tests, lint, build and Docker build on every push
```

## Running it

### Docker (recommended)

```bash
docker compose up --build
```

Open http://localhost:8000. Interactive API docs are at `/docs`, both locally and on the deployed app.

### Local development

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm ci
npm run dev                   # http://localhost:5173, proxies /api to :8000
```

Tests: `cd backend && pytest -q` · Lint and build: `cd frontend && npm run lint && npm run build`

### Analysis notebook

```bash
cd analysis
pip install -r requirements.txt
jupyter notebook forecast_error_analysis.ipynb
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness |
| `GET /api/meta` | Data window, max horizon, last refresh, row counts |
| `GET /api/series?start&end&horizon` | Actual + horizon-selected forecast per target time, with metrics for the range |
| `GET /api/accuracy?horizon` | Metrics for every horizon 0–48h, and by hour of day for the chosen horizon |

Times are ISO-8601 and treated as UTC. A reversed range, a range entirely outside the data window, or an out-of-bounds horizon returns `422`; a range that partly overlaps the window is clamped to it, and the response echoes the clamped `start`/`end`. If Elexon fails or returns malformed data before any data has loaded, the API returns `502`.

## Design decisions

- **Forecast selection.** For target *t* and horizon *h*, the app uses the latest forecast with `publishTime ≤ t − h`, so there is no look-ahead. Forecasts published after the target time, or more than 48h before it, are discarded. Vintages are sorted once per target, so each lookup is a binary search: O(log n).
- **Data flow.** Each server instance fetches the whole January window (~1.5k actuals, ~12k forecast rows) in concurrent 7-day chunks, indexes it in memory and caches it for 6h. Concurrent cold requests share one fetch. After the TTL, requests keep getting the cached snapshot while a single background refresh runs (stale-while-revalidate). A failed cold load is remembered for 15s, so a burst of requests doesn't hammer Elexon. Rate-limit and 5xx responses are retried with exponential backoff, and malformed payloads surface as `502`. Month-wide accuracy results are memoised per snapshot.
- **Caching layers.** Responses carry `Cache-Control` with `s-maxage`, so the Vercel edge serves repeated identical queries without calling Python. The browser side uses TanStack Query with abort-on-change and kept-previous data, so the charts don't flash while you drag the horizon slider.
- **Layering.** `domain.py` has no I/O and is fully unit tested. `elexon.py` is the only module that knows the upstream format. `main.py` is a thin HTTP layer. Changing the data window, horizon cap or cache TTL needs only environment variables.
- **Scaling path.** For longer histories or many instances, replace the per-instance in-memory snapshot with a scheduled ingest into Postgres/Parquet (or a shared Redis cache). `DataStore.snapshot()` is the single seam to swap. Range queries already bisect a pre-sorted time index rather than scanning.
- **Honest horizon comparison.** Above ~46h, few target hours have a forecast published that far ahead, so the error-vs-horizon chart hides horizons with under 90% coverage instead of comparing different samples. Every metric carries its `count`.
- **Front end.** State lives in the URL, so any view can be shared as a link. Vendor and chart libraries ship as separate, long-cacheable chunks (app code is ~12 kB). The layout works from 375px up.

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `WINDOW_START` / `WINDOW_END` | `2026-01-01T00:00:00Z` / `2026-02-01T00:00:00Z` | Target-time window served |
| `MAX_HORIZON_HOURS` | `48` | Longest forecast lead time considered |
| `CACHE_TTL_SECONDS` | `21600` | Snapshot lifetime |
| `STALE_RETRY_SECONDS` | `300` | Wait before retrying a failed background refresh (stale data keeps being served) |
| `FAILURE_BACKOFF_SECONDS` | `15` | How long a failed cold load is remembered before trying again |
| `FETCH_CHUNK_DAYS` | `7` | Size of each concurrent Elexon request |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed origins when the frontend is hosted separately |
| `STATIC_DIR` | _(unset)_ | Serve a built frontend from this folder (set in Docker) |

## Data sources

- Actuals: [Elexon BMRS FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), `fuelType = WIND`, 30-minute resolution
- Forecasts: [Elexon BMRS WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream), hourly targets, multiple publish times per target

## Use of AI tools

This project was built with help from **Claude Code (Anthropic)**, used for scaffolding, writing code and tests, and reviewing the analysis. The domain approach, design decisions and final verification are my own.
