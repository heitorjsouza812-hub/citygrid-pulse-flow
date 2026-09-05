import { useEffect, useState } from "react";
import type { SalaPlateia } from "@/lib/audience-types";

function readable(value?: string) {
  if (!value) return "—";
  const label = value.replace(/^zona_/, "").replaceAll("_", " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function CronometroVotacao({ endsAt }: { endsAt: string | null }) {
  const [, repaint] = useState(0);
  useEffect(() => {
    const id = setInterval(() => repaint((v) => v + 1), 250);
    return () => clearInterval(id);
  }, []);
  if (!endsAt) return <span className="audience-timer">SEM LIMITE</span>;
  const seconds = Math.max(0, Math.ceil((new Date(endsAt).getTime() - Date.now()) / 1000));
  return (
    <span className="audience-timer" aria-label={`${seconds} segundos restantes`}>
      {seconds}s
    </span>
  );
}

export function ComparacaoPlateiaIA({ sala }: { sala: SalaPlateia }) {
  const r = sala.recomendacao;
  if (!r) return null;
  return (
    <section className="audience-comparison">
      <p>RESULTADO DA RODADA</p>
      <h2>Vocês escolheram: {readable(sala.vencedores.acao)}</h2>
      <div className="audience-choice-row">
        <span>
          <b>Plateia</b>
          {readable(sala.vencedores.zona)} · {readable(sala.vencedores.acao)}
        </span>
        <span>
          <b>CityGrid</b>
          {readable(r.zona)} · {readable(r.acao)}
        </span>
      </div>
      <b className={r.semelhante ? "ok" : "warn"}>{r.classificacao}</b>
      <small>O sistema é uma referência para a conversa, não um comando.</small>
    </section>
  );
}

export function ConsequenciaRodada({ sala }: { sala: SalaPlateia }) {
  const c = sala.consequencia;
  if (!c) return null;
  const metrics = [
    { key: "estabilidade", label: "Estabilidade", symbol: "↯" },
    { key: "reserva", label: "Reserva", symbol: "◒" },
    { key: "controle_custos", label: "Custos", symbol: "$" },
    { key: "satisfacao", label: "Satisfação", symbol: "♥" },
  ] as const;
  return (
    <section className="audience-consequence">
      <div className="audience-impact-head">
        <div>
          <p>IMPACTO DA ESCOLHA</p>
          <h2>O que muda na cidade</h2>
        </div>
        <span className="audience-impact-action">AÇÃO APLICADA</span>
      </div>
      <strong className="audience-impact-summary">{c.resumo}</strong>
      <div className="audience-impact-zone">
        <div className="audience-impact-zone-label">
          <span>ÁREA PROTEGIDA</span>
          <strong>● {readable(c.zona_priorizada)}</strong>
        </div>
        <div className="audience-city-nodes" aria-label="Zonas afetadas pelo cenário">
          {c.zonas_afetadas.map((zone) => (
            <span className={zone === c.zona_priorizada ? "priority" : ""} key={zone}>
              <i aria-hidden="true" />
              {readable(zone)}
            </span>
          ))}
        </div>
      </div>
      <div className="audience-impact-board">
        <div className="audience-impact-board-title">
          <span>PLACAR PREVISTO</span>
          <small>ANTES → DEPOIS</small>
        </div>
        <div className="audience-impact-metrics">
          {metrics.map((metric) => {
            const change = c.deltas[metric.key] ?? 0;
            const after = sala.placar[metric.key];
            const before = sala.placar_antes?.[metric.key] ?? after - change;
            return (
              <div className={change >= 0 ? "gain" : "cost"} key={metric.key}>
                <span className="audience-impact-symbol" aria-hidden="true">
                  {metric.symbol}
                </span>
                <span className="audience-impact-metric-name">{metric.label}</span>
                <strong>
                  <small>ANTES</small>
                  {before.toFixed(0)}
                </strong>
                <b aria-hidden="true">→</b>
                <strong>
                  <small>DEPOIS</small>
                  {after.toFixed(0)}
                </strong>
                <em>
                  {change > 0 ? "+" : ""}
                  {change}
                </em>
              </div>
            );
          })}
        </div>
      </div>
      <small>Simulação educativa: nada é executado em uma rede real.</small>
    </section>
  );
}

export function ResumoFinal({ sala }: { sala: SalaPlateia }) {
  const r = sala.resumo_final;
  if (!r) return null;
  return (
    <section className="audience-final">
      <p>JOGO CONCLUÍDO</p>
      <h1>{r.pontuacao_final.toFixed(0)}%</h1>
      <strong>
        Vocês enfrentaram {r.rodadas} missões e deram {r.total_votos} respostas para a cidade.
      </strong>
      <div>
        <span>{r.participantes} jogadores</span>
        <span>melhor rodada: {r.melhor_rodada}</span>
        <span>desafio maior: {r.rodada_mais_arriscada}</span>
      </div>
    </section>
  );
}
