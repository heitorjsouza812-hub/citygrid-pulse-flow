import type { ReactNode } from "react";

export function MetricaCard({
  icon, label, valor, unidade, sub, color = "var(--cyan-elec)", gradient = false, pct,
}: {
  icon: ReactNode;
  label: string;
  valor: string | number;
  unidade?: string;
  sub?: string;
  color?: string;
  gradient?: boolean;
  pct?: number;
}) {
  return (
    <div className="card-surface p-4 relative group transition-colors hover:border-[color-mix(in_oklab,var(--cyan-elec)_30%,var(--border))]">
      <div
        className="absolute inset-x-0 top-0 h-px opacity-80"
        style={{ background: gradient ? "var(--gradient-green)" : "var(--gradient-accent)" }}
      />
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-display font-bold">{label}</span>
        <span style={{ color }} className="opacity-70">{icon}</span>
      </div>
      <div className="font-mono text-[28px] leading-none font-bold tabular-nums tracking-tight transition-colors" style={{ color }}>
        {valor}
        {unidade && <span className="text-sm text-muted-foreground ml-1.5 font-normal">{unidade}</span>}
      </div>
      {typeof pct === "number" && (
        <div className="mt-2.5 h-[3px] w-full rounded-full bg-surface/80 overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${Math.min(100, Math.max(0, pct))}%`, background: color, boxShadow: `0 0 8px ${color}` }}
          />
        </div>
      )}
      {sub && <div className="text-[11px] text-muted-foreground mt-2 font-mono tracking-tight">{sub}</div>}
    </div>
  );
}
