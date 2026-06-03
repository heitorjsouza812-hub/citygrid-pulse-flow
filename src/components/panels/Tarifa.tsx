import { TARIFA_MOCK } from "@/lib/mock-data";
import { CircleDollarSign } from "lucide-react";

const tipoColor: Record<string, string> = {
  "fora-ponta": "var(--risk-low)",
  intermediario: "var(--risk-med)",
  ponta: "var(--risk-crit)",
};

export function TarifaPanel() {
  const ativo = TARIFA_MOCK.find((t) => t.ativo);
  return (
    <div className="card-surface">
      <div className="flex items-center justify-between px-4 h-10 border-b border-border">
        <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-2">
          <CircleDollarSign className="h-3.5 w-3.5" /> Tarifa Horosazonal · CCEE
        </h3>
        <span className="text-[10px] font-mono text-muted-foreground">R$/MWh</span>
      </div>
      <div className="p-4">
        {ativo && (
          <div className="rounded-sm border border-border bg-surface/40 p-3 mb-3 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-mono">Janela atual</div>
              <div className="text-sm font-display font-semibold text-foreground">{ativo.nome}</div>
              <div className="text-[10px] font-mono text-muted-foreground">{ativo.inicio} – {ativo.fim}</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-mono">PLD horário</div>
              <div className="font-mono text-lg font-semibold tabular-nums" style={{ color: tipoColor[ativo.tipo] }}>
                R$ {ativo.preco_rs_mwh.toFixed(2)}
              </div>
            </div>
          </div>
        )}
        <div className="space-y-1.5">
          {TARIFA_MOCK.map((t, i) => (
            <div
              key={i}
              className={`flex items-center justify-between text-[11px] font-mono px-2 py-1.5 rounded-sm border ${
                t.ativo ? "border-primary/40 bg-surface/40" : "border-border"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: tipoColor[t.tipo] }} />
                <span className="text-muted-foreground tabular-nums">{t.inicio}–{t.fim}</span>
                <span className="text-foreground">{t.nome}</span>
              </div>
              <span className="text-foreground tabular-nums">R$ {t.preco_rs_mwh.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
