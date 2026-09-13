import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { PainelVotacao } from "@/components/audiencia/PainelVotacao";
import {
  ComparacaoPlateiaIA,
  ConsequenciaRodada,
  CronometroVotacao,
  ResumoFinal,
} from "@/components/audiencia/ResultadoSala";
import { PlacarCidade } from "@/components/audiencia/PlacarCidade";
import { ProgressoJogo } from "@/components/audiencia/ProgressoJogo";
import { audienceApi } from "@/lib/audience-api";
import { participantIdFor, useSala } from "@/lib/use-sala";

export const Route = createFileRoute("/participar/$codigo")({ component: Participar });
function Participar() {
  const { codigo } = Route.useParams();
  const code = codigo.toUpperCase();
  const [nickname, setNickname] = useState("");
  const [participant, setParticipant] = useState(() =>
    typeof window !== "undefined" ? localStorage.getItem(`citygrid-audience-${code}`) : null,
  );
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const { sala, erro, status, refresh } = useSala(code, participant ?? undefined);
  async function enter() {
    setSending(true);
    try {
      const id = participantIdFor(code);
      await audienceApi.join(code, id, nickname);
      setParticipant(id);
      await refresh();
    } catch {
      await refresh();
    } finally {
      setSending(false);
    }
  }
  async function vote(etapa: "zona" | "acao", option: string) {
    if (!participant || sending) return;
    setSending(true);
    try {
      await audienceApi.vote(code, participant, etapa, option);
      setSelected((current) => ({ ...current, [etapa]: option }));
      await refresh();
    } finally {
      setSending(false);
    }
  }
  if (erro && !sala)
    return (
      <main className="audience-mobile">
        <h1>Sala indisponível</h1>
        <p>{erro}</p>
        <button onClick={() => void refresh()}>Tentar novamente</button>
      </main>
    );
  if (!participant)
    return (
      <main className="audience-mobile">
        <p className="audience-kicker">CITYGRID BRAIN · ENTRE NO JOGO</p>
        <h1>Sua decisão muda a cidade.</h1>
        <p>
          Você entrou na sala <b>{code}</b>. Escolha um apelido e prepare-se para votar.
        </p>
        <label>
          Seu apelido <small>(opcional)</small>
          <input
            value={nickname}
            maxLength={28}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="Como quer aparecer?"
          />
        </label>
        <button className="audience-primary" disabled={sending} onClick={() => void enter()}>
          {sending ? "ENTRANDO..." : "ENTRAR E JOGAR"}
        </button>
        <small>
          Dados sintéticos. Esta é uma simulação educacional, não uma rede elétrica real.
        </small>
      </main>
    );
  if (!sala) return <main className="audience-mobile">Conectando à sala…</main>;
  const stage =
    sala.fase === "VOTACAO_ZONA" ? "zona" : sala.fase === "VOTACAO_ACAO" ? "acao" : null;
  return (
    <main className="audience-mobile">
      <header>
        <p className="audience-kicker">
          SALA {sala.codigo} · RODADA {sala.rodada || "—"}
        </p>
        <span className={`audience-connection ${status}`}>{status}</span>
      </header>
      <PlacarCidade placar={sala.placar} compacto />
      <ProgressoJogo progressao={sala.progressao} />
      {sala.fase === "LOBBY" && (
        <section className="audience-wait audience-ready">
          <span className="audience-ready-orb" aria-hidden="true">
            ✓
          </span>
          <p className="audience-kicker">VOCÊ ESTÁ NO JOGO</p>
          <h1>Tudo pronto, {nickname || "jogador"}!</h1>
          <p>Olhe para o telão. Quando a missão aparecer, você escolhe em dois toques.</p>
          <div className="audience-how-to">
            <span>1 · escolha a área</span>
            <span>2 · escolha a ação</span>
          </div>
        </section>
      )}
      {sala.fase === "EVENTO" && (
        <section className="audience-wait audience-alert">
          <p className="audience-kicker">⚠ NOVA MISSÃO</p>
          <h1>{sala.evento?.nome}</h1>
          <p>{sala.evento?.descricao}</p>
          <strong>Prepare-se: a votação abre a qualquer momento.</strong>
        </section>
      )}
      {stage && (
        <>
          <div className="audience-time">
            <span>{sala.votacao_bloqueada ? "VOTAÇÃO ENCERRADA" : "VOTE AGORA"}</span>
            <CronometroVotacao endsAt={sala.votacao_termina_em} />
          </div>
          <PainelVotacao
            step={
              stage === "zona"
                ? "MISSÃO 1 DE 2 · ESCOLHA A ÁREA"
                : "MISSÃO 2 DE 2 · ESCOLHA O PLANO"
            }
            question={stage === "zona" ? "Onde agir primeiro?" : "Qual plano você escolhe?"}
            options={stage === "zona" ? sala.opcoes_zona : sala.opcoes_acao}
            selected={selected[stage]}
            disabled={sending || sala.votacao_bloqueada}
            onVote={(option) => void vote(stage, option)}
            counts={sala.contagens[stage]}
            visible={sala.resultado_ao_vivo || sala.votacao_bloqueada}
          />
          {selected[stage] && (
            <p className="audience-confirm" aria-live="polite">
              ✓ Escolha salva! Você pode trocar até a votação fechar.
            </p>
          )}
        </>
      )}
      {sala.fase === "RESULTADO" && <ComparacaoPlateiaIA sala={sala} />}
      {sala.fase === "CONSEQUENCIA" && (
        <>
          <ComparacaoPlateiaIA sala={sala} />
          <ConsequenciaRodada sala={sala} />
        </>
      )}
      {sala.fase === "ENCERRADA" && <ResumoFinal sala={sala} />}
      <footer>Resultado da simulação educacional · recomendações exigem avaliação humana.</footer>
    </main>
  );
}
