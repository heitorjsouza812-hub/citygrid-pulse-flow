type Estado = "verde" | "amarelo" | "vermelho";

const colorMap: Record<Estado, string> = {
  verde: "var(--risk-low)",
  amarelo: "var(--risk-med)",
  vermelho: "var(--risk-crit)",
};

export function SemaforoANEEL({ estado, label, valor, unidade }: { estado: Estado; label: string; valor: string | number; unidade?: string }) {
  const color = colorMap[estado];
  return (
    <div className="card-surface p-3 flex items-center gap-3">
      <div
        className="h-3 w-3 rounded-full shrink-0"
        style={{ backgroundColor: color, boxShadow: `0 0 12px ${color}` }}
      />
      <div className="min-w-0 flex-1">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-display font-bold">{label}</div>
        <div className="font-mono text-base font-bold" style={{ color }}>
          {valor}
          {unidade && <span className="text-xs text-muted-foreground ml-1">{unidade}</span>}
        </div>
      </div>
    </div>
  );
}
