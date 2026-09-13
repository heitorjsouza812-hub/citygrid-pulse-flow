import type { ProgressaoJogo as Progressao } from "@/lib/audience-types";

const PROGRESSO_INICIAL: Progressao = {
  pontos_total: 0,
  meta_pontos: 300,
  progresso_pct: 0,
  rodadas_concluidas: 0,
  total_rodadas: 3,
  bonus_alinhamento_total: 0,
  bonus_participacao_total: 0,
  feedback_rodada: null,
};

export function ProgressoJogo({ progressao = PROGRESSO_INICIAL }: { progressao?: Progressao }) {
  const feedback = progressao.feedback_rodada;

  return (
    <section className="audience-progression" aria-label="Progresso do jogo">
      <div className="audience-progression-head">
        <div>
          <span>JORNADA DA PLATEIA</span>
          <h2>Progresso coletivo</h2>
        </div>
        <strong>
          {progressao.pontos_total} / {progressao.meta_pontos} pontos
        </strong>
      </div>
      <progress
        max={100}
        value={progressao.progresso_pct}
        aria-label="Progresso até a meta coletiva"
        aria-valuenow={progressao.progresso_pct}
        aria-valuetext={`${progressao.progresso_pct}% da meta coletiva`}
      />
      <p>
        {progressao.rodadas_concluidas} de {progressao.total_rodadas} rodadas concluídas
      </p>
      <div className="audience-scoring-rules" aria-label="Como os pontos são calculados">
        <span>+{feedback?.pontos_base ?? 50} missão concluída</span>
        <span>+{feedback?.bonus_alinhamento ?? "até 25"} alinhamento completo</span>
        <span>+{feedback?.bonus_participacao ?? "até 25"} participação nas duas escolhas</span>
      </div>
      {feedback && (
        <div className="audience-round-feedback" aria-live="polite">
          <strong>
            Rodada {feedback.rodada}: +{feedback.pontos_rodada} pontos
          </strong>
          <span>{feedback.mensagem}</span>
          <small>
            {feedback.participantes_completos} de {feedback.participantes_elegiveis} participantes
            completaram as duas escolhas ({feedback.participacao_pct.toFixed(0)}%).
          </small>
        </div>
      )}
      <small>
        Pontos e bônus calculados pelo servidor. Projeção sintética educacional; não representa uma
        rede elétrica ao vivo.
      </small>
    </section>
  );
}
