import { SHIFT_MOCK } from "@/lib/mock-data";
import { UserCheck, Phone, ShieldAlert } from "lucide-react";

export function PlantaoPanel() {
  const s = SHIFT_MOCK;
  return (
    <div className="card-surface">
      <div className="flex items-center justify-between px-4 h-10 border-b border-border">
        <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-2">
          <UserCheck className="h-3.5 w-3.5" /> Plantão & SLA
        </h3>
        <span className="text-[10px] font-mono text-muted-foreground">{s.centro.split(" — ")[0]}</span>
      </div>
      <div className="p-4 space-y-3 text-[11px]">
        <Row k="Operador" v={s.operador} sub={s.matricula} />
        <Row k="Supervisor" v={s.supervisor} />
        <Row k="Turno" v={`${s.turno} · ${s.inicio} – ${s.fim}`} />
        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border">
          <Kpi label="MTTR" val="14m" />
          <Kpi label="MTBF" val="48h" />
          <Kpi label="SAIDI" val="2.1 h" tone="warn" />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Kpi label="DEC" val="6.8" />
          <Kpi label="FEC" val="4.2" />
        </div>
        <div className="rounded-sm border border-border bg-surface/40 p-2.5 flex items-center gap-2 text-[10px] font-mono">
          <ShieldAlert className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">Despacho de emergência:</span>
          <Phone className="h-3 w-3 text-foreground" />
          <span className="text-foreground tabular-nums">0800 727 1234</span>
        </div>
      </div>
    </div>
  );
}

function Row({ k, v, sub }: { k: string; v: string; sub?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-mono">{k}</span>
      <span className="text-foreground">
        {v}{sub && <span className="text-muted-foreground font-mono ml-1.5">· {sub}</span>}
      </span>
    </div>
  );
}
function Kpi({ label, val, tone }: { label: string; val: string; tone?: "warn" | "crit" }) {
  const color = tone === "crit" ? "var(--risk-crit)" : tone === "warn" ? "var(--risk-med)" : "var(--foreground)";
  return (
    <div className="rounded-sm border border-border bg-surface/40 p-2 text-center">
      <div className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground font-mono">{label}</div>
      <div className="font-mono text-sm font-semibold tabular-nums" style={{ color }}>{val}</div>
    </div>
  );
}
