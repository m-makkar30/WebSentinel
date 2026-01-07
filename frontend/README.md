# frontend

React + Vite + TypeScript dashboard for WebSentinel, styled with Tailwind CSS
and shadcn/ui.

Showpieces: the before/after diff viewer, the per-target change timeline, and
the dashboard (alerts feed + trend charts + LLM-cost panel).

## Stack

React 18 + Vite + TypeScript, Tailwind CSS v4, shadcn/ui primitives, React
Router, and TanStack Query. A typed API client (`src/lib/api.ts`) talks to the
DRF backend; in dev, Vite proxies `/api` to the backend.

## Develop

```bash
npm install
npm run dev      # http://localhost:5173 (proxies /api -> backend:8000)
npm run build    # type-check + production build
npm run lint     # eslint
```

Or via Docker: `docker compose up frontend` (joins the full stack).
