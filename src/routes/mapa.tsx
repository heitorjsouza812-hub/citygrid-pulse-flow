import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  Activity,
  Bot,
  ChevronLeft,
  ChevronRight,
  CloudLightning,
  Flame,
  Gauge,
  Layers3,
  MapPin,
  RotateCcw,
  ShieldAlert,
  TimerReset,
  TriangleAlert,
  Zap,
} from "lucide-react";

import { RiscoBadge } from "@/components/RiscoBadge";
import { useCityGrid } from "@/lib/citygrid-context";
import type { CenarioManual, TipoCenario, Zona } from "@/lib/citygrid-types";

export const Route = createFileRoute("/mapa")({
  head: () => ({
    meta: [
      { title: "NOC / SCADA — CityGrid Pulse Flow" },
      {
        name: "description",
        content:
          "Mapa operacional interativo com telemetria sintética, cenários explícitos e histórico navegável.",
      },
    ],
  }),
  component: MapaOperacionalPage,
});

type ConfigEvento = {
  tipo: TipoCenario;
  titulo: string;
  subtitulo: string;
  Icone: typeof CloudLightning;
  tom: "cyan" | "orange" | "violet";
};

const EVENTOS: ConfigEvento[] = [
  {
    tipo: "tempestade",
    titulo: "Tempestade",
    subtitulo: "Geração distribuída e qualidade",
    Icone: CloudLightning,
    tom: "cyan",
  },
  {
    tipo: "incendio",
    titulo: "Incêndio",
    subtitulo: "Contingência urbana localizada",
    Icone: Flame,
    tom: "orange",
  },
  {
    tipo: "pico_consumo",
    titulo: "Pico de consumo",
    subtitulo: "Demanda máxima coordenada",
    Icone: Activity,
    tom: "violet",
  },
];

const LIGACOES: Array<[string, string]> = [
  ["zona_norte", "zona_centro"],
  ["zona_oeste", "zona_centro"],
  ["zona_centro", "zona_leste"],
  ["zona_centro", "zona_sul"],
  ["zona_hospitalar", "zona_centro"],
  ["zona_universitaria", "zona_leste"],
  ["zona_aeroporto", "zona_sul"],
  ["zona_norte", "zona_hospitalar"],
];

function MapaOperacionalPage() {
  const {
    zonas,
    snapshots,
    recomendacoes,
    cenarioManual,
    status,
    timestampSimulado,
    ativarCenario,
    limparCenario,
  } = useCityGrid();
  const [deslocamentoTimeline, setDeslocamentoTimeline] = useState(0);
  const [zonaSelecionada, setZonaSelecionada] = useState<string | null>(null);
  const [pendente, setPendente] = useState<TipoCenario | "limpar" | null>(null);
  const [erroCenario, setErroCenario] = useState<string | null>(null);

  const historico = useMemo(() => {
    if (snapshots.length) return snapshots;
    return zonas.length
      ? [
          {
            ciclo: zonas[0]?.ciclo ?? 0,
            timestamp: timestampSimulado,
            zonas,
            stats: { ciclo: zonas[0]?.ciclo ?? 0 },
            recomendacoes,
          },
        ]
      : [];
  }, [snapshots, zonas, timestampSimulado, recomendacoes]);

  useEffect(() => {
    setDeslocamentoTimeline(0);
  }, [snapshots.length]);

  const indiceTimeline = Math.max(0, historico.length - 1 - deslocamentoTimeline);
  const pontoTimeline = historico[indiceTimeline];
  const zonasBase = pontoTimeline?.zonas ?? zonas;
  const emHistorico = deslocamentoTimeline > 0;
  const zonasExibidas = useMemo(
    () => projetarCenario(zonasBase, emHistorico ? null : cenarioManual),
    [zonasBase, emHistorico, cenarioManual],
  );
  const zonaAtiva =
    zonasExibidas.find((zona) => zona.zona_id === zonaSelecionada) ?? zonasExibidas[0] ?? null;
  const recomendacoesAtivas = pontoTimeline?.recomendacoes ?? recomendacoes;

  async function executarCenario(tipo: TipoCenario) {
    setPendente(tipo);
    setErroCenario(null);
    try {
      await ativarCenario(tipo);
      setDeslocamentoTimeline(0);
    } catch (error) {
      setErroCenario(error instanceof Error ? error.message : "Não foi possível iniciar o cenário");
    } finally {
      setPendente(null);
    }
  }

  async function encerrarCenario() {
    setPendente("limpar");
    setErroCenario(null);
    try {
      await limparCenario();
    } catch (error) {
      setErroCenario(
        error instanceof Error ? error.message : "Não foi possível encerrar o cenário",
      );
    } finally {
      setPendente(null);
    }
  }

  return (
    <main className="noc-shell mx-auto max-w-[1700px] px-3 py-4 sm:px-5 lg:px-6">
      <section className="noc-commandbar">
        <div className="min-w-0">
          <div className="noc-eyebrow">
            <span className="noc-live-dot" /> CENTRAL DE OPERAÇÕES · NOC / SCADA
          </div>
          <h1 className="font-display text-2xl font-extrabold tracking-tight sm:text-3xl">
            Mapa Operacional da Rede
          </h1>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
            Telemetria sintética em ciclo de 5 min · selecione uma zona para inspecionar o sistema.
          </p>
        </div>
        <div className="noc-status-cluster">
          <div className="noc-status-box">
            <span className="text-muted-foreground">LINK</span>
            <strong
              className={
                status === "conectado" ? "text-[var(--risk-low)]" : "text-[var(--risk-high)]"
              }
            >
              {status === "conectado" ? "ONLINE" : status.toUpperCase()}
            </strong>
          </div>
          <div className="noc-status-box">
            <span className="text-muted-foreground">CICLO</span>
            <strong>#{pontoTimeline?.ciclo ?? "--"}</strong>
          </div>
          <div className="noc-status-box hidden sm:flex">
            <span className="text-muted-foreground">HORA SIM.</span>
            <strong>{formatarHora(pontoTimeline?.timestamp ?? timestampSimulado)}</strong>
          </div>
        </div>
      </section>

      <section className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-4">
          <CenarioControls
            ativo={cenarioManual}
            pendente={pendente}
            erro={erroCenario}
            emHistorico={emHistorico}
            onExecutar={executarCenario}
            onEncerrar={encerrarCenario}
          />

          {cenarioManual && !emHistorico && <ScenarioBanner cenario={cenarioManual} />}

          <section className="noc-map-frame" aria-label="Mapa interativo das zonas elétricas">
            <div className="noc-map-grid" />
            <div className="noc-map-topline">
              <span className="inline-flex items-center gap-2">
                <Layers3 className="h-3.5 w-3.5" /> MALHA 13,8 kV
              </span>
              <span>{emHistorico ? "REPRODUÇÃO HISTÓRICA" : "FLUXO AO VIVO"}</span>
            </div>
            {!zonasExibidas.length ? (
              <div className="flex h-[510px] items-center justify-center text-center text-sm text-muted-foreground">
                Aguardando telemetria do simulador para construir a malha.
              </div>
            ) : (
              <MapaInterativo
                zonas={zonasExibidas}
                zonaSelecionada={zonaAtiva?.zona_id ?? null}
                cenario={emHistorico ? null : cenarioManual}
                onSelecionar={setZonaSelecionada}
              />
            )}
            <div className="noc-map-legend">
              <LegendaCor risco="BAIXO" />
              <LegendaCor risco="MÉDIO" />
              <LegendaCor risco="ALTO" />
              <LegendaCor risco="CRÍTICO" />
              <span className="ml-auto hidden items-center gap-1.5 text-[10px] text-muted-foreground sm:flex">
                <Zap className="h-3 w-3 text-primary" /> traços = fluxo estimado de potência
              </span>
            </div>
          </section>

          <Timeline
            historico={historico}
            deslocamento={deslocamentoTimeline}
            onAlterar={setDeslocamentoTimeline}
          />
        </div>

        <aside className="space-y-4">
          <PainelZona zona={zonaAtiva} cenario={emHistorico ? null : cenarioManual} />
          <PainelIA
            zona={zonaAtiva}
            cenario={emHistorico ? null : cenarioManual}
            recomendacoes={recomendacoesAtivas}
          />
        </aside>
      </section>
    </main>
  );
}

function CenarioControls({
  ativo,
  pendente,
  erro,
  emHistorico,
  onExecutar,
  onEncerrar,
}: {
  ativo: CenarioManual | null;
  pendente: TipoCenario | "limpar" | null;
  erro: string | null;
  emHistorico: boolean;
  onExecutar: (tipo: TipoCenario) => Promise<void>;
  onEncerrar: () => Promise<void>;
}) {
  return (
    <section className="noc-panel overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border/70 px-4 py-3">
        <div>
          <div className="noc-eyebrow text-primary">
            <TriangleAlert className="h-3.5 w-3.5" /> SIMULADOR DE EVENTOS
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Projeções temporárias no mapa. Não escrevem telemetria, histórico ou modelos.
          </p>
        </div>
        {ativo && (
          <button
            type="button"
            className="noc-quiet-button"
            onClick={() => void onEncerrar()}
            disabled={pendente !== null}
          >
            <RotateCcw className="h-3.5 w-3.5" />{" "}
            {pendente === "limpar" ? "ENCERRANDO" : "ENCERRAR"}
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 gap-px bg-border/60 sm:grid-cols-3">
        {EVENTOS.map(({ tipo, titulo, subtitulo, Icone, tom }) => (
          <button
            key={tipo}
            type="button"
            className={`noc-event-button noc-event-${tom} ${ativo?.tipo === tipo ? "is-active" : ""}`}
            disabled={pendente !== null || emHistorico}
            onClick={() => void onExecutar(tipo)}
          >
            <Icone className="h-5 w-5" />
            <span className="font-display text-sm font-bold">{titulo}</span>
            <small>{emHistorico ? "Volte ao ao vivo para simular" : subtitulo}</small>
          </button>
        ))}
      </div>
      {erro && (
        <p className="border-t border-destructive/30 bg-destructive/10 px-4 py-2 text-xs text-destructive">
          {erro}
        </p>
      )}
    </section>
  );
}

function ScenarioBanner({ cenario }: { cenario: CenarioManual }) {
  const evento = EVENTOS.find((item) => item.tipo === cenario.tipo);
  const Icone = evento?.Icone ?? ShieldAlert;
  return (
    <section className={`noc-scenario-banner noc-event-${evento?.tom ?? "orange"}`}>
      <Icone className="h-5 w-5 shrink-0" />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <strong className="font-display text-sm tracking-wide">
            CENÁRIO ATIVO: {cenario.nome.toUpperCase()}
          </strong>
          <span className="font-mono text-[10px]">{cenario.ciclos_restantes} CICLOS RESTANTES</span>
        </div>
        <p>{cenario.descricao}</p>
      </div>
    </section>
  );
}

function MapaInterativo({
  zonas,
  zonaSelecionada,
  cenario,
  onSelecionar,
}: {
  zonas: Zona[];
  zonaSelecionada: string | null;
  cenario: CenarioManual | null;
  onSelecionar: (zonaId: string) => void;
}) {
  const porId = new Map(zonas.map((zona) => [zona.zona_id, zona]));
  return (
    <div className="noc-map-canvas">
      <svg
        className="noc-flow-layer"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="0.7" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {LIGACOES.map(([origem, destino]) => {
          const a = porId.get(origem);
          const b = porId.get(destino);
          if (!a || !b) return null;
          const intensidade = Math.max(0.3, Math.min(1, (a.pct_carga + b.pct_carga) / 180));
          return (
            <g key={`${origem}-${destino}`}>
              <line className="noc-flow-base" x1={a.lng} y1={a.lat} x2={b.lng} y2={b.lat} />
              <line
                className="noc-flow-pulse"
                x1={a.lng}
                y1={a.lat}
                x2={b.lng}
                y2={b.lat}
                style={{
                  opacity: intensidade,
                  animationDuration: `${2.4 + (1 - intensidade) * 2}s`,
                }}
                filter="url(#glow)"
              />
            </g>
          );
        })}
      </svg>
      {zonas.map((zona) => {
        const cor = corRisco(zona.risco_atual);
        const afetada = Boolean(cenario?.zonas_afetadas.includes(zona.zona_id));
        const selecionada = zona.zona_id === zonaSelecionada;
        const estilo = {
          left: `${zona.lng}%`,
          top: `${zona.lat}%`,
          "--node-color": cor,
          "--node-intensity": `${Math.max(0.72, Math.min(1.25, zona.pct_carga / 75))}`,
        } as CSSProperties;
        return (
          <button
            key={zona.zona_id}
            type="button"
            className={`noc-zone-node ${selecionada ? "is-selected" : ""} ${afetada ? "is-affected" : ""}`}
            style={estilo}
            onClick={() => onSelecionar(zona.zona_id)}
            aria-pressed={selecionada}
          >
            <span className="noc-zone-radar" />
            <span className="noc-zone-core">
              <Zap className="h-3.5 w-3.5" />
            </span>
            <span className="noc-zone-label">
              <strong>{zona.zona_nome}</strong>
              <small>
                {zona.consumo_mw.toFixed(1)} MW · {zona.pct_carga.toFixed(0)}%
              </small>
            </span>
            {afetada && <span className="noc-zone-alert">SIM</span>}
          </button>
        );
      })}
      <div className="noc-map-compass">
        <MapPin className="h-3.5 w-3.5" /> SÃO PAULO · MALHA ILUSTRATIVA
      </div>
    </div>
  );
}

function Timeline({
  historico,
  deslocamento,
  onAlterar,
}: {
  historico: Array<{ ciclo: number; timestamp: string | null }>;
  deslocamento: number;
  onAlterar: (valor: number) => void;
}) {
  const total = Math.max(0, historico.length - 1);
  const indice = Math.max(0, historico.length - 1 - deslocamento);
  const ponto = historico[indice];
  return (
    <section className="noc-panel px-4 py-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <TimerReset className="h-4 w-4 text-primary" />
          <div>
            <h2 className="font-display text-xs font-extrabold uppercase tracking-[0.14em]">
              Timeline operacional
            </h2>
            <p className="text-[11px] text-muted-foreground">
              Navegue por snapshots recebidos; o histórico não é reprocessado.
            </p>
          </div>
        </div>
        <div className="font-mono text-[11px] text-primary">
          CICLO #{ponto?.ciclo ?? "--"} · {formatarHora(ponto?.timestamp)}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="noc-icon-button"
          disabled={deslocamento >= total}
          onClick={() => onAlterar(Math.min(total, deslocamento + 1))}
          aria-label="Voltar no histórico"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <input
          className="noc-timeline-input"
          type="range"
          min="0"
          max={total}
          value={total - deslocamento}
          disabled={total === 0}
          onChange={(evento) => onAlterar(total - Number(evento.target.value))}
          aria-label="Selecionar snapshot da timeline"
        />
        <button
          type="button"
          className="noc-icon-button"
          disabled={deslocamento === 0}
          onClick={() => onAlterar(Math.max(0, deslocamento - 1))}
          aria-label="Avançar no histórico"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-2 flex justify-between font-mono text-[9px] uppercase text-muted-foreground">
        <span>{historico[0] ? formatarHora(historico[0].timestamp) : "--"}</span>
        <span>AO VIVO {deslocamento === 0 ? "●" : ""}</span>
      </div>
    </section>
  );
}

function PainelZona({ zona, cenario }: { zona: Zona | null; cenario: CenarioManual | null }) {
  if (!zona)
    return (
      <section className="noc-panel p-5 text-center text-sm text-muted-foreground">
        Selecione uma zona no mapa.
      </section>
    );
  const afetada = Boolean(cenario?.zonas_afetadas.includes(zona.zona_id));
  return (
    <section className="noc-panel overflow-hidden">
      <div className="noc-panel-title">
        <MapPin className="h-4 w-4 text-primary" /> INSPEÇÃO DE ZONA
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-extrabold">{zona.zona_nome}</h2>
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {zona.perfil}
            </p>
          </div>
          <RiscoBadge risco={zona.risco_atual} label="AGORA" />
        </div>
        {afetada && (
          <div className="mt-3 rounded border border-primary/30 bg-primary/10 px-2.5 py-2 text-[11px] text-primary">
            Impacto projetado do cenário manual exibido neste nó.
          </div>
        )}
        <div className="noc-metric-grid mt-4">
          <Metrica
            label="Carga"
            valor={`${zona.pct_carga.toFixed(1)}%`}
            detalhe={`${zona.consumo_mw.toFixed(2)} MW`}
          />
          <Metrica
            label="Geração"
            valor={`${zona.geracao_total_mw.toFixed(2)} MW`}
            detalhe="renovável local"
          />
          <Metrica
            label="Frequência"
            valor={`${zona.frequencia_hz.toFixed(2)} Hz`}
            detalhe={zona.frequencia_hz < 59.9 ? "atenção" : "normal"}
          />
          <Metrica
            label="Bateria"
            valor={`${zona.bat_soc_pct.toFixed(0)}%`}
            detalhe={zona.bat_modo.toLowerCase()}
          />
        </div>
        <div className="mt-4 flex items-center justify-between border-t border-border/70 pt-3 text-xs">
          <span className="text-muted-foreground">THD / fator potência</span>
          <strong className="font-mono">
            {zona.thd_tensao_pct.toFixed(1)}% / {zona.fator_potencia.toFixed(3)}
          </strong>
        </div>
        <Link to="/zona/$id" params={{ id: zona.zona_id }} className="noc-detail-link mt-4">
          <Gauge className="h-3.5 w-3.5" /> Abrir histórico completo
        </Link>
      </div>
    </section>
  );
}

function PainelIA({
  zona,
  cenario,
  recomendacoes,
}: {
  zona: Zona | null;
  cenario: CenarioManual | null;
  recomendacoes: ReturnType<typeof useCityGrid>["recomendacoes"];
}) {
  const alertas = recomendacoes
    .filter((item) => !zona || item.zona_id === zona.zona_id || item.zona_id === "TODAS")
    .slice(0, 3);
  const orientacao = zona ? explicarCenario(cenario, zona) : null;
  return (
    <section className="noc-panel overflow-hidden">
      <div className="noc-panel-title">
        <Bot className="h-4 w-4 text-[var(--purple-elec)]" /> PAINEL IA · DECISÕES
      </div>
      <div className="space-y-3 p-4">
        {orientacao && (
          <div className="noc-ai-rationale">
            <span>LEITURA DO CENÁRIO</span>
            <p>{orientacao}</p>
          </div>
        )}
        {alertas.length ? (
          alertas.map((alerta) => (
            <article className="noc-ai-item" key={alerta.id}>
              <div className="flex items-center justify-between gap-2">
                <strong>{alerta.tipo}</strong>
                <span className={`noc-urgency ${alerta.urgencia}`}>{alerta.urgencia}</span>
              </div>
              <p>{alerta.descricao}</p>
              <small>{alerta.explicacao || `Fonte: ${alerta.origem}`}</small>
            </article>
          ))
        ) : (
          <p className="py-4 text-center text-xs text-muted-foreground">
            Nenhuma recomendação nova para esta seleção.
          </p>
        )}
        <div className="rounded border border-border/70 bg-muted/20 px-3 py-2 text-[10px] leading-relaxed text-muted-foreground">
          Saídas do motor são recomendações explicáveis; nenhuma ação é executada pelo dashboard.
        </div>
      </div>
    </section>
  );
}

function Metrica({ label, valor, detalhe }: { label: string; valor: string; detalhe: string }) {
  return (
    <div className="noc-metric">
      <span>{label}</span>
      <strong>{valor}</strong>
      <small>{detalhe}</small>
    </div>
  );
}
function LegendaCor({ risco }: { risco: Zona["risco_atual"] }) {
  return (
    <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
      <i className="h-1.5 w-1.5 rounded-full" style={{ background: corRisco(risco) }} />
      {risco}
    </span>
  );
}
function corRisco(risco: Zona["risco_atual"]): string {
  return {
    BAIXO: "var(--risk-low)",
    MÉDIO: "var(--risk-medium)",
    ALTO: "var(--risk-high)",
    CRÍTICO: "var(--risk-critical)",
  }[risco];
}
function formatarHora(valor: string | null | undefined) {
  const trecho = valor?.match(/T(\d{2}:\d{2}:\d{2})/)?.[1];
  return trecho ?? "--:--:--";
}

function projetarCenario(zonas: Zona[], cenario: CenarioManual | null): Zona[] {
  if (!cenario) return zonas;
  return zonas.map((zona) => {
    if (!cenario.zonas_afetadas.includes(zona.zona_id)) return zona;
    const impactos = cenario.impactos;
    const consumo = Math.min(
      zona.capacidade_mw,
      zona.consumo_mw * (1 + impactos.consumo_pct / 100),
    );
    const geracao = Math.max(0, zona.geracao_total_mw * (1 + impactos.geracao_pct / 100));
    const carga = (consumo / Math.max(zona.capacidade_mw, 0.01)) * 100;
    return {
      ...zona,
      consumo_mw: consumo,
      geracao_total_mw: geracao,
      pct_carga: carga,
      frequencia_hz: zona.frequencia_hz + impactos.frequencia_delta_hz,
      thd_tensao_pct: zona.thd_tensao_pct + impactos.thd_delta_pct,
      bat_soc_pct: Math.max(0, zona.bat_soc_pct + impactos.bateria_delta_pct),
      risco_atual: riscoPorCarga(carga, zona.risco_atual),
    };
  });
}

function riscoPorCarga(carga: number, atual: Zona["risco_atual"]): Zona["risco_atual"] {
  if (atual === "CRÍTICO" || carga >= 92) return "CRÍTICO";
  if (carga >= 78) return "ALTO";
  if (carga >= 58) return "MÉDIO";
  return atual;
}
function explicarCenario(cenario: CenarioManual | null, zona: Zona): string | null {
  if (!cenario?.zonas_afetadas.includes(zona.zona_id)) return null;
  if (cenario.tipo === "tempestade")
    return "IA sugere preservar reserva de bateria, monitorar THD e priorizar as cargas críticas até a recuperação da geração distribuída.";
  if (cenario.tipo === "incendio")
    return "IA sugere manter contingência na zona afetada, assegurar continuidade de cargas essenciais e evitar manobras automáticas sem aprovação humana.";
  return "IA sugere reduzir demanda não essencial, preparar descarga controlada da bateria e acompanhar a tendência de frequência antes de qualquer intervenção.";
}
