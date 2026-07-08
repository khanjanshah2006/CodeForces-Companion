import { Compass, Lightbulb } from "lucide-react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { useDashboard } from "@/lib/store";

const chipColors = [
  "border-blue-400/25 bg-blue-500/10 text-blue-300 hover:border-blue-400/50 hover:bg-blue-500/20 hover:shadow-[0_0_14px_rgba(59,130,246,0.35)]",
  "border-violet-400/25 bg-violet-500/10 text-violet-300 hover:border-violet-400/50 hover:bg-violet-500/20 hover:shadow-[0_0_14px_rgba(139,92,246,0.35)]",
  "border-cyan-400/25 bg-cyan-500/10 text-cyan-300 hover:border-cyan-400/50 hover:bg-cyan-500/20 hover:shadow-[0_0_14px_rgba(34,211,238,0.35)]",
  "border-emerald-400/25 bg-emerald-500/10 text-emerald-300 hover:border-emerald-400/50 hover:bg-emerald-500/20 hover:shadow-[0_0_14px_rgba(52,211,153,0.35)]",
  "border-pink-400/25 bg-pink-500/10 text-pink-300 hover:border-pink-400/50 hover:bg-pink-500/20 hover:shadow-[0_0_14px_rgba(236,72,153,0.35)]",
  "border-amber-400/25 bg-amber-500/10 text-amber-300 hover:border-amber-400/50 hover:bg-amber-500/20 hover:shadow-[0_0_14px_rgba(251,191,36,0.35)]",
];

const chipVariants = {
  hidden: { opacity: 0, scale: 0.75, y: 8 },
  show: (i) => ({
    opacity: 1, scale: 1, y: 0,
    transition: { duration: 0.35, ease: [0.34, 1.56, 0.64, 1], delay: i * 0.04 },
  }),
};

export function UnexploredTopics() {
  const { analytics, loadState } = useDashboard();
  const topics = analytics?.untried_tags ?? [];

  return (
    <GlassCard glow="violet">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-500/10">
            <Compass className="h-3.5 w-3.5 text-violet-300" />
          </div>
          <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">Unexplored Topics</h3>
        </div>
        {topics.length > 0 && (
          <motion.span
            initial={{ scale: 0 }} animate={{ scale: 1 }}
            className="rounded-full border border-violet-400/25 bg-violet-500/15 px-2 py-0.5 text-[9px] font-black text-violet-300 shadow-[0_0_10px_rgba(139,92,246,0.25)]"
          >
            {topics.length}
          </motion.span>
        )}
      </div>

      {loadState === "loading" && (
        <div className="mt-5 flex flex-wrap gap-2 animate-pulse">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div key={n} className="h-7 rounded-lg bg-white/5" style={{ width: `${60 + n * 10}px` }} />
          ))}
        </div>
      )}

      {loadState === "success" && topics.length > 0 && (
        <motion.div
          className="mt-5 flex flex-wrap gap-2"
          initial="hidden"
          animate="show"
        >
          {topics.map((t, i) => (
            <motion.span
              key={t}
              custom={i}
              variants={chipVariants}
              className={`cursor-pointer rounded-lg border px-3 py-1.5 text-xs font-semibold backdrop-blur-sm transition-all duration-200 hover:-translate-y-0.5 ${chipColors[i % chipColors.length]}`}
            >
              {t}
            </motion.span>
          ))}
        </motion.div>
      )}

      {loadState === "success" && topics.length === 0 && (
        <p className="mt-5 text-xs text-slate-500">All known CF tags have been attempted. Impressive!</p>
      )}

      {(loadState === "idle" || loadState === "error") && (
        <p className="mt-5 text-xs text-slate-500">Sync a handle to see unexplored topics.</p>
      )}

      {topics.length > 0 && (
        <div className="mt-6 flex items-start gap-2 rounded-xl border border-violet-400/10 bg-violet-500/5 p-3">
          <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-400" />
          <p className="text-[11px] leading-relaxed text-slate-500">
            Tackle one unexplored topic each week to broaden your competitive surface area.
          </p>
        </div>
      )}
    </GlassCard>
  );
}
