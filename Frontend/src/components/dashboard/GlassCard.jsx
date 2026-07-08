import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export const GlassCard = forwardRef(({ className, glow = "none", ...props }, ref) => {
  const glowMap = {
    none:  "",
    blue:  "hover:shadow-[0_0_32px_rgba(59,130,246,0.25),0_0_64px_rgba(59,130,246,0.08)] hover:border-blue-400/30",
    green: "hover:shadow-[0_0_32px_rgba(16,185,129,0.25),0_0_64px_rgba(16,185,129,0.08)] hover:border-emerald-400/30",
    violet:"hover:shadow-[0_0_32px_rgba(139,92,246,0.25),0_0_64px_rgba(139,92,246,0.08)] hover:border-violet-400/30",
    yellow:"hover:shadow-[0_0_32px_rgba(234,179,8,0.2),0_0_64px_rgba(234,179,8,0.07)] hover:border-yellow-400/30",
  };

  return (
    <div
      ref={ref}
      className={cn(
        // Base glass
        "relative overflow-hidden rounded-2xl border border-white/[0.07] bg-slate-900/60 p-6 backdrop-blur-xl",
        // Transition
        "transition-all duration-300 ease-out",
        // Hover lift + shadow
        "hover:-translate-y-1 hover:border-white/[0.12] hover:bg-slate-900/70 hover:shadow-2xl",
        // Per-card glow
        glowMap[glow] ?? "",
        className,
      )}
      {...props}
    >
      {/* Shimmer sweep on hover */}
      <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100 animate-shimmer rounded-2xl" aria-hidden />
      {/* Subtle inner top highlight */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" aria-hidden />
      {props.children}
    </div>
  );
});
GlassCard.displayName = "GlassCard";
