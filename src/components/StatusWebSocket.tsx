export type WSStatus = "conectado" | "conectando" | "offline";

export function StatusWebSocket({ status }: { status: WSStatus }) {
  const map = {
    conectado: { color: "var(--risk-low)", label: "AO VIVO", pulse: true },
    conectando: { color: "var(--risk-med)", label: "CONECTANDO", pulse: true },
    offline: { color: "var(--risk-crit)", label: "OFFLINE", pulse: false },
  } as const;
  const cfg = map[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-mono font-bold uppercase tracking-wider"
      style={{
        color: cfg.color,
        backgroundColor: `color-mix(in oklab, ${cfg.color} 12%, transparent)`,
        border: `1px solid color-mix(in oklab, ${cfg.color} 40%, transparent)`,
      }}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${cfg.pulse ? "animate-pulse-dot" : ""}`}
        style={{ backgroundColor: cfg.color, boxShadow: `0 0 8px ${cfg.color}` }}
      />
      {cfg.label}
    </span>
  );
}
