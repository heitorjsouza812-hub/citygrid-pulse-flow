export type Risco = "BAIXO" | "MÉDIO" | "ALTO" | "CRÍTICO";
export type EstadoPrevisao = Risco | "AGUARDANDO" | "ERRO" | "DESCONHECIDO";
export type BatModo = "CARREGANDO" | "STANDBY" | "DESCARGANDO";
export type StatusConexao = "conectado" | "conectando" | "offline";
export type TipoCenario = "tempestade" | "incendio" | "pico_consumo";

export interface ImpactosCenario {
  consumo_pct: number;
  geracao_pct: number;
  frequencia_delta_hz: number;
  thd_delta_pct: number;
  bateria_delta_pct: number;
}

export interface CenarioManual {
  id: string;
  tipo: TipoCenario;
  nome: string;
  descricao: string;
  zonas_afetadas: string[];
  ciclo_inicio: number;
  ciclo_fim: number;
  ciclos_restantes: number;
  impactos: ImpactosCenario;
}

export interface Zona {
  zona_id: string;
  zona_nome: string;
  perfil: string;
  timestamp: string | null;
  ciclo: number;
  consumo_mw: number;
  capacidade_mw: number;
  pct_carga: number;
  risco_atual: Risco;
  risco_xgb: EstadoPrevisao;
  risco_lstm: EstadoPrevisao;
  conf_xgb: number | null;
  geracao_total_mw: number;
  solar_mw: number;
  eolica_mw: number;
  frequencia_hz: number;
  tensao_media_v: number;
  thd_tensao_pct: number;
  fator_potencia: number;
  desequilibrio_pct: number;
  bat_soc_pct: number;
  bat_modo: BatModo;
  ve_postos_em_uso: number;
  ve_postos_total: number;
  clima_temp_c: number;
  clima_sensacao_c: number;
  clima_irrad_wm2: number;
  clima_vento_ms: number;
  clima_umidade_pct: number;
  anomalia_tipo: string | null;
  evento: string | null;
  previsao_mw: number[];
  lat: number;
  lng: number;
}

export interface Recomendacao {
  id: string;
  ts: string;
  zona_id: string;
  zona_nome: string;
  tipo: string;
  urgencia: "info" | "atencao" | "alto" | "critico";
  origem: "heuristica" | "xgboost" | "lstm" | "genetico";
  descricao: string;
  explicacao: string;
  score: number | null;
}

export interface Stats {
  consumo_total_mw: number;
  renovavel_pct: number;
  renovavel_mw: number;
  zonas_criticas: number;
  zonas_alto: number;
  anomalias: number;
  total_recomendacoes: number;
  energia_renovavel_intervalo_mwh: number;
  intervalo_simulado_minutos: number;
  ciclo: number;
  evento_ativo: string | null;
  cenario_manual: CenarioManual | null;
  dados_sinteticos: boolean;
}

export interface SnapshotTelemetria {
  ciclo: number;
  timestamp: string | null;
  zonas: Zona[];
  stats: Stats;
  recomendacoes: Recomendacao[];
}

export interface HistoricoPonto {
  t: string;
  ciclo: number;
  consumo: number;
  freq: number;
  tensao: number;
  thd: number;
  soc: number;
}

export interface AtualizacaoWS {
  tipo: "update";
  ciclo: number;
  timestamp_simulado: string | null;
  atualizado_em_utc: string;
  zonas: unknown[];
  stats: unknown;
  recomendacoes: unknown[];
}
