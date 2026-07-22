import type { ReactNode } from "react";

export function MetricaCard({
  icon,
  label,
  valor,
  unidade,
  sub,
  color,
  pct,
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
  const accent = color ?? "var(--foreground)";
  return (
    <div className="card-surface p-3.5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-mono">
          {label}
        </span>
        <span className="text-muted-foreground opacity-80">{icon}</span>
      </div>
      <div
        className="font-mono text-[24px] leading-none font-semibold tabular-nums tracking-tight"
        style={{ color: accent }}
      >
        {valor}
        {unidade && (
          <span className="text-sm text-muted-foreground ml-1.5 font-normal">{unidade}</span>
        )}
      </div>
      {typeof pct === "number" && (
        <div className="mt-2.5 h-1 w-full bg-surface overflow-hidden rounded-sm">
          <div
            className="h-full"
            style={{ width: `${Math.min(100, Math.max(0, pct))}%`, backgroundColor: accent }}
          />
        </div>
      )}
      {sub && <div className="text-[11px] text-muted-foreground mt-2 font-mono">{sub}</div>}
    </div>
  );
}
