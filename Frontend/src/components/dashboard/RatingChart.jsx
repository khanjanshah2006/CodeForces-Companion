import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";
import { BarChart3 } from "lucide-react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { useDashboard } from "@/lib/store";

const RATING_COLORS = [
  { min: 0,    max: 1199, from: "#64748b", to: "#94a3b8" }, // gray  — newbie
  { min: 1200, max: 1399, from: "#22c55e", to: "#4ade80" }, // green  — pupil
  { min: 1400, max: 1599, from: "#06b6d4", to: "#67e8f9" }, // cyan   — specialist
  { min: 1600, max: 1899, from: "#3b82f6", to: "#93c5fd" }, // blue   — expert
  { min: 1900, max: 2099, from: "#8b5cf6", to: "#c4b5fd" }, // violet — CM
  { min: 2100, max: 2399, from: "#f59e0b", to: "#fcd34d" }, // amber  — master
  { min: 2400, max: 9999, from: "#ef4444", to: "#fca5a5" }, // red    — grandmaster+
];

function getColor(rating) {
  const r = RATING_COLORS.find((c) => rating >= c.min && rating <= c.max);
  return r ?? RATING_COLORS[0];
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const c = getColor(Number(label));
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900/95 px-4 py-3 backdrop-blur-xl shadow-xl">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Rating {label}</p>
      <p className="text-lg font-black" style={{ background: `linear-gradient(to right, ${c.from}, ${c.to})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
        {payload[0].value} solved
      </p>
    </div>
  );
};

export function RatingChart() {
  const { analytics, loadState } = useDashboard();
  const [activeIndex, setActiveIndex] = useState(null);

  const data = analytics
    ? Object.entries(analytics.problems_solved_by_rating)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([rating, solved]) => ({ rating, solved }))
    : [];

  return (
    <GlassCard glow="blue" className="h-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-500/10">
            <BarChart3 className="h-3.5 w-3.5 text-blue-300" />
          </div>
          <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
            Problems by Rating
          </h3>
        </div>
        {data.length > 0 && (
          <span className="rounded-full border border-blue-400/20 bg-blue-500/10 px-2 py-0.5 text-[9px] font-bold text-blue-300">
            {data.reduce((a, b) => a + b.solved, 0)} total
          </span>
        )}
      </div>

      <div className="mt-6 h-60 w-full">
        {loadState === "loading" && (
          <div className="flex h-full items-end gap-2 pb-4">
            {[60, 90, 75, 45, 30, 20].map((h, i) => (
              <div key={i} className="flex-1 rounded-t-md bg-white/5 animate-pulse" style={{ height: `${h}%` }} />
            ))}
          </div>
        )}

        {loadState === "success" && data.length > 0 && (
          <motion.div
            className="h-full w-full"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}
                onMouseLeave={() => setActiveIndex(null)}>
                <defs>
                  {data.map(({ rating }, i) => {
                    const c = getColor(Number(rating));
                    return (
                      <linearGradient key={i} id={`bar-${i}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={c.from} stopOpacity={0.95} />
                        <stop offset="100%" stopColor={c.to} stopOpacity={0.5} />
                      </linearGradient>
                    );
                  })}
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="rating" stroke="transparent"
                  tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10, fontWeight: 600 }}
                  tickLine={false} axisLine={false} />
                <YAxis stroke="transparent"
                  tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10 }}
                  tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)", radius: 8 }} />
                <Bar dataKey="solved" radius={[6, 6, 2, 2]} maxBarSize={48}
                  onMouseEnter={(_, index) => setActiveIndex(index)}>
                  {data.map((_, i) => (
                    <Cell
                      key={i}
                      fill={`url(#bar-${i})`}
                      opacity={activeIndex === null || activeIndex === i ? 1 : 0.4}
                      style={{ filter: activeIndex === i ? `drop-shadow(0 0 8px ${getColor(Number(data[i].rating)).from}88)` : "none", transition: "opacity 0.2s, filter 0.2s" }}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {loadState === "success" && data.length === 0 && (
          <p className="flex h-full items-center justify-center text-xs text-slate-500">No solved problems recorded yet.</p>
        )}

        {(loadState === "idle" || loadState === "error") && (
          <p className="flex h-full items-center justify-center text-xs text-slate-500">Sync a handle to see the chart.</p>
        )}
      </div>
    </GlassCard>
  );
}
