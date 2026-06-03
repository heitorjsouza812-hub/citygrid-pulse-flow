import { SUBESTACOES_MOCK, type Subestacao } from "@/lib/mock-data";
import { Building2 } from "lucide-react";
import { cargaColor } from "@/lib/risco";

const statusColor: Record<Subestacao["status"], string> = {
  ok: "var(--risk-low)",
  alerta: "var(--risk-med)",
  manutencao: "var(--primary)",
  falha: "var(--risk-crit)",
};
const statusLabel: Record<Subestacao["status"], string> = {
  ok: "OK",
  alerta: "ALERTA",
  manutencao: "MANUT.",
  falha: "FALHA",
};

export function SubestacoesPanel() {
  return (
    <div className="card-surface">
      <PanelHeader title="Subestações" count={SUBESTACOES_MOCK.length} />
      <div className="overflow-x-auto">
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground border-b border-border bg-surface/30">
              <Th>ID</Th><Th>Nome</Th><Th>kV</Th><Th>Carga</Th><Th>Temp</Th><Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {SUBESTACOES_MOCK.map((s) => {
              const c = cargaColor(s.carga_pct);
              return (
                <tr key={s.id} className="border-b border-border/40 hover:bg-surface/40">
                  <Td className="text-foreground">{s.id}</Td>
                  <Td>{s.nome}</Td>
                  <Td className="tabular-nums">{s.tensao_kv}</Td>
                  <Td className="tabular-nums">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-12 bg-surface rounded-sm overflow-hidden border border-border">
                        <div className="h-full" style={{ width: `${s.carga_pct}%`, backgroundColor: c }} />
                      </div>
                      <span style={{ color: c }}>{s.carga_pct.toFixed(0)}%</span>
                    </div>
                  </Td>
                  <Td className="tabular-nums">{s.temp_c}°C</Td>
                  <Td>
                    <span
                      className="px-1.5 py-0.5 rounded-sm text-[9px] font-semibold tracking-wider"
                      style={{
                        color: statusColor[s.status],
                        backgroundColor: `color-mix(in oklab, ${statusColor[s.status]} 12%, transparent)`,
                        border: `1px solid color-mix(in oklab, ${statusColor[s.status]} 35%, transparent)`,
                      }}
                    >
                      {statusLabel[s.status]}
                    </span>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PanelHeader({ title, count }: { title: string; count: number }) {
  return (
    <div className="flex items-center justify-between px-4 h-10 border-b border-border">
      <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-2">
        <Building2 className="h-3.5 w-3.5" /> {title}
      </h3>
      <span className="text-[10px] font-mono text-muted-foreground tabular-nums">{count} ativos</span>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="text-left py-2 px-3 font-normal">{children}</th>;
}
function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`py-1.5 px-3 text-muted-foreground ${className}`}>{children}</td>;
}
