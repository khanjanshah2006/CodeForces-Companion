import { useState } from "react";
import { Search, RefreshCw, Crown, Loader2, User2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { CountUp } from "./CountUp";
import { useDashboard } from "@/lib/store";

const rankMeta = {
  "legendary grandmaster": { label: "Legendary GM", cls: "from-red-500 to-rose-400", badge: "border-red-400/40 bg-red-500/15 text-red-300" },
  "international grandmaster": { label: "Int. GM", cls: "from-red-400 to-orange-400", badge: "border-red-400/30 bg-red-500/10 text-red-300" },
  "grandmaster":  { label: "Grandmaster", cls: "from-orange-400 to-amber-400", badge: "border-orange-400/30 bg-orange-500/10 text-orange-300" },
  "international master": { label: "Int. Master", cls: "from-amber-400 to-yellow-300", badge: "border-amber-400/30 bg-amber-500/10 text-amber-300" },
  "master":       { label: "Master", cls: "from-amber-400 to-yellow-300", badge: "border-amber-400/30 bg-amber-500/10 text-amber-200" },
  "candidate master": { label: "Cand. Master", cls: "from-violet-400 to-purple-400", badge: "border-violet-400/30 bg-violet-500/10 text-violet-300" },
  "expert":       { label: "Expert", cls: "from-blue-400 to-cyan-400", badge: "border-blue-400/30 bg-blue-500/10 text-blue-300" },
  "specialist":   { label: "Specialist", cls: "from-cyan-400 to-teal-400", badge: "border-cyan-400/30 bg-cyan-500/10 text-cyan-300" },
  "pupil":        { label: "Pupil", cls: "from-green-400 to-emerald-400", badge: "border-green-400/30 bg-green-500/10 text-green-300" },
  "newbie":       { label: "Newbie", cls: "from-slate-400 to-slate-300", badge: "border-slate-400/30 bg-slate-500/10 text-slate-400" },
  "unrated":      { label: "Unrated", cls: "from-slate-500 to-slate-400", badge: "border-slate-400/20 bg-slate-500/5 text-slate-500" },
};
const getRank = (r) => rankMeta[r?.toLowerCase()] ?? rankMeta.unrated;

function ratingBar(cur, max) { return max > 0 ? Math.min(100, Math.round((cur / max) * 100)) : 0; }

export function IdentityCard() {
  const { loadState, error, analytics, doSync } = useDashboard();
  const [input, setInput] = useState("");
  const onSubmit = (e) => { e.preventDefault(); if (input.trim()) doSync(input.trim()); };
  const rank = analytics ? getRank(analytics.rank) : null;
  const barPct = analytics ? ratingBar(analytics.current_rating, analytics.max_rating) : 0;

  return (
    <GlassCard glow="blue" className="h-full">
      {/* Search form */}
      <form onSubmit={onSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
          <input
            id="cf-handle-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter Codeforces handle…"
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-9 pr-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-all focus:border-blue-400/50 focus:bg-white/8 focus:shadow-[0_0_0_2px_rgba(59,130,246,0.15)]"
          />
        </div>
        <button
          id="sync-button" type="submit"
          disabled={loadState === "loading"}
          className="flex items-center gap-1.5 rounded-xl border border-blue-400/30 bg-gradient-to-br from-blue-500/20 to-violet-500/20 px-4 py-2.5 text-xs font-bold text-blue-200 shadow-[0_0_12px_rgba(59,130,246,0.2)] transition-all hover:border-blue-400/50 hover:shadow-[0_0_20px_rgba(59,130,246,0.35)] active:scale-95 disabled:opacity-50"
        >
          {loadState === "loading" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Sync
        </button>
      </form>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.p initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="mt-3 rounded-xl border border-red-400/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      {/* Loading skeleton */}
      <AnimatePresence>
        {loadState === "loading" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="mt-6 space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-14 w-14 rounded-2xl bg-white/5 animate-pulse" />
              <div className="space-y-2 flex-1">
                <div className="h-4 w-32 rounded bg-white/5 animate-pulse" />
                <div className="h-3 w-20 rounded bg-white/5 animate-pulse" />
              </div>
            </div>
            <div className="h-10 w-40 rounded bg-white/5 animate-pulse" />
            <div className="h-1.5 w-full rounded-full bg-white/5 animate-pulse" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loaded */}
      <AnimatePresence>
        {loadState === "success" && analytics && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            {/* Avatar + name */}
            <div className="mt-5 flex items-start gap-4">
              {/* Avatar with gradient ring */}
              <div className="relative flex-shrink-0">
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${rank.cls} p-[2px]`} style={{ borderRadius: "16px" }}>
                  <div className="h-full w-full rounded-2xl bg-slate-900" />
                </div>
                <div className={`relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${rank.cls} bg-opacity-20`}>
                  <Crown className="h-6 w-6 text-white drop-shadow-lg" />
                </div>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-xl font-black tracking-tight text-white truncate">{analytics.handle}</h2>
                  <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em] ${rank.badge}`}>
                    {rank.label}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-500">Codeforces · Synced just now</p>
              </div>
            </div>

            {/* Rating */}
            <div className="mt-5 flex items-end gap-3">
              <span className={`bg-gradient-to-r ${rank.cls} bg-clip-text text-6xl font-black tracking-tight text-transparent`}>
                <CountUp end={analytics.current_rating} duration={1200} />
              </span>
              <div className="pb-1.5 flex flex-col items-start">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Peak</span>
                <span className="text-base font-bold text-slate-400">{analytics.max_rating}</span>
              </div>
            </div>

            {/* Progress bar to peak */}
            <div className="mt-4 space-y-1">
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>Progress to peak</span>
                <span>{barPct}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                <motion.div
                  className={`h-full rounded-full bg-gradient-to-r ${rank.cls}`}
                  style={{ boxShadow: `0 0 12px rgba(59,130,246,0.5)` }}
                  initial={{ width: 0 }}
                  animate={{ width: `${barPct}%` }}
                  transition={{ duration: 1.2, ease: [0.34, 1.56, 0.64, 1], delay: 0.2 }}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Idle */}
      {loadState === "idle" && (
        <div className="mt-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
            <User2 className="h-5 w-5 text-slate-500" />
          </div>
          <p className="text-xs text-slate-500">Enter your handle above to load your analytics dashboard</p>
        </div>
      )}
    </GlassCard>
  );
}
