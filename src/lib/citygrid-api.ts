import type {
  AtualizacaoWS,
  BatModo,
  CenarioManual,
  EstadoPrevisao,
  HistoricoPonto,
  Recomendacao,
  Risco,
  Stats,
  Zona,
} from "./citygrid-types";

const RISCOS = new Set<Risco>(["BAIXO", "MÉDIO", "ALTO", "CRÍTICO"]);
const ESTADOS = new Set<EstadoPrevisao>([
  "BAIXO",
  "MÉDIO",
  "ALTO",
  "CRÍTICO",
  "AGUARDANDO",
  "ERRO",
  "DESCONHECIDO",
]);

const COORDENADAS: Record<string, [number, number]> = {
  zona_norte: [22, 38],
  zona_sul: [74, 52],
  zona_leste: [52, 78],
  zona_oeste: [48, 18],
  zona_centro: [50, 50],
  zona_hospitalar: [64, 32],
  zona_universitaria: [28, 68],
  zona_aeroporto: [80, 82],
};

// Sem variável de ambiente, usa o mesmo host do dashboard. O Vite encaminha
// /api e /ws ao FastAPI no desenvolvimento, permitindo uma demonstração via ngrok.
const API_BASE = ((import.meta.env.VITE_CITYGRID_API_URL as string | undefined) ?? "").replace(
  /\/$/,
  "",
);

export function formatarHorarioSimulado(valor: string | null | undefined): string {
  if (!valor) return "--:--:--";
  const horario = valor.match(/T(\d{2}:\d{2}:\d{2})/);
  return horario?.[1] ?? "--:--:--";
}

function registro(valor: unknown): Record<string, unknown> {
  return valor !== null && typeof valor === "object" ? (valor as Record<string, unknown>) : {};
}

function numero(valor: unknown, padrao = 0): number {
  const convertido = Number(valor);
  return Number.isFinite(convertido) ? convertido : padrao;
}

function texto(valor: unknown, padrao = ""): string {
  return typeof valor === "string" ? valor : padrao;
}

function textoOpcional(valor: unknown): string | null {
  return typeof valor === "string" && valor.length > 0 ? valor : null;
}

function risco(valor: unknown, padrao: Risco = "BAIXO"): Risco {
  return RISCOS.has(valor as Risco) ? (valor as Risco) : padrao;
}

function estadoPrevisao(valor: unknown): EstadoPrevisao {
  return ESTADOS.has(valor as EstadoPrevisao) ? (valor as EstadoPrevisao) : "AGUARDANDO";
}

function batModo(valor: unknown): BatModo {
  return valor === "CARREGANDO" || valor === "DESCARGANDO" ? valor : "STANDBY";
}

export function normalizarZona(valor: unknown): Zona {
  const raw = registro(valor);
  const zonaId = texto(raw.zona_id, "zona_desconhecida");
  const [lat, lng] = COORDENADAS[zonaId] ?? [50, 50];
  const previsao = Array.isArray(raw.previsao_mw)
    ? raw.previsao_mw.map((item) => numero(item)).filter(Number.isFinite)
    : [];
  const conf = raw.conf_xgb == null ? null : numero(raw.conf_xgb);

  return {
    zona_id: zonaId,
    zona_nome: texto(raw.zona_nome, zonaId.replace(/_/g, " ")),
    perfil: texto(raw.perfil, "não informado"),
    timestamp: textoOpcional(raw.timestamp),
    ciclo: numero(raw.ciclo),
    consumo_mw: numero(raw.consumo_mw),
    capacidade_mw: numero(raw.capacidade_mw, 1),
    pct_carga: numero(raw.pct_carga),
    risco_atual: risco(raw.risco),
    risco_xgb: estadoPrevisao(raw.risco_xgb),
    risco_lstm: estadoPrevisao(raw.risco_lstm),
    conf_xgb: conf,
    geracao_total_mw: numero(raw.geracao_total_mw),
    solar_mw: numero(raw.solar_mw),
    eolica_mw: numero(raw.eolica_mw),
    frequencia_hz: numero(raw.frequencia_hz, 60),
    tensao_media_v: numero(raw.tensao_media_v, 220),
    thd_tensao_pct: numero(raw.thd_tensao_pct),
    fator_potencia: numero(raw.fator_potencia, 1),
    desequilibrio_pct: numero(raw.desequilibrio_tensao_pct),
    bat_soc_pct: numero(raw.bat_soc_pct),
    bat_modo: batModo(raw.bat_modo),
    ve_postos_em_uso: numero(raw.ve_postos_em_uso),
    ve_postos_total: numero(raw.ve_postos_total),
    clima_temp_c: numero(raw.clima_temp_c),
    clima_sensacao_c: numero(raw.clima_sensacao_c),
    clima_irrad_wm2: numero(raw.clima_irrad_wm2),
    clima_vento_ms: numero(raw.clima_vento_ms),
    clima_umidade_pct: numero(raw.clima_umidade_pct),
    anomalia_tipo: textoOpcional(raw.anomalia_tipo),
    evento: textoOpcional(raw.evento),
    previsao_mw: previsao,
    lat,
    lng,
  };
}

function normalizarCenario(valor: unknown): CenarioManual | null {
  const raw = registro(valor);
  const tipo = texto(raw.tipo);
  if (tipo !== "tempestade" && tipo !== "incendio" && tipo !== "pico_consumo") return null;
  const impactos = registro(raw.impactos);
  return {
    id: texto(raw.id),
    tipo,
    nome: texto(raw.nome),
    descricao: texto(raw.descricao),
    zonas_afetadas: Array.isArray(raw.zonas_afetadas)
      ? raw.zonas_afetadas.filter((zona): zona is string => typeof zona === "string")
      : [],
    ciclo_inicio: numero(raw.ciclo_inicio),
    ciclo_fim: numero(raw.ciclo_fim),
    ciclos_restantes: numero(raw.ciclos_restantes),
    impactos: {
      consumo_pct: numero(impactos.consumo_pct),
      geracao_pct: numero(impactos.geracao_pct),
      frequencia_delta_hz: numero(impactos.frequencia_delta_hz),
      thd_delta_pct: numero(impactos.thd_delta_pct),
      bateria_delta_pct: numero(impactos.bateria_delta_pct),
    },
  };
}

export function normalizarStats(valor: unknown, ciclo = 0): Stats {
  const raw = registro(valor);
  return {
    consumo_total_mw: numero(raw.consumo_total_mw),
    renovavel_pct: numero(raw.pct_renovavel),
    renovavel_mw: numero(raw.renovavel_total_mw),
    zonas_criticas: numero(raw.zonas_criticas),
    zonas_alto: numero(raw.zonas_alto),
    anomalias: numero(raw.anomalias_ativas),
    total_recomendacoes: numero(raw.total_recomendacoes),
    energia_renovavel_intervalo_mwh: numero(raw.energia_renovavel_intervalo_mwh),
    intervalo_simulado_minutos: numero(raw.intervalo_simulado_minutos, 5),
    ciclo,
    evento_ativo: textoOpcional(raw.evento_ativo),
    cenario_manual: normalizarCenario(raw.cenario_manual),
    dados_sinteticos: raw.dados_sinteticos !== false,
  };
}

function urgencia(valor: unknown): Recomendacao["urgencia"] {
  const normalizada = texto(valor)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase();
  if (normalizada === "CRITICA" || normalizada === "CRITICO") return "critico";
  if (normalizada === "ALTA" || normalizada === "ALTO") return "alto";
  if (normalizada === "MEDIA" || normalizada === "MEDIO") return "atencao";
  return "info";
}

function origem(valor: unknown): Recomendacao["origem"] {
  return valor === "xgboost" || valor === "lstm" || valor === "genetico" ? valor : "heuristica";
}

export function normalizarRecomendacao(
  valor: unknown,
  nomesZonas: Map<string, string>,
  indice: number,
): Recomendacao {
  const raw = registro(valor);
  const zonaId = texto(raw.zona_alvo ?? raw.zona_id, "TODAS");
  const ts = texto(raw.timestamp ?? raw.ts, "");
  const tipo = texto(raw.tipo, "RECOMENDACAO");
  const score = raw.confianca == null ? null : numero(raw.confianca);
  return {
    id: `${ts}-${zonaId}-${tipo}-${indice}`,
    ts,
    zona_id: zonaId,
    zona_nome: nomesZonas.get(zonaId) ?? (zonaId === "TODAS" ? "Todas as zonas" : zonaId),
    tipo: tipo.replace(/_/g, " "),
    urgencia: urgencia(raw.urgencia),
    origem: origem(raw.origem),
    descricao: texto(raw.descricao),
    explicacao: texto(raw.explicacao),
    score,
  };
}

export function normalizarHistorico(valor: unknown): HistoricoPonto[] {
  if (!Array.isArray(valor)) return [];
  return valor.map((item) => {
    const raw = registro(item);
    return {
      t: texto(raw.timestamp),
      ciclo: numero(raw.ciclo),
      consumo: numero(raw.consumo_mw),
      freq: numero(raw.frequencia_hz, 60),
      tensao: numero(raw.tensao_media_v, 220),
      thd: numero(raw.thd_tensao_pct),
      soc: numero(raw.bat_soc_pct),
    };
  });
}

async function buscarJson(caminho: string): Promise<unknown> {
  const resposta = await fetch(`${API_BASE}${caminho}`);
  if (!resposta.ok) throw new Error(`API respondeu HTTP ${resposta.status}`);
  return resposta.json();
}

export async function buscarEstadoInicial(): Promise<{
  zonas: Zona[];
  stats: Stats;
  recomendacoes: Recomendacao[];
}> {
  const [zonasRaw, statsRaw, recomendacoesRaw] = await Promise.all([
    buscarJson("/api/zonas"),
    buscarJson("/api/stats"),
    buscarJson("/api/alertas?n=20"),
  ]);
  const zonas = Array.isArray(zonasRaw) ? zonasRaw.map(normalizarZona) : [];
  const nomes = new Map(zonas.map((zona) => [zona.zona_id, zona.zona_nome]));
  const recomendacoes = Array.isArray(recomendacoesRaw)
    ? recomendacoesRaw.map((item, indice) => normalizarRecomendacao(item, nomes, indice))
    : [];
  const ciclo = Math.max(0, ...zonas.map((zona) => zona.ciclo));
  return { zonas, stats: normalizarStats(statsRaw, ciclo), recomendacoes };
}

export async function buscarHistorico(zonaId: string): Promise<HistoricoPonto[]> {
  return normalizarHistorico(
    await buscarJson(`/api/historico/${encodeURIComponent(zonaId)}?ultimas=48`),
  );
}

export async function ativarCenario(tipo: CenarioManual["tipo"]): Promise<CenarioManual> {
  const resposta = await fetch(`${API_BASE}/api/simulacao/evento`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tipo }),
  });
  if (!resposta.ok) throw new Error(`Não foi possível iniciar o cenário (HTTP ${resposta.status})`);
  const cenario = normalizarCenario(await resposta.json());
  if (!cenario) throw new Error("A API devolveu um cenário inválido");
  return cenario;
}

export async function limparCenario(): Promise<void> {
  const resposta = await fetch(`${API_BASE}/api/simulacao/evento`, { method: "DELETE" });
  if (!resposta.ok)
    throw new Error(`Não foi possível encerrar o cenário (HTTP ${resposta.status})`);
}

export function urlWebSocket(): string {
  if (API_BASE) return `${API_BASE.replace(/^http/, "ws")}/ws`;
  if (typeof window !== "undefined") {
    const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocolo}//${window.location.host}/ws`;
  }
  return "ws://127.0.0.1:8000/ws";
}

export function normalizarAtualizacao(valor: unknown): {
  zonas: Zona[];
  stats: Stats;
  recomendacoes: Recomendacao[];
  ciclo: number;
  timestampSimulado: string | null;
} {
  const raw = registro(valor) as Partial<AtualizacaoWS>;
  const zonas = Array.isArray(raw.zonas) ? raw.zonas.map(normalizarZona) : [];
  const nomes = new Map(zonas.map((zona) => [zona.zona_id, zona.zona_nome]));
  const ciclo = numero(raw.ciclo);
  const recomendacoes = Array.isArray(raw.recomendacoes)
    ? raw.recomendacoes.map((item, indice) => normalizarRecomendacao(item, nomes, indice))
    : [];
  return {
    zonas,
    stats: normalizarStats(raw.stats, ciclo),
    recomendacoes,
    ciclo,
    timestampSimulado: textoOpcional(raw.timestamp_simulado),
  };
}
