import { useEffect, useRef } from "react";
import { GlassCard } from "./GlassCard";
import { CountUp } from "./CountUp";

const themes = {
  blue: {
    glow: "blue",
    iconBg: "bg-blue-500/10 ring-blue-400/25 text-blue-300",
    valueColor: "from-blue-300 to-cyan-300",
    accentBar: "from-blue-500 via-cyan-400 to-blue-400",
    accentGlow: "shadow-[0_0_16px_rgba(59,130,246,0.6)]",
    dotColor: "bg-blue-400",
  },
  green: {
    glow: "green",
    iconBg: "bg-emerald-500/10 ring-emerald-400/25 text-emerald-300",
    valueColor: "from-emerald-300 to-teal-300",
    accentBar: "from-emerald-500 via-teal-400 to-emerald-400",
    accentGlow: "shadow-[0_0_16px_rgba(16,185,129,0.6)]",
    dotColor: "bg-emerald-400",
  },
  red: {
    glow: "none",
    iconBg: "bg-red-500/10 ring-red-400/25 text-red-300",
    valueColor: "from-red-300 to-rose-300",
    accentBar: "from-red-500 via-rose-400 to-red-400",
    accentGlow: "shadow-[0_0_16px_rgba(239,68,68,0.5)]",
    dotColor: "bg-red-400",
  },
  orange: {
    glow: "yellow",
    iconBg: "bg-orange-500/10 ring-orange-400/25 text-orange-300",
    valueColor: "from-orange-300 to-amber-300",
    accentBar: "from-orange-500 via-amber-400 to-orange-400",
    accentGlow: "shadow-[0_0_16px_rgba(249,115,22,0.6)]",
    dotColor: "bg-orange-400",
  },
};

export function StatCard({ label, value, decimals = 0, suffix = "", icon: Icon, accent = "blue", display = "" }) {
  const t = themes[accent] ?? themes.blue;
  const cardRef = useRef(null);

  // Pop animation when value changes
  useEffect(() => {
    if (!cardRef.current || value === 0) return;
    cardRef.current.classList.remove("animate-count-pop");
    void cardRef.current.offsetWidth;
    cardRef.current.classList.add("animate-count-pop");
  }, [value]);

  return (
    <GlassCard glow={t.glow} className="relative flex h-full flex-col justify-between overflow-hidden">
      {/* Background number watermark */}
      <div
        className="pointer-events-none absolute -right-4 -top-3 select-none text-8xl font-black opacity-[0.025] text-white"
        aria-hidden
      >
        {display || (value ? Math.round(value) : "—")}
      </div>

      {/* Top row: label + icon */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
          {label}
        </span>
        <span className={`flex h-9 w-9 items-center justify-center rounded-xl ring-1 ${t.iconBg}`}>
          <Icon className="h-4 w-4" />
        </span>
      </div>

      {/* Main value */}
      <div ref={cardRef} className={`mt-3 bg-gradient-to-br ${t.valueColor} bg-clip-text text-5xl font-black tracking-tight text-transparent`}>
        {display ? display : <CountUp end={value} decimals={decimals} suffix={suffix} />}
      </div>

      {/* Accent bar at bottom */}
      <div className={`mt-4 h-[3px] w-full overflow-hidden rounded-full bg-white/5`}>
        <div className={`h-full rounded-full bg-gradient-to-r ${t.accentBar} ${t.accentGlow} animate-bar-grow`}
          style={{ width: display ? "100%" : value > 0 ? "100%" : "0%" }}
        />
      </div>

      {/* Dot indicator */}
      <div className={`absolute top-3 right-3 h-1.5 w-1.5 rounded-full ${t.dotColor} opacity-60`} />
    </GlassCard>
  );
}
