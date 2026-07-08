import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Code2,
  Search,
  Loader2,
  ExternalLink,
  Copy,
  Check,
  Clock,
  Zap,
  ShieldCheck,
  AlertTriangle,
  ArrowLeft,
  ChevronRight,
} from "lucide-react";
import {
  issueChallenge,
  verifyChallenge,
  setAuthToken,
  type ChallengeResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/authStore";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Verify Ownership — Codeforces Companion" },
      {
        name: "description",
        content: "Prove you own your Codeforces handle via a TLE submission.",
      },
    ],
  }),
  component: LoginPage,
});

// ---------------------------------------------------------------------------
// Countdown timer hook
// ---------------------------------------------------------------------------
function useCountdown(expiresAt: string | null) {
  const [secondsLeft, setSecondsLeft] = useState<number>(0);

  useEffect(() => {
    if (!expiresAt) return;
    const tick = () => {
      const diff = Math.max(
        0,
        Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000)
      );
      setSecondsLeft(diff);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [expiresAt]);

  const mm = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
  const ss = String(secondsLeft % 60).padStart(2, "0");
  return { secondsLeft, label: `${mm}:${ss}` };
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------
function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isRestoringSession, setAuthenticatedUser } = useAuth();

  // If already authenticated, go straight to dashboard.
  useEffect(() => {
    if (!isRestoringSession && isAuthenticated) {
      navigate({ to: "/" });
    }
  }, [isAuthenticated, isRestoringSession, navigate]);

  type Step = "handle" | "challenge" | "success";
  const [step, setStep] = useState<Step>("handle");
  const [handle, setHandle] = useState("");
  const [challenge, setChallenge] = useState<ChallengeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { secondsLeft, label: countdownLabel } = useCountdown(
    challenge?.expires_at ?? null
  );

  // Stop polling when component unmounts.
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // When challenge expires, stop polling and show error.
  useEffect(() => {
    if (secondsLeft === 0 && isPolling) {
      stopPolling();
      setError("Challenge expired. Please start over and request a new one.");
      setStep("handle");
    }
  }, [secondsLeft, isPolling]);

  // ---------- Step 1: Issue challenge ----------
  const handleIssueChallenge = async (e: React.FormEvent) => {
    e.preventDefault();
    const h = handle.trim();
    if (!h) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await issueChallenge(h);
      setChallenge(data);
      setStep("challenge");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to issue challenge."
      );
    } finally {
      setIsLoading(false);
    }
  };

  // ---------- Step 2: Poll for TLE verification ----------
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const startPolling = useCallback(() => {
    if (!handle || isPolling) return;
    setIsPolling(true);
    setError(null);

    const poll = async () => {
      try {
        const result = await verifyChallenge(handle.trim());
        if (result.status === "ok" && result.access_token && result.cf_handle) {
          stopPolling();
          setAuthToken(result.access_token);
          setAuthenticatedUser(result.cf_handle);
          setStep("success");
          setTimeout(() => navigate({ to: "/" }), 1800);
        }
        // "pending" → keep polling
      } catch (err) {
        stopPolling();
        setError(
          err instanceof Error ? err.message : "Verification failed. Try again."
        );
      }
    };

    poll(); // immediate first check
    pollRef.current = setInterval(poll, 4000);
  }, [handle, isPolling, stopPolling, setAuthenticatedUser, navigate]);

  // ---------- Copy snippet ----------
  const copySnippet = () => {
    if (!challenge) return;
    navigator.clipboard.writeText(challenge.snippet).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (isRestoringSession) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
      </div>
    );
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center bg-slate-950 px-4 overflow-hidden">
      {/* Ambient background blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-indigo-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-purple-600/10 blur-3xl" />
        <div className="absolute top-1/2 left-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-600/5 blur-2xl" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        {/* Logo header */}
        <motion.div
          className="mb-8 flex flex-col items-center text-center"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-[0_0_30px_rgba(99,102,241,0.35)]">
            <Code2 className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-black tracking-tight text-white">
            Codeforces Companion
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Prove ownership · No passwords needed
          </p>
        </motion.div>

        <AnimatePresence mode="wait">
          {/* ─── STEP 1: Handle Input ─────────────────────────────── */}
          {step === "handle" && (
            <motion.div
              key="handle"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.35 }}
              className="rounded-2xl border border-white/[0.06] bg-slate-900/60 p-8 backdrop-blur-xl shadow-2xl"
            >
              <div className="mb-6">
                <h2 className="text-base font-black text-white">
                  Verify Your CF Handle
                </h2>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
                  Enter your Codeforces handle. We'll assign you a problem —
                  submit an infinite loop to get a{" "}
                  <span className="font-semibold text-rose-400">TLE</span>, and
                  we'll confirm it's you.
                </p>
              </div>

              <form onSubmit={handleIssueChallenge} className="space-y-4">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <input
                    id="cf-handle-input"
                    type="text"
                    value={handle}
                    onChange={(e) => setHandle(e.target.value)}
                    placeholder="e.g. tourist"
                    autoComplete="off"
                    className="w-full rounded-xl border border-white/[0.06] bg-slate-950/60 py-3 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-600 outline-none transition-all focus:border-indigo-500/50 focus:shadow-[0_0_20px_rgba(99,102,241,0.15)]"
                  />
                </div>

                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-2 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2"
                  >
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-rose-400" />
                    <p className="text-xs text-rose-300">{error}</p>
                  </motion.div>
                )}

                <button
                  id="verify-handle-btn"
                  type="submit"
                  disabled={isLoading || !handle.trim()}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 py-3 text-sm font-bold text-white shadow-[0_4px_24px_rgba(99,102,241,0.3)] transition-all hover:shadow-[0_4px_32px_rgba(99,102,241,0.45)] hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Checking handle…
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="h-4 w-4" />
                      Get Verification Challenge
                      <ChevronRight className="h-3.5 w-3.5 opacity-60" />
                    </>
                  )}
                </button>
              </form>

              {/* How it works */}
              <div className="mt-6 border-t border-white/[0.04] pt-5">
                <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-600">
                  How it works
                </p>
                <div className="space-y-2">
                  {[
                    {
                      icon: "①",
                      text: "Enter your CF handle → get a challenge problem",
                    },
                    {
                      icon: "②",
                      text: "Submit an infinite loop → receive a TLE verdict",
                    },
                    {
                      icon: "③",
                      text: "We verify the TLE via the CF API → you're in",
                    },
                  ].map((item) => (
                    <div
                      key={item.icon}
                      className="flex items-start gap-3 text-xs text-slate-500"
                    >
                      <span className="shrink-0 font-black text-indigo-500">
                        {item.icon}
                      </span>
                      <span>{item.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* ─── STEP 2: Challenge ───────────────────────────────── */}
          {step === "challenge" && challenge && (
            <motion.div
              key="challenge"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.35 }}
              className="rounded-2xl border border-white/[0.06] bg-slate-900/60 p-8 backdrop-blur-xl shadow-2xl"
            >
              {/* Header */}
              <div className="mb-5 flex items-start justify-between">
                <div>
                  <h2 className="text-base font-black text-white">
                    Submit a TLE
                  </h2>
                  <p className="mt-1 text-xs text-slate-400">
                    Proving ownership for{" "}
                    <span className="font-bold text-indigo-300">{handle}</span>
                  </p>
                </div>
                {/* Countdown */}
                <div
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-black ${
                    secondsLeft < 120
                      ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                      : "border-indigo-500/30 bg-indigo-500/10 text-indigo-300"
                  }`}
                >
                  <Clock className="h-3 w-3" />
                  {countdownLabel}
                </div>
              </div>

              {/* Challenge problem */}
              <div className="mb-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                <p className="mb-1 text-[10px] font-black uppercase tracking-widest text-amber-500/70">
                  Challenge Problem
                </p>
                <p className="text-sm font-bold text-white">
                  {challenge.problem_id} — {challenge.problem_title}
                </p>
                <a
                  id="open-problem-link"
                  href={challenge.problem_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 flex items-center gap-1.5 text-[11px] font-bold text-amber-400 hover:text-amber-300 transition-colors"
                >
                  <ExternalLink className="h-3 w-3" />
                  Open on Codeforces
                </a>
              </div>

              {/* Code snippet */}
              <div className="mb-5">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                    Submit this code (Python)
                  </p>
                  <button
                    onClick={copySnippet}
                    className="flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-bold text-slate-400 hover:bg-white/5 hover:text-slate-200 transition-all"
                  >
                    {copied ? (
                      <>
                        <Check className="h-3 w-3 text-green-400" />
                        <span className="text-green-400">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
                <div className="rounded-xl border border-white/[0.06] bg-slate-950 px-4 py-3 font-mono text-sm text-emerald-400">
                  <pre className="whitespace-pre-wrap">{challenge.snippet}</pre>
                </div>
                <p className="mt-2 text-[10px] text-slate-600">
                  Any language works — just make sure you get a{" "}
                  <span className="font-bold text-rose-400">
                    Time Limit Exceeded
                  </span>{" "}
                  verdict.
                </p>
              </div>

              {/* Error */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 flex items-center gap-2 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2"
                >
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-rose-400" />
                  <p className="text-xs text-rose-300">{error}</p>
                </motion.div>
              )}

              {/* Actions */}
              <div className="flex flex-col gap-2">
                <button
                  id="check-tle-btn"
                  onClick={startPolling}
                  disabled={isPolling || secondsLeft === 0}
                  className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 py-3 text-sm font-bold text-white shadow-[0_4px_24px_rgba(99,102,241,0.3)] transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {isPolling ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Checking for TLE verdict…
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4" />
                      I've Submitted — Verify Now
                    </>
                  )}
                </button>

                {isPolling && (
                  <p className="text-center text-[10px] text-slate-600 animate-pulse">
                    Polling Codeforces API every 4 seconds…
                  </p>
                )}

                <button
                  onClick={() => {
                    stopPolling();
                    setStep("handle");
                    setChallenge(null);
                    setError(null);
                  }}
                  className="flex items-center justify-center gap-1.5 py-2 text-xs text-slate-600 hover:text-slate-400 transition-colors"
                >
                  <ArrowLeft className="h-3 w-3" />
                  Use a different handle
                </button>
              </div>
            </motion.div>
          )}

          {/* ─── STEP 3: Success ─────────────────────────────────── */}
          {step === "success" && (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, type: "spring" }}
              className="rounded-2xl border border-white/[0.06] bg-slate-900/60 p-10 backdrop-blur-xl shadow-2xl text-center"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 border border-emerald-500/30 shadow-[0_0_30px_rgba(16,185,129,0.2)]"
              >
                <ShieldCheck className="h-8 w-8 text-emerald-400" />
              </motion.div>

              <h2 className="text-xl font-black text-white mb-1">
                Ownership Verified! ✅
              </h2>
              <p className="text-sm text-slate-400 mb-1">
                Welcome,{" "}
                <span className="font-bold text-indigo-300">{handle}</span>
              </p>
              <p className="text-xs text-slate-600">
                Redirecting to your dashboard…
              </p>

              <div className="mt-6 flex justify-center">
                <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
