import { useState } from "react";
import { Bot, Scan, Loader2, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { GlassCard } from "./GlassCard";
import { useDashboard } from "@/lib/store";
import { getAiCoach } from "@/lib/api";

export function CoachCard() {
  const { handle, loadState } = useDashboard();
  const [scanning, setScanning] = useState(false);
  const [summary, setSummary] = useState(null);
  const [coachError, setCoachError] = useState(null);

  const onScan = async () => {
    if (!handle || scanning) return;
    setScanning(true);
    setCoachError(null);
    try {
      const res = await getAiCoach(handle);
      setSummary(res.summary);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Diagnostic failed";
      setCoachError(
        msg.includes("400") || msg.toLowerCase().includes("missing")
          ? "Analytics cache expired. Please sync the handle again first."
          : msg
      );
    } finally {
      setScanning(false);
    }
  };

  return (
    <GlassCard glow="green" className="flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10">
          <Bot className="h-3.5 w-3.5 text-emerald-300" />
        </div>
        <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
          Coach's Diagnostic
        </h3>
        {summary && (
          <span className="ml-auto rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold text-emerald-400">
            AI Powered
          </span>
        )}
      </div>

      {/* Body */}
      <div className="my-4 flex flex-1 flex-col overflow-hidden">
        <AnimatePresence mode="wait">
          {/* Idle / ready */}
          {!summary && !scanning && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-1 flex-col items-center justify-center text-center gap-4">
              {/* Animated scan rings */}
              <div className="relative">
                <div className="absolute inset-0 animate-ping rounded-full bg-emerald-400/10" style={{ animationDuration: "2s" }} />
                <div className="absolute inset-0 animate-ping rounded-full bg-emerald-400/5" style={{ animationDuration: "3s", animationDelay: "0.5s" }} />
                <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-emerald-400/25 bg-gradient-to-br from-emerald-500/15 to-teal-500/10 shadow-[0_0_24px_rgba(16,185,129,0.2)]">
                  <Scan className="h-6 w-6 text-emerald-300" />
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-semibold text-slate-300">
                  {loadState === "success" ? "AI Coach Ready" : "Awaiting Data"}
                </p>
                <p className="max-w-[200px] text-xs leading-relaxed text-slate-500">
                  {loadState === "success"
                    ? "Run a diagnostic to get your personalized coaching analysis."
                    : "Sync a Codeforces handle to enable the AI coach."}
                </p>
              </div>
              {coachError && (
                <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-red-400/20 bg-red-500/10 px-3 py-2 text-xs text-red-300 max-w-xs">
                  {coachError}
                </motion.p>
              )}
            </motion.div>
          )}

          {/* Scanning state */}
          {scanning && (
            <motion.div key="scanning" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-1 flex-col items-center justify-center gap-4">
              <div className="relative">
                <Loader2 className="h-10 w-10 animate-spin text-emerald-400" />
                <div className="absolute inset-0 rounded-full bg-emerald-400/10 animate-pulse" />
              </div>
              <div className="space-y-1 text-center">
                <p className="text-sm font-semibold text-slate-300">Analyzing Performance…</p>
                <p className="text-xs text-slate-500">Gemini AI is auditing your code profile</p>
              </div>
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <motion.div key={i} className="h-1.5 w-1.5 rounded-full bg-emerald-400"
                    animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }} />
                ))}
              </div>
            </motion.div>
          )}

          {/* Summary */}
          {summary && !scanning && (
            <motion.div key="summary" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="flex-1 overflow-y-auto pr-1">
              {/* AI badge */}
              <div className="mb-3 flex items-center gap-2">
                <Sparkles className="h-3 w-3 text-emerald-400" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400/80">Gemini Analysis</span>
              </div>
              <div className="ai-coach-summary-content">
                <ReactMarkdown>{summary}</ReactMarkdown>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Button */}
      <button
        id="run-diagnostic-button" type="button" onClick={onScan}
        disabled={loadState !== "success" || scanning}
        className="group relative inline-flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl border border-emerald-400/25 bg-gradient-to-br from-emerald-500/15 to-teal-500/10 px-5 py-3.5 text-sm font-bold text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.15)] transition-all duration-300 hover:border-emerald-400/40 hover:shadow-[0_0_28px_rgba(16,185,129,0.35)] active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <span className="pointer-events-none absolute inset-0 -translate-x-full skew-x-12 bg-gradient-to-r from-transparent via-white/10 to-transparent transition-transform duration-700 group-hover:translate-x-full" aria-hidden />
        {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Scan className="h-4 w-4" />}
        {summary ? "Re-run Diagnostic" : "Run Diagnostic Scan"}
      </button>
    </GlassCard>
  );
}
