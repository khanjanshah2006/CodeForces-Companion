import { useState } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { TrendingUp } from "lucide-react";
import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";
import { useDashboard } from "@/lib/store";

export function RatingHistoryChart() {
  const { stats, loadState } = useDashboard();
  const [activeIndex, setActiveIndex] = useState(null);

  const history = stats?.ratingHistory || [];

  const data = history.map((item, idx) => {
    const prevRating = idx > 0 ? history[idx - 1].rating : 0;
    const change = idx > 0 ? item.rating - prevRating : item.rating;
    return {
      name: item.contestName,
      date: new Date(item.date).toLocaleDateString(undefined, {
        month: "short",
        year: "2-digit",
      }),
      fullDate: new Date(item.date).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      }),
      rating: item.rating,
      change,
    };
  });

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const item = payload[0].payload;
    const changeStr = item.change >= 0 ? `+${item.change}` : `${item.change}`;
    const changeColor = item.change >= 0 ? "text-emerald-400" : "text-rose-400";

    return (
      <div className="rounded-xl border border-white/10 bg-slate-950/95 px-4 py-3 backdrop-blur-xl shadow-2xl">
        <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500 mb-0.5">
          {item.fullDate}
        </p>
        <p className="max-w-[220px] text-xs font-semibold text-white leading-tight mb-2 truncate">
          {item.name}
        </p>
        <div className="flex items-baseline gap-2">
          <span className="text-xl font-black text-blue-400">{item.rating}</span>
          <span className={`text-xs font-bold ${changeColor}`}>{changeStr}</span>
        </div>
      </div>
    );
  };

  const minRating = data.length > 0 ? Math.max(0, Math.min(...data.map((d) => d.rating)) - 100) : 0;
  const maxRating = data.length > 0 ? Math.max(...data.map((d) => d.rating)) + 100 : 2000;

  return (
    <GlassCard glow="blue" className="flex flex-col h-[340px]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-500/10">
            <TrendingUp className="h-3.5 w-3.5 text-blue-300" />
          </div>
          <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
            Rating History
          </h3>
        </div>
        {data.length > 0 && (
          <span className="rounded-full border border-blue-400/25 bg-blue-500/10 px-2 py-0.5 text-[9px] font-black text-blue-300">
            {data.length} contests
          </span>
        )}
      </div>

      <div className="mt-6 flex-1 w-full min-h-0">
        {loadState === "loading" && (
          <div className="flex h-full items-end gap-2 pb-4 animate-pulse">
            <div className="h-1/2 w-full rounded bg-white/5" />
          </div>
        )}

        {loadState === "success" && data.length > 0 && (
          <motion.div
            className="h-full w-full"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data}
                margin={{ top: 8, right: 8, left: -22, bottom: 0 }}
                onMouseMove={(state) => {
                  if (state.activeTooltipIndex !== undefined) {
                    setActiveIndex(state.activeTooltipIndex);
                  }
                }}
                onMouseLeave={() => setActiveIndex(null)}
              >
                <defs>
                  <linearGradient id="colorRating" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="transparent"
                  tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 9, fontWeight: 500 }}
                  tickLine={false}
                  axisLine={false}
                  dy={6}
                />
                <YAxis
                  stroke="transparent"
                  domain={[minRating, maxRating]}
                  tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 9 }}
                  tickLine={false}
                  axisLine={false}
                  dx={-4}
                />
                <Tooltip
                  content={<CustomTooltip />}
                  cursor={{
                    stroke: "rgba(255, 255, 255, 0.1)",
                    strokeWidth: 1.5,
                    strokeDasharray: "4 4",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="rating"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorRating)"
                  dot={({ cx, cy, index }) => {
                    const active = activeIndex === index;
                    return (
                      <circle
                        key={index}
                        cx={cx}
                        cy={cy}
                        r={active ? 5 : 2}
                        fill={active ? "#3b82f6" : "rgba(59, 130, 246, 0.7)"}
                        stroke={active ? "#ffffff" : "transparent"}
                        strokeWidth={1}
                        style={{ transition: "all 0.15s ease" }}
                      />
                    );
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {loadState === "success" && data.length === 0 && (
          <p className="flex h-full items-center justify-center text-xs text-slate-500">
            No official contests recorded for this handle.
          </p>
        )}

        {(loadState === "idle" || loadState === "error") && (
          <p className="flex h-full items-center justify-center text-xs text-slate-500">
            Sync a handle to view rating history.
          </p>
        )}
      </div>
    </GlassCard>
  );
}
