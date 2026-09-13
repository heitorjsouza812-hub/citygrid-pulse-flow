import { Beaker, Brain, Cpu, Dna, Zap } from "lucide-react";

import type { Recomendacao } from "@/lib/citygrid-types";
import { FONTES_RECOMENDACAO, contarAtividadePorFonte } from "@/lib/recommendation-activity";

const APRESENTACAO = {
  heuristica: { icon: Zap, color: "var(--cyan-elec)" },
  xgboost: { icon: Cpu, color: "var(--risk-med)" },
  lstm: { icon: Brain, color: "var(--purple-elec)" },
  genetico: { icon: Dna, color: "var(--risk-low)" },
  mistral3b: { icon: Beaker, color: "var(--primary)" },
} as const;

export function FontesRecomendacao({
  recomendacoes,
  ciclo,
}: {
  recomendacoes: Recomendacao[];
  ciclo: number;
}) {
  const contagens = contarAtividadePorFonte(recomendacoes, ciclo);

  return (
    <section className="space-y-3" role="region" aria-label="Atividade por fonte">
      <div>
        <h2 className="font-display font-bold text-sm">Heurística + 4 fontes analíticas</h2>
        <p className="text-xs text-muted-foreground max-w-4xl">
          Cada ciclo alimenta uma observação sintética em todos os painéis. Os números crescem com
          os ciclos desta sessão; eles não são métricas de produção, desempenho ou acurácia.
        </p>
      </div>
      <ul className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {FONTES_RECOMENDACAO.map((fonte) => {
          const { icon: Icon, color } = APRESENTACAO[fonte.id];
          return (
            <li className="card-surface p-4" key={fonte.id}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-display font-bold">
                  {fonte.label}
                </span>
                <Icon className="h-4 w-4" style={{ color }} aria-hidden="true" />
              </div>
              <div className="font-mono text-3xl font-bold" style={{ color }}>
                {contagens[fonte.id]}
              </div>
              <div className="text-[11px] text-muted-foreground mt-1">
                {fonte.experimental
                  ? "POC experimental · observação sem inferência ao vivo"
                  : "observações sintéticas acumuladas"}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
