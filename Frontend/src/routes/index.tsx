import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Target, AlertTriangle, Code2, Search, Loader2, Sparkles, RefreshCw, Trophy, Crown, Flame, LogOut } from "lucide-react";
import { StatCard } from "@/components/dashboard/StatCard";
import { POTDCard } from "@/components/dashboard/POTDCard";
import { CoachCard } from "@/components/dashboard/CoachCard";
import { RatingChart } from "@/components/dashboard/RatingChart";
import { TagPerformance } from "@/components/dashboard/TagPerformance";
import { UnexploredTopics } from "@/components/dashboard/UnexploredTopics";
import { RatingHistoryChart } from "@/components/dashboard/RatingHistoryChart";
import { ContestsList } from "@/components/dashboard/ContestsList";
import { UnsolvedProblems } from "@/components/dashboard/UnsolvedProblems";
import { DashboardProvider, useDashboard } from "@/lib/store";
import { useAuth } from "@/lib/authStore";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Codeforces Companion — Competitive Programming Analytics" },
      { name: "description", content: "Elite competitive programming analytics with AI coaching." },
    ],
  }),
  component: () => (
    <DashboardProvider>
      <AuthGuard />
    </DashboardProvider>
  ),
});

/* ─── Auth Guard ─────────────────────────────────────────── */
function AuthGuard() {
  const { isAuthenticated, isRestoringSession, user } = useAuth();
  const navigate = useNavigate();
  const { doSync, loadState } = useDashboard();
  const hasSynced = useRef(false);

  // Redirect unauthenticated users to /login.
  useEffect(() => {
    if (!isRestoringSession && !isAuthenticated) {
      navigate({ to: "/login" });
    }
  }, [isAuthenticated, isRestoringSession, navigate]);

  // Auto-load the user's own CF handle on first authenticated render.
  useEffect(() => {
    if (isAuthenticated && user && loadState === "idle" && !hasSynced.current) {
      hasSynced.current = true;
      doSync(user.cfHandle);
    }
  }, [isAuthenticated, user, loadState, doSync]);

  if (isRestoringSession) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
          <p className="text-xs text-slate-500">Restoring session…</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return <Dashboard />;
}

/* ─── Rank Metadata ──────────────────────────────────────── */
const rankMeta: Record<string, { label: string; cls: string; badge: string }> = {
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
const getRank = (r: string | null | undefined) => {
  const key = r?.toLowerCase();
  return (key && rankMeta[key]) ? rankMeta[key] : rankMeta.unrated;
};

/* ─── Interactive Background Canvas ────────────────────────── */
interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  baseAlpha: number;
}

function InteractiveBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const particles: Particle[] = [];
    const particleCount = Math.min(50, Math.floor((width * height) / 25000));

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 1.5 + 1,
        baseAlpha: Math.random() * 0.2 + 0.08,
      });
    }

    let mouse = { x: -1000, y: -1000, active: false };

    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
    };

    const handleMouseLeave = () => {
      mouse.active = false;
    };

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseleave", handleMouseLeave);
    window.addEventListener("resize", handleResize);

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < particles.length; i++) {
        const p1 = particles[i];
        p1.x += p1.vx;
        p1.y += p1.vy;

        if (p1.x < 0 || p1.x > width) p1.vx *= -1;
        if (p1.y < 0 || p1.y > height) p1.vy *= -1;

        ctx.beginPath();
        ctx.arc(p1.x, p1.y, p1.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(148, 163, 184, ${p1.baseAlpha})`;
        ctx.fill();

        if (mouse.active) {
          const dx = mouse.x - p1.x;
          const dy = mouse.y - p1.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(mouse.x, mouse.y);
            const alpha = (1 - dist / 150) * 0.1;
            ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }

        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            const alpha = (1 - dist / 100) * 0.08;
            ctx.strokeStyle = `rgba(148, 163, 184, ${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return <canvas ref={canvasRef} className="interactive-canvas" />;
}

/* ─── Search Bar ─────────────────────────────────────────── */
interface SearchBarProps {
  className?: string;
  compact?: boolean;
}

function SearchBar({ className, compact = false }: SearchBarProps) {
  const { loadState, doSync } = useDashboard();
  const [input, setInput] = useState("");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) doSync(input.trim());
  };

  return (
    <form onSubmit={onSubmit} className={className}>
      <div className="relative flex items-center">
        <Search className="pointer-events-none absolute left-4 h-4 w-4 text-slate-500" />
        <input
          id="cf-handle-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter Codeforces handle…"
          className={`w-full rounded-full border border-white/[0.06] bg-slate-950/45 pl-11 pr-24 outline-none transition-all focus:border-blue-500/40 focus:bg-slate-950/70 focus:shadow-[0_0_24px_rgba(59,130,246,0.15)] text-slate-200 placeholder-slate-500 ${
            compact ? "py-2 text-xs" : "py-3 text-sm"
          }`}
        />
        <button
          id="sync-button"
          type="submit"
          disabled={loadState === "loading"}
          className={`absolute right-1.5 rounded-full bg-slate-900 border border-white/[0.08] hover:bg-slate-800 text-slate-300 font-bold transition-all active:scale-95 disabled:opacity-50 flex items-center justify-center gap-1.5 ${
            compact ? "px-3 py-1 text-[10px]" : "px-4 py-1.5 text-xs"
          }`}
        >
          {loadState === "loading" ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <RefreshCw className="h-3 w-3" />
          )}
          <span>Sync</span>
        </button>
      </div>
    </form>
  );
}

/* ─── Profile Header ─────────────────────────────────────── */
function ProfileHeader() {
  const { analytics } = useDashboard();
  if (!analytics) return null;

  const rank = getRank(analytics.rank);
  const barPct = analytics.max_rating > 0 ? Math.min(100, Math.round((analytics.current_rating / analytics.max_rating) * 100)) : 0;

  return (
    <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-4 rounded-2xl border border-white/[0.04] bg-slate-950/20 p-6 backdrop-blur-xl">
      <div className="flex items-center gap-4">
        <div className="relative shrink-0">
          <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${rank.cls} p-[1.5px]`} style={{ borderRadius: "16px" }}>
            <div className="h-full w-full rounded-2xl bg-slate-950" />
          </div>
          <div className={`relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${rank.cls} bg-opacity-20`}>
            <Crown className="h-6 w-6 text-white drop-shadow-lg" />
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-xl font-black text-white">{analytics.handle}</h2>
            <span className={`rounded-full border px-2.5 py-0.5 text-[8px] font-extrabold uppercase tracking-wider ${rank.badge}`}>
              {rank.label}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Codeforces competitive profile</p>
        </div>
      </div>

      <div className="flex items-end gap-6 w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 border-white/[0.04] pt-4 md:pt-0">
        <div>
          <p className="text-[9px] font-black uppercase tracking-wider text-slate-500 mb-0.5">Rating</p>
          <span className={`bg-gradient-to-r ${rank.cls} bg-clip-text text-3xl font-black text-transparent`}>
            {analytics.current_rating}
          </span>
        </div>

        <div>
          <p className="text-[9px] font-black uppercase tracking-wider text-slate-500 mb-0.5">Peak Rating</p>
          <span className="text-xl font-bold text-slate-400">
            {analytics.max_rating}
          </span>
        </div>

        <div className="hidden sm:block min-w-[120px]">
          <div className="flex justify-between text-[8px] font-black uppercase tracking-wider text-slate-500 mb-1">
            <span>Peak progress</span>
            <span>{barPct}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-white/[0.04] overflow-hidden">
            <div className={`h-full rounded-full bg-gradient-to-r ${rank.cls}`} style={{ width: `${barPct}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Dashboard ──────────────────────────────────────────── */
function Dashboard() {
  const { analytics, loadState, error, doSync, potd } = useDashboard();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate({ to: "/login" });
  };

  const totalSolved = analytics
    ? Object.values(analytics.problems_solved_by_rating).reduce((a, b) => a + b, 0)
    : 0;
  const acceptancePct = analytics ? Math.round(analytics.overall_acceptance_rate * 1000) / 10 : 0;
  const topError = analytics
    ? analytics.top_issue_verdict === "N/A"
      ? "N/A"
      : analytics.top_issue_verdict.replace("_", " ").slice(0, 15)
    : "—";

  return (
    <main className="relative min-h-screen w-full overflow-x-hidden bg-slate-950 text-slate-200">
      {/* Dynamic Background */}
      <InteractiveBackground />

      <div className="relative z-10 mx-auto max-w-[1200px] px-4 py-8 md:px-6 lg:px-8">
        {/* Navigation / Header */}
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-[0_0_20px_rgba(99,102,241,0.3)]">
              <Code2 className="h-4.5 w-4.5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white">
                Companion
              </h1>
              <p className="text-[9px] text-slate-500 leading-none mt-0.5">Codeforces Analytics</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.7)] animate-pulse" />
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest hidden sm:block">Minimalist v2.0</span>
            {/* Logout button */}
            <button
              id="logout-btn"
              onClick={handleLogout}
              title="Log out"
              className="flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-slate-900/50 px-3 py-1.5 text-[10px] font-bold text-slate-400 hover:border-rose-500/30 hover:bg-rose-500/10 hover:text-rose-300 transition-all"
            >
              <LogOut className="h-3 w-3" />
              <span className="hidden sm:block">Logout</span>
            </button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          {/* Idle / Input state */}
          {loadState === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <div className="relative mb-6">
                <div className="absolute inset-0 rounded-full bg-indigo-500/10 blur-xl" />
                <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-white/[0.06] bg-slate-900/40">
                  <Sparkles className="h-6 w-6 text-indigo-400" />
                </div>
              </div>
              <h2 className="text-2xl font-black tracking-tight text-white mb-2">
                Analyze your Competitive Profile
              </h2>
              <p className="max-w-[400px] text-xs text-slate-500 mb-8 leading-relaxed">
                Connect your Codeforces handle to fetch diagnostic metrics, unsolved problems, rating trends, and AI-powered recommendations.
              </p>
              <SearchBar className="w-full max-w-md" />
            </motion.div>
          )}

          {/* Error State */}
          {loadState === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-16 text-center"
            >
              <div className="rounded-full bg-rose-500/10 p-3 mb-4 border border-rose-500/10">
                <AlertTriangle className="h-6 w-6 text-rose-400" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">Diagnostic Sync Failed</h3>
              <p className="max-w-[320px] text-xs text-slate-500 mb-6">{error || "An unknown error occurred while contacting Codeforces."}</p>
              <SearchBar className="w-full max-w-sm mb-4" />
              <button
                onClick={() => window.location.reload()}
                className="text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition-all underline"
              >
                Go Back Home
              </button>
            </motion.div>
          )}

          {/* Syncing State */}
          {loadState === "loading" && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-28 text-center"
            >
              <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mb-4" />
              <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">
                Fetching Submissions
              </h3>
              <p className="text-[10px] text-slate-500">Contacting Codeforces API and processing stats...</p>
            </motion.div>
          )}

          {/* Success State */}
          {loadState === "success" && analytics && (
            <motion.div
              key="success"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="space-y-6"
            >
              {/* Profile Block */}
              <ProfileHeader />

              {/* Main Stats Grid */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                <StatCard
                  label="Total Solved"
                  value={totalSolved}
                  icon={CheckCircle2}
                  accent="blue"
                />
                <StatCard
                  label="Acceptance Rate"
                  value={acceptancePct}
                  decimals={1}
                  suffix="%"
                  icon={Target}
                  accent="green"
                />
                <StatCard
                  label="Daily Streak"
                  value={potd?.streak ?? 0}
                  suffix=" days"
                  icon={Flame}
                  accent="orange"
                />
                <StatCard
                  label="Major Issue"
                  value={0}
                  display={topError}
                  icon={AlertTriangle}
                  accent="red"
                />
              </div>

              {/* POTD Section */}
              <div className="grid grid-cols-1">
                <POTDCard />
              </div>

              {/* Charts & Lists Row */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <RatingHistoryChart />
                </div>
                <div className="lg:col-span-1">
                  <ContestsList />
                </div>
              </div>

              {/* Tag Analytics Grid */}
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <TagPerformance />
                <div className="space-y-6">
                  <UnsolvedProblems />
                  <UnexploredTopics />
                </div>
              </div>

              {/* AI Coaching Summary (Placed at the end) */}
              <div className="border-t border-white/[0.04] pt-8 mt-12">
                <CoachCard />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer */}
        <footer className="mt-16 border-t border-white/[0.04] py-6 text-center text-[9px] font-mono text-slate-600">
          Codeforces Companion · Minimalist Theme · Powered by Codeforces + Gemini AI
        </footer>
      </div>
    </main>
  );
}

