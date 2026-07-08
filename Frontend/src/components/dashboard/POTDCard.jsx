import { useState, useEffect } from "react";
import { Sparkles, Zap, CheckCircle2, Loader2, ExternalLink, Calendar, Tag, Flame } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { useDashboard } from "@/lib/store";
import { verifyPotd } from "@/lib/api";

const verifyTheme = {
  success: "border-emerald-400/25 bg-emerald-500/10 text-emerald-300",
  warn:    "border-yellow-400/25 bg-yellow-500/10 text-yellow-300",
  info:    "border-blue-400/25 bg-blue-500/10 text-blue-300",
};

export function POTDCard() {
  const { handle, loadState, potd, markPotdSolved } = useDashboard();
  const [verifying, setVerifying] = useState(false);
  const [verifyMsg, setVerifyMsg] = useState(null);
  const [verifyVariant, setVerifyVariant] = useState(null);

  useEffect(() => {
    if (verifyMsg) {
      const timer = setTimeout(() => {
        setVerifyMsg(null);
        setVerifyVariant(null);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [verifyMsg]);

  const onVerify = async () => {
    if (!handle || verifying) return;
    setVerifying(true);
    setVerifyMsg(null);
    try {
      const res = await verifyPotd(handle);
      if (res.status === "NEWLY_SOLVED") {
        markPotdSolved();
        setVerifyMsg("🎉 Congratulations! Problem marked as solved!");
        setVerifyVariant("success");
      } else if (res.status === "ALREADY_SOLVED") {
        setVerifyMsg("✅ Already solved — streak maintained!");
        setVerifyVariant("success");
      } else if (res.status === "STILL_PENDING") {
        setVerifyMsg("⏳ Not solved yet — keep going!");
        setVerifyVariant("warn");
      } else {
        setVerifyMsg("No POTD generated for today.");
        setVerifyVariant("info");
      }
    } catch (err) {
      setVerifyMsg(err instanceof Error ? err.message : "Verification failed");
      setVerifyVariant("warn");
    } finally {
      setVerifying(false);
    }
  };

  const isSolved = potd?.status === "SOLVED";
  const cfLink = potd
    ? `https://codeforces.com/problemset/problem/${potd.problem_id.replace(/([A-Z])$/, "/$1")}`
    : "#";

  return (
    <GlassCard glow="yellow" className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-yellow-400/10">
            <Sparkles className="h-3.5 w-3.5 text-yellow-300" />
          </div>
          <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">Problem of the Day</h3>
        </div>
        <AnimatePresence mode="wait">
          {potd && (
            <motion.span
              key={isSolved ? "solved" : "pending"}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className={`rounded-full border px-2.5 py-0.5 text-[9px] font-black uppercase tracking-wider ${
                isSolved
                  ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300 shadow-[0_0_10px_rgba(52,211,153,0.3)]"
                  : "border-yellow-400/30 bg-yellow-400/10 text-yellow-300 shadow-[0_0_10px_rgba(234,179,8,0.25)]"
              }`}
            >
              {isSolved ? "✓ Solved" : "● Pending"}
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Content */}
      {loadState === "loading" && (
        <div className="mt-5 space-y-3 animate-pulse">
          <div className="h-6 w-3/4 rounded-lg bg-white/5" />
          <div className="flex gap-2">
            <div className="h-6 w-24 rounded-lg bg-white/5" />
            <div className="h-6 w-16 rounded-lg bg-white/5" />
          </div>
        </div>
      )}

      {loadState === "success" && potd && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <a href={cfLink} target="_blank" rel="noopener noreferrer"
            className="group mt-5 flex items-start gap-1.5">
            <h2 className="text-xl font-black leading-snug text-white transition-colors group-hover:text-blue-300">
              {potd.problem_title}
            </h2>
            <ExternalLink className="mt-1.5 h-3.5 w-3.5 shrink-0 text-slate-500 transition-colors group-hover:text-blue-400" />
          </a>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-lg border border-blue-400/20 bg-blue-500/10 px-2.5 py-1.5 text-xs font-bold text-blue-300">
              <Zap className="h-3 w-3" />
              Difficulty {potd.difficulty}
            </span>
            {potd.problem_tags ? (
              potd.problem_tags.map(tag => (
                <span key={tag} className="flex items-center gap-1.5 rounded-lg border border-violet-400/20 bg-violet-500/10 px-2.5 py-1.5 text-xs font-semibold text-violet-300">
                  <Tag className="h-3 w-3" />
                  {tag}
                </span>
              ))
            ) : (
              potd.problem_tag && (
                <span className="flex items-center gap-1.5 rounded-lg border border-violet-400/20 bg-violet-500/10 px-2.5 py-1.5 text-xs font-semibold text-violet-300">
                  <Tag className="h-3 w-3" />
                  {potd.problem_tag}
                </span>
              )
            )}
            {potd.streak !== undefined && potd.streak > 0 && (
              <span className="flex items-center gap-1.5 rounded-lg border border-orange-400/20 bg-orange-500/10 px-2.5 py-1.5 text-xs font-black text-orange-300">
                <Flame className="h-3 w-3 text-orange-400 fill-orange-400" />
                {potd.streak} Day Streak
              </span>
            )}
            <span className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs text-slate-400">
              <Calendar className="h-3 w-3" />
              {potd.assigned_date}
            </span>
          </div>

          <AnimatePresence>
            {verifyMsg && verifyVariant && (
              <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className={`mt-4 rounded-xl border px-3 py-2.5 text-xs font-medium ${verifyTheme[verifyVariant]}`}>
                {verifyMsg}
              </motion.p>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {(loadState === "idle" || loadState === "error") && (
        <p className="mt-5 text-sm text-slate-500">Sync a handle to see today's problem.</p>
      )}

      {/* CTA button */}
      <div className="mt-auto pt-6">
        {isSolved ? (
          <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-5 py-3.5 text-sm font-bold text-emerald-300 shadow-[0_0_20px_rgba(52,211,153,0.2)]">
            <CheckCircle2 className="h-4 w-4" />
            Problem Solved!
          </motion.div>
        ) : (
          <button
            id="verify-potd-button" type="button" onClick={onVerify}
            disabled={!potd || verifying || loadState !== "success"}
            className="group relative inline-flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-400 px-5 py-3.5 text-sm font-bold text-white shadow-[0_0_24px_rgba(59,130,246,0.4)] transition-all duration-300 hover:shadow-[0_0_40px_rgba(59,130,246,0.65)] active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {/* Shimmer sweep */}
            <span className="pointer-events-none absolute inset-0 -translate-x-full skew-x-12 bg-gradient-to-r from-transparent via-white/15 to-transparent transition-transform duration-700 group-hover:translate-x-full" aria-hidden />
            {verifying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            {verifying ? "Checking…" : "Verify Solution"}
          </button>
        )}
      </div>
    </GlassCard>
  );
}
