
## Codeforces Companion — Bento Dashboard

Build a single-page dashboard at `/` (replacing the placeholder in `src/routes/index.tsx`) matching the spec.

### Setup
- Install `framer-motion` and `recharts` via `bun add`.
- Update `src/styles.css` to default to dark mode (add `dark` class to `<html>` in `__root.tsx`) and add a radial gradient background on body. Keep semantic tokens; introduce accent CSS vars for electric blue (`--accent-blue`) and neon green (`--accent-green`) plus neon orange and warning red.
- Update root route `head()` with title "Codeforces Companion" and matching meta/description/og tags.

### Components (under `src/components/dashboard/`)
- `GlassCard.tsx` — shared wrapper: `bg-slate-900/50 backdrop-blur-md border border-white/10 rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-blue-500/10 hover:border-white/20`.
- `CountUp.tsx` — hook/component animating 0 → target on mount using `requestAnimationFrame`.
- `IdentityCard.tsx` — handle "tourist", rating "3522 (Max: 3979)", "Legendary Grandmaster" badge, `RefreshCw` icon button top-right.
- `StatCard.tsx` — label + big number (CountUp). Used for Total Submissions (842), Unique Solved (412), Acceptance Rate (68.3%), Top Error (TLE — red glow text).
- `POTDCard.tsx` — title, yellow "PENDING" pill, problem title, difficulty 2400 + tag `dp`, glowing blue "Verify Solution" button (`active:scale-95`, blue shadow glow).
- `CoachCard.tsx` — title with `Bot` icon, empty state with `Scan` icon centered, copy, "Run Diagnostic Scan" button.
- `RatingChart.tsx` — Recharts `BarChart` (800/1000/1200/1400, mock counts), dark theme, electric blue bars, subtle grid.
- `TagPerformance.tsx` — 6 horizontal progress bars: 3 weak (orange) — `dp`, `trees`, `graphs`; 3 strong (green) — `math`, `greedy`, `implementation`.
- `UnexploredTopics.tsx` — flex-wrap pill chips (`fft`, `geometry`, `2-sat`, `flows`, `suffix-array`, `treap`, `sqrt-decomposition`, `chinese-remainder`) with hover highlight.

### Layout in `src/routes/index.tsx`
- Full-screen container, no nav/sidebar/footer.
- `motion.div` parent with `staggerChildren`; each grid child is a `motion.div` with `initial={{opacity:0, y:20}} animate={{opacity:1, y:0}}`.
- CSS Grid:
  - Row 1: `grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4` — Identity spans `lg:col-span-2`, then 4 stat cards (acceptance/top-error fit on lg). Adjust to: Identity `col-span-2`, then 3 stats on row, push 4th stat to wrap — or make identity `col-span-2` plus four stats each `col-span-1` (total 6) → switch to `lg:grid-cols-6` with identity `col-span-2`.
  - Row 2: `grid-cols-1 lg:grid-cols-2 gap-4` — POTD + Coach.
  - Row 3: `grid-cols-1 lg:grid-cols-3 gap-4` — Rating chart + Tag performance + Unexplored.
- Page padding `p-6 lg:p-8`, max-width container, min-h-screen.

### Technical notes
- Recharts: `<ResponsiveContainer>`, `<CartesianGrid stroke="rgba(255,255,255,0.05)">`, axis ticks in muted white, `<Tooltip>` with dark glass styling, bar `fill="#3b82f6"` with `radius={[6,6,0,0]}`.
- Framer Motion variants: `container` with `staggerChildren: 0.08`, `item` with y:20 → 0 over 0.5s ease-out.
- CountUp respects `prefers-reduced-motion` by jumping straight to value.
- All colors via Tailwind utilities + a few custom accent classes; keep design-token usage consistent for borders.

### Out of scope
No routing changes beyond `/`, no backend, no auth, no persistence — pure presentational with mock data.
