import { Trophy, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { useDashboard } from "@/lib/store";

export function ContestsList() {
  const { stats, loadState } = useDashboard();

  const history = stats?.ratingHistory || [];
  // Reverse to show newest first
  const displayHistory = [...history].reverse();

  return (
    <GlassCard glow="blue" className="flex flex-col h-[340px]">
      <div className="flex items-center gap-2 mb-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-500/10">
          <Trophy className="h-3.5 w-3.5 text-blue-300" />
        </div>
        <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
          Contest History
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {loadState === "loading" && (
          <div className="space-y-3 animate-pulse">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-10 rounded-lg bg-white/5" />
            ))}
          </div>
        )}

        {loadState === "success" && displayHistory.length > 0 && (
          <div className="space-y-2">
            {displayHistory.map((item, idx) => {
              // Note: item is in displayHistory which is reversed.
              // To find the previous rating, we look at the original history:
              // original index of `item` is `history.length - 1 - idx`
              const origIdx = history.length - 1 - idx;
              const prevRating = origIdx > 0 ? history[origIdx - 1].rating : 0;
              const change = origIdx > 0 ? item.rating - prevRating : item.rating;
              const changePositive = change >= 0;

              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: Math.min(idx * 0.05, 0.4) }}
                  className="flex items-center justify-between rounded-xl border border-white/[0.03] bg-white/[0.01] p-3 transition-colors hover:bg-white/[0.03]"
                >
                  <div className="min-w-0 pr-2">
                    <h4 className="truncate text-xs font-semibold text-slate-200" title={item.contestName}>
                      {item.contestName}
                    </h4>
                    <p className="text-[9px] text-slate-500 mt-0.5">
                      {new Date(item.date).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <p className="text-xs font-bold text-slate-300">{item.rating}</p>
                      <p className="text-[9px] text-slate-500">rating</p>
                    </div>

                    <div
                      className={`flex items-center gap-0.5 rounded-lg px-2 py-1 text-xs font-bold ${
                        changePositive
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/10"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/10"
                      }`}
                    >
                      {changePositive ? (
                        <ArrowUpRight className="h-3 w-3" />
                      ) : (
                        <ArrowDownRight className="h-3 w-3" />
                      )}
                      <span>{changePositive ? `+${change}` : change}</span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {loadState === "success" && displayHistory.length === 0 && (
          <p className="text-center py-8 text-xs text-slate-500">
            No contests found.
          </p>
        )}

        {(loadState === "idle" || loadState === "error") && (
          <p className="text-center py-8 text-xs text-slate-500">
            Sync a handle to view contest history.
          </p>
        )}
      </div>
    </GlassCard>
  );
}
