import { Activity } from "lucide-react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { useDashboard } from "@/lib/store";

const barVariants = {
  hidden: { width: 0 },
  show: (pct) => ({
    width: `${pct}%`,
    transition: { duration: 0.9, ease: [0.34, 1.56, 0.64, 1] },
  }),
};

const rowVariants = {
  hidden: { opacity: 0, x: -12 },
  show: { opacity: 1, x: 0 },
};

function TagBar({ tag, failureIndex, uniqueSolved, uniqueAttempted, accent, index }) {
  const successPct = Math.round((1 - failureIndex) * 100);
  const isWeak = accent === "orange";

  return (
    <motion.div
      variants={rowVariants}
      transition={{ duration: 0.4, ease: "easeOut", delay: index * 0.07 }}
    >
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-200">{tag}</span>
          <span className={`rounded-full px-1.5 py-0.5 font-mono text-[9px] font-semibold ${isWeak ? "bg-orange-500/10 text-orange-400" : "bg-emerald-500/10 text-emerald-400"}`}>
            {uniqueSolved}/{uniqueAttempted}
          </span>
        </div>
        <span className={`font-mono text-[11px] font-bold ${isWeak ? "text-orange-300" : "text-emerald-300"}`}>
          {successPct}%
        </span>
      </div>

      {/* Track */}
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-white/5">
        {/* Filled bar */}
        <motion.div
          className={`absolute inset-y-0 left-0 rounded-full ${isWeak
            ? "bg-gradient-to-r from-orange-600 via-amber-500 to-yellow-400"
            : "bg-gradient-to-r from-emerald-600 via-teal-400 to-green-300"
          }`}
          style={{ boxShadow: isWeak ? "0 0 10px rgba(251,146,60,0.5)" : "0 0 10px rgba(52,211,153,0.5)" }}
          custom={successPct}
          variants={barVariants}
          initial="hidden"
          animate="show"
        />
        {/* Shimmer overlay */}
        <div className="absolute inset-0 rounded-full animate-shimmer opacity-40" />
      </div>
    </motion.div>
  );
}

export function TagPerformance() {
  const { analytics, loadState } = useDashboard();

  return (
    <GlassCard glow="green" className="h-full">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10">
          <Activity className="h-3.5 w-3.5 text-emerald-300" />
        </div>
        <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">Tag Performance</h3>
      </div>

      {/* Loading */}
      {loadState === "loading" && (
        <div className="mt-5 space-y-5 animate-pulse">
          {[1, 2, 3].map((n) => (
            <div key={n} className="space-y-1.5">
              <div className="h-3 w-1/2 rounded bg-white/5" />
              <div className="h-2 w-full rounded-full bg-white/5" />
            </div>
          ))}
        </div>
      )}

      {loadState === "success" && analytics && (
        <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.05 } } }}>
          {/* Weak tags */}
          <div className="mt-5">
            <div className="mb-3 flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-orange-400 shadow-[0_0_6px_rgba(251,146,60,0.8)]" />
              <p className="text-[9px] font-black uppercase tracking-[0.15em] text-orange-400/90">Weak Tags</p>
            </div>
            <div className="space-y-4">
              {analytics.weak_tags.slice(0, 5).map((t, i) => (
                <TagBar key={t.tag} tag={t.tag} failureIndex={t.failure_index}
                  uniqueSolved={t.unique_solved} uniqueAttempted={t.unique_attempted}
                  accent="orange" index={i} />
              ))}
            </div>
          </div>

          {/* Divider */}
          <div className="my-5 h-px bg-gradient-to-r from-transparent via-white/8 to-transparent" />

          {/* Strong tags */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
              <p className="text-[9px] font-black uppercase tracking-[0.15em] text-emerald-400/90">Strong Tags</p>
            </div>
            <div className="space-y-4">
              {analytics.strong_tags.slice(0, 5).map((t, i) => (
                <TagBar key={t.tag} tag={t.tag} failureIndex={t.failure_index}
                  uniqueSolved={t.unique_solved} uniqueAttempted={t.unique_attempted}
                  accent="green" index={i} />
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {(loadState === "idle" || loadState === "error") && (
        <p className="mt-5 text-xs text-slate-500">Sync a handle to see tag performance.</p>
      )}
    </GlassCard>
  );
}
