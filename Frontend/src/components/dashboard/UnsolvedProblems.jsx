import { HelpCircle, ExternalLink, RefreshCw, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { useDashboard } from "@/lib/store";

export function UnsolvedProblems() {
  const { analytics, loadState } = useDashboard();
  const problems = analytics?.unsolved_problems ?? [];

  return (
    <GlassCard glow="violet" className="flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-500/10">
          <HelpCircle className="h-3.5 w-3.5 text-violet-300" />
        </div>
        <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
          Unsolved Problems
        </h3>
        {problems.length > 0 && (
          <span className="ml-auto rounded-full border border-violet-400/25 bg-violet-500/15 px-2 py-0.5 text-[9px] font-black text-violet-300 shadow-[0_0_10px_rgba(139,92,246,0.25)]">
            {problems.length} remaining
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto pr-1 max-h-[240px]">
        {loadState === "loading" && (
          <div className="space-y-3 animate-pulse">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-10 rounded-lg bg-white/5" />
            ))}
          </div>
        )}

        {loadState === "success" && problems.length > 0 && (
          <div className="space-y-2">
            {problems.map((prob, idx) => {
              const cfLink = prob.contest_id && prob.index
                ? `https://codeforces.com/problemset/problem/${prob.contest_id}/${prob.index}`
                : `https://codeforces.com/problemset/problem/${prob.problem_id.replace(/([A-Z])$/, "/$1")}`;

              return (
                <motion.div
                  key={prob.problem_id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: Math.min(idx * 0.05, 0.4) }}
                  className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.03] bg-white/[0.01] p-3 transition-all hover:bg-white/[0.03]"
                >
                  <div className="min-w-0 flex-1">
                    <a
                      href={cfLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-center gap-1 text-xs font-semibold text-slate-200 hover:text-blue-400"
                    >
                      <span className="truncate">
                        <span className="text-[10px] text-slate-500 font-mono mr-1">
                          {prob.problem_id}
                        </span>
                        {prob.title}
                      </span>
                      <ExternalLink className="h-3 w-3 shrink-0 text-slate-500 group-hover:text-blue-400" />
                    </a>

                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {prob.rating && (
                        <span className="rounded bg-blue-500/10 px-1 py-0.5 text-[9px] font-bold text-blue-400">
                          {prob.rating}
                        </span>
                      )}
                      {prob.tags.slice(0, 2).map((t) => (
                        <span
                          key={t}
                          className="rounded bg-white/5 px-1 py-0.5 text-[9px] text-slate-400"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <div className="flex items-center gap-1 rounded-lg bg-rose-500/10 px-2 py-1 text-[10px] font-bold text-rose-400 border border-rose-500/10">
                      <AlertTriangle className="h-3 w-3" />
                      <span>{prob.failed_attempts} tries</span>
                    </div>
                    <p className="text-[8px] text-slate-500 font-mono">Unsolved</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {loadState === "success" && problems.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center gap-2">
            <RefreshCw className="h-5 w-5 text-slate-500 animate-spin" style={{ animationDuration: "8s" }} />
            <p className="text-xs text-slate-500">
              No unsolved problems with failed attempts! Excellent work.
            </p>
          </div>
        )}

        {(loadState === "idle" || loadState === "error") && (
          <p className="text-center py-8 text-xs text-slate-500">
            Sync a handle to view unsolved problems.
          </p>
        )}
      </div>
    </GlassCard>
  );
}
