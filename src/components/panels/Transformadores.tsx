import { TRANSFORMADORES_MOCK } from "@/lib/mock-data";
import { Server } from "lucide-react";
import { cargaColor } from "@/lib/risco";

function saudeColor(s: number) {
  if (s >= 90) return "var(--risk-low)";
  if (s >= 75) return "var(--risk-med)";
  if (s >= 60) return "var(--risk-high)";
  return "var(--risk-crit)";
}

export function TransformadoresPanel() {
  return (
    <div className="card-surface">
      <div className="flex items-center justify-between px-4 h-10 border-b border-border">
        <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-2">
          <Server className="h-3.5 w-3.5" /> Transformadores Críticos
        </h3>
        <span className="text-[10px] font-mono text-muted-foreground tabular-nums">
          {TRANSFORMADORES_MOCK.length} monitorados
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground border-b border-border bg-surface/30">
              <th className="text-left py-2 px-3 font-normal">TAG</th>
              <th className="text-left py-2 px-3 font-normal">SE</th>
              <th className="text-left py-2 px-3 font-normal">MVA</th>
              <th className="text-left py-2 px-3 font-normal">Carga</th>
              <th className="text-left py-2 px-3 font-normal">Óleo</th>
              <th className="text-left py-2 px-3 font-normal">Enrol.</th>
              <th className="text-left py-2 px-3 font-normal">Saúde</th>
            </tr>
          </thead>
          <tbody>
            {TRANSFORMADORES_MOCK.map((t) => {
              const c = cargaColor(t.carga_pct);
              const sc = saudeColor(t.saude);
              return (
                <tr key={t.id} className="border-b border-border/40 hover:bg-surface/40">
                  <td className="py-1.5 px-3 text-foreground">{t.id}</td>
                  <td className="py-1.5 px-3 text-muted-foreground">{t.se}</td>
                  <td className="py-1.5 px-3 text-muted-foreground tabular-nums">{t.potencia_mva}</td>
                  <td className="py-1.5 px-3 tabular-nums" style={{ color: c }}>{t.carga_pct.toFixed(1)}%</td>
                  <td className="py-1.5 px-3 text-muted-foreground tabular-nums">{t.oleo_c}°C</td>
                  <td className="py-1.5 px-3 text-muted-foreground tabular-nums">{t.enrol_c}°C</td>
                  <td className="py-1.5 px-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-14 bg-surface rounded-sm overflow-hidden border border-border">
                        <div className="h-full" style={{ width: `${t.saude}%`, backgroundColor: sc }} />
                      </div>
                      <span className="tabular-nums" style={{ color: sc }}>{t.saude}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
