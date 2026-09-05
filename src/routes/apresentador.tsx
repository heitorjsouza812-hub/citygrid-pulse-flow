import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { QRCodeSala } from "@/components/audiencia/QRCodeSala";
import { PainelVotacao } from "@/components/audiencia/PainelVotacao";
import {
  ComparacaoPlateiaIA,
  ConsequenciaRodada,
  CronometroVotacao,
  ResumoFinal,
} from "@/components/audiencia/ResultadoSala";
import { PlacarCidade } from "@/components/audiencia/PlacarCidade";
import { audienceApi } from "@/lib/audience-api";
import type { TipoEventoPlateia } from "@/lib/audience-types";
import { useSala } from "@/lib/use-sala";

export const Route = createFileRoute("/apresentador")({ component: Apresentador });
const events: Array<[TipoEventoPlateia, string]> = [
  ["tempestade", "Tempestade severa"],
  ["incendio", "Incêndio urbano"],
  ["pico_consumo", "Pico de consumo"],
];
function Apresentador() {
  const [code, setCode] = useState(() =>
    typeof window === "undefined" ? "" : sessionStorage.getItem("citygrid-presenter-code") || "",
  );
  const [token, setToken] = useState(() =>
    typeof window === "undefined" ? "" : sessionStorage.getItem("citygrid-presenter-token") || "",
  );
  const [live, setLive] = useState(false);
  const [duration, setDuration] = useState<number | null>(20);
  const [nextEvent, setNextEvent] = useState<TipoEventoPlateia>("tempestade");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [entryUrl, setEntryUrl] = useState(() =>
    typeof window === "undefined"
      ? ""
      : sessionStorage.getItem("citygrid-presenter-entry-url") || "",
  );
  const { sala, erro, status, refresh } = useSala(code || "CG-INVALID");
  useEffect(() => {
    if (code || typeof window === "undefined") return;
    const savedCode = sessionStorage.getItem("citygrid-presenter-code");
    const savedToken = sessionStorage.getItem("citygrid-presenter-token");
    if (!savedCode || !savedToken) return;
    setCode(savedCode);
    setToken(savedToken);
    setEntryUrl(sessionStorage.getItem("citygrid-presenter-entry-url") || "");
  }, [code]);
  async function create() {
    setBusy(true);
    try {
      const created = await audienceApi.create(live, duration);
      sessionStorage.setItem("citygrid-presenter-code", created.codigo);
      sessionStorage.setItem("citygrid-presenter-token", created.presenter_token);
      sessionStorage.setItem("citygrid-presenter-entry-url", created.participation_url);
      setCode(created.codigo);
      setToken(created.presenter_token);
      setEntryUrl(created.participation_url);
    } finally {
      setBusy(false);
    }
  }
  function resetPresenterRoom() {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("citygrid-presenter-code");
      sessionStorage.removeItem("citygrid-presenter-token");
      sessionStorage.removeItem("citygrid-presenter-entry-url");
    }
    setCode("");
    setToken("");
    setEntryUrl("");
  }
  async function finishAndCreateNew() {
    setBusy(true);
    setActionError(null);
    try {
      await audienceApi.delete(code, token);
      resetPresenterRoom();
      const created = await audienceApi.create(live, duration);
      sessionStorage.setItem("citygrid-presenter-code", created.codigo);
      sessionStorage.setItem("citygrid-presenter-token", created.presenter_token);
      sessionStorage.setItem("citygrid-presenter-entry-url", created.participation_url);
      setCode(created.codigo);
      setToken(created.presenter_token);
      setEntryUrl(created.participation_url);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Não foi possível criar uma nova sala",
      );
    } finally {
      setBusy(false);
    }
  }
  async function action(run: () => Promise<unknown>) {
    setBusy(true);
    setActionError(null);
    try {
      await run();
      await refresh();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Não foi possível atualizar a sala");
    } finally {
      setBusy(false);
    }
  }
  if (!code || !token)
    return (
      <main className="audience-presenter">
        <section className="audience-create">
          <p className="audience-kicker">CITYGRID BRAIN · CENTRAL DE DECISÃO DA PLATEIA</p>
          <h1>Transforme a demonstração em uma decisão coletiva.</h1>
          <p>
            O apresentador controla as rodadas; a plateia participa pelo celular, sem acesso ao
            simulador.
          </p>
          <label>
            <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} />{" "}
            Resultado ao vivo (padrão: oculto)
          </label>
          <label>
            Duração
            <select
              value={duration ?? ""}
              onChange={(e) => setDuration(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="10">10 segundos</option>
              <option value="15">15 segundos</option>
              <option value="20">20 segundos</option>
              <option value="30">30 segundos</option>
              <option value="">Sem limite automático</option>
            </select>
          </label>
          <button className="audience-primary" disabled={busy} onClick={() => void create()}>
            {busy ? "CRIANDO..." : "CRIAR NOVA SALA"}
          </button>
        </section>
      </main>
    );
  if (!sala)
    return (
      <main className="audience-presenter">
        <section className="audience-create">
          <p>
            Conectando à sala {code}… {erro}
          </p>
          {erro && (
            <button className="audience-primary" onClick={resetPresenterRoom}>
              Criar outra sala
            </button>
          )}
        </section>
      </main>
    );
  const phaseAction =
    sala.fase === "EVENTO"
      ? "VOTACAO_ZONA"
      : sala.fase === "VOTACAO_ZONA" &&
          sala.votacao_bloqueada &&
          !sala.empate.opcoes.length &&
          Boolean(sala.vencedores.zona)
        ? "VOTACAO_ACAO"
        : null;
  const total =
    Object.values(sala.contagens.zona).reduce((a, b) => a + b, 0) +
    Object.values(sala.contagens.acao).reduce((a, b) => a + b, 0);
  const participationUrl =
    entryUrl ||
    (typeof window === "undefined"
      ? `/participar/${sala.codigo}`
      : `${window.location.origin}/participar/${sala.codigo}`);
  return (
    <main className="audience-presenter">
      <header className="audience-presenter-head">
        <div>
          <p className="audience-kicker">CENTRAL DE DECISÃO DA PLATEIA · {status}</p>
          <h1>
            Sala {sala.codigo} <small>Rodada {sala.rodada}/3</small>
          </h1>
        </div>
        <div>
          <b>{sala.conectados}</b> conectados · {sala.participantes} participantes
          <button
            className="audience-primary"
            disabled={busy}
            onClick={() => void finishAndCreateNew()}
          >
            {busy ? "ENCERRANDO..." : "TERMINAR SALA E ABRIR NOVA"}
          </button>
          <button onClick={() => void document.documentElement.requestFullscreen?.()}>
            Tela cheia
          </button>
        </div>
      </header>
      <section className="audience-presenter-grid">
        <div className="audience-stage">
          {sala.fase === "LOBBY" && (
            <QRCodeSala
              code={sala.codigo}
              url={participationUrl}
              onCopy={() => void navigator.clipboard.writeText(participationUrl)}
            />
          )}
          {sala.fase === "EVENTO" && (
            <section className="audience-event">
              <p>RODADA {sala.rodada}</p>
              <h2>{sala.evento?.nome}</h2>
              <strong>{sala.evento?.descricao}</strong>
              <small>
                Dados integralmente sintéticos · nenhuma ação será enviada a uma rede real.
              </small>
            </section>
          )}
          {(sala.fase === "VOTACAO_ZONA" || sala.fase === "VOTACAO_ACAO") && (
            <>
              <div className="audience-time">
                <span>{sala.resultado_ao_vivo ? "RESULTADO AO VIVO" : "RESULTADO OCULTO"}</span>
                <CronometroVotacao endsAt={sala.votacao_termina_em} />
              </div>
              <PainelVotacao
                question={
                  sala.fase === "VOTACAO_ZONA"
                    ? "Qual zona deve ser priorizada?"
                    : "Qual ação deve ser tomada?"
                }
                options={sala.fase === "VOTACAO_ZONA" ? sala.opcoes_zona : sala.opcoes_acao}
                onVote={() => undefined}
                disabled
                counts={sala.fase === "VOTACAO_ZONA" ? sala.contagens.zona : sala.contagens.acao}
                visible={sala.resultado_ao_vivo || sala.votacao_bloqueada}
              />
            </>
          )}
          {sala.fase === "RESULTADO" && <ComparacaoPlateiaIA sala={sala} />}
          {sala.fase === "CONSEQUENCIA" && (
            <>
              <ConsequenciaRodada sala={sala} />
              <ComparacaoPlateiaIA sala={sala} />
            </>
          )}
          {sala.fase === "ENCERRADA" && <ResumoFinal sala={sala} />}
        </div>
        <aside>
          <PlacarCidade placar={sala.placar} />
          <section className="audience-control">
            <p>CONTROLE DO APRESENTADOR</p>
            <b>{total} votos registrados</b>
            {actionError && <p className="audience-error">{actionError}</p>}
            {sala.fase === "VOTACAO_ZONA" &&
              sala.votacao_bloqueada &&
              !sala.vencedores.zona &&
              !sala.empate.opcoes.length && (
                <p className="audience-muted">
                  Nenhuma pessoa votou nesta etapa. Reinicie a rodada ou convide a plateia a
                  participar.
                </p>
              )}
            {sala.empate.opcoes.length > 0 && (
              <div>
                <strong>Empate: escolha uma opção</strong>
                {sala.empate.opcoes.map((option) => (
                  <button
                    key={option}
                    disabled={busy}
                    onClick={() => void action(() => audienceApi.tie(code, token, option))}
                  >
                    {option.replace("zona_", "")}
                  </button>
                ))}
              </div>
            )}
            {sala.fase === "LOBBY" && (
              <div className="audience-start-game">
                <strong>INICIAR JOGO · escolha o primeiro evento</strong>
                <p className="audience-muted">
                  A plateia já entrou. Selecione um cenário para abrir a primeira rodada.
                </p>
                {events.map(([id, label]) => (
                  <button
                    key={id}
                    disabled={busy}
                    onClick={() =>
                      void action(() => audienceApi.start(code, token, id, duration, live))
                    }
                  >
                    Iniciar: {label}
                  </button>
                ))}
              </div>
            )}
            {phaseAction && (
              <button
                className="audience-primary"
                disabled={busy || !!sala.empate.opcoes.length}
                onClick={() => void action(() => audienceApi.phase(code, token, phaseAction))}
              >
                {phaseAction === "VOTACAO_ZONA" ? "Abrir votação de zona" : "Abrir votação de ação"}
              </button>
            )}
            {(sala.fase === "VOTACAO_ZONA" || sala.fase === "VOTACAO_ACAO") &&
              !sala.votacao_bloqueada && (
                <button
                  className="audience-primary"
                  disabled={busy}
                  onClick={() => void action(() => audienceApi.close(code, token))}
                >
                  Encerrar votação
                </button>
              )}
            {sala.fase === "VOTACAO_ACAO" &&
              sala.votacao_bloqueada &&
              !sala.empate.opcoes.length && (
                <button
                  className="audience-primary"
                  disabled={busy}
                  onClick={() => void action(() => audienceApi.reveal(code, token))}
                >
                  Revelar Plateia × IA
                </button>
              )}
            {sala.fase === "RESULTADO" && (
              <button
                className="audience-primary"
                disabled={busy}
                onClick={() => void action(() => audienceApi.apply(code, token))}
              >
                Aplicar consequência projetada
              </button>
            )}
            {sala.fase === "CONSEQUENCIA" &&
              (sala.rodada >= 3 ? (
                <button
                  className="audience-primary"
                  disabled={busy}
                  onClick={() => void action(() => audienceApi.end(code, token))}
                >
                  Encerrar apresentação
                </button>
              ) : (
                <>
                  <select
                    aria-label="Evento da próxima rodada"
                    value={nextEvent}
                    onChange={(event) => setNextEvent(event.target.value as TipoEventoPlateia)}
                  >
                    {events.map(([id, label]) => (
                      <option key={id} value={id}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <button
                    className="audience-primary"
                    disabled={busy}
                    onClick={() =>
                      void action(() => audienceApi.start(code, token, nextEvent, duration, live))
                    }
                  >
                    Próxima rodada
                  </button>
                </>
              ))}
          </section>
        </aside>
      </section>
    </main>
  );
}
