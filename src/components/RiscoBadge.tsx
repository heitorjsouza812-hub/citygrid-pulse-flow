import { riscoColor } from "@/lib/risco";
import type { EstadoPrevisao } from "@/lib/citygrid-types";

export function RiscoBadge({ risco, label }: { risco: EstadoPrevisao; label?: string }) {
  const isCrit = risco === "CRÍTICO";
  const color = riscoColor(risco);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${isCrit ? "animate-pulse-crit" : ""}`}
      style={{
        color,
        backgroundColor: `color-mix(in oklab, ${color} 14%, transparent)`,
        border: `1px solid color-mix(in oklab, ${color} 40%, transparent)`,
      }}
    >
      {label && <span className="opacity-60">{label}:</span>}
      {risco}
    </span>
  );
}
