import type { ReactNode } from "react";

export function MetricaCard({
  icon, label, valor, unidade, sub, color = "var(--cyan-elec)", gradient = false,
}: {
  icon: ReactNode;
  label: string;
  valor: string | number;
  unidade?: string;
  sub?: string;
  color?: string;
  gradient?: boolean;
}) {
  return (
    <div className="card-surface p-4 relative">
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{ background: gradient ? "var(--gradient-green)" : "var(--gradient-accent)" }}
      />
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-display font-bold">{label}</span>
        <span style={{ color }}>{icon}</span>
      </div>
      <div className="font-mono text-3xl font-bold leading-none transition-colors" style={{ color }}>
        {valor}
        {unidade && <span className="text-base text-muted-foreground ml-1.5">{unidade}</span>}
      </div>
      {sub && <div className="text-[11px] text-muted-foreground mt-1.5">{sub}</div>}
    </div>
  );
}
