export type Risco = "BAIXO" | "MÉDIO" | "ALTO" | "CRÍTICO";
export type BatModo = "CARREGANDO" | "STANDBY" | "DESCARGANDO";
export type Perfil = "residencial" | "comercial" | "industrial" | "misto" | "hospitalar" | "turístico";

export interface Zona {
  zona_id: string;
  zona_nome: string;
  perfil: Perfil;
  consumo_mw: number;
  capacidade_mw: number;
  pct_carga: number;
  risco_xgb: Risco;
  risco_lstm: Risco | "AGUARDANDO";
  conf_xgb: number;
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
  anomalia_tipo: string | null;
  evento: string | null;
  previsao_mw: number[];
  lat: number; // pseudo coords for stylized map (0-100)
  lng: number;
}

export interface Alerta {
  id: string;
  ts: string;
  min_ago: number;
  zona_id: string;
  zona_nome: string;
  tipo: string;
  urgencia: "info" | "atencao" | "alto" | "critico";
  origem: "heuristica" | "xgboost" | "lstm" | "genetico";
  descricao: string;
  confianca: number;
}

export interface Clima {
  temp_c: number;
  sensacao_c: number;
  irradiancia_wm2: number;
  vento_ms: number;
  umidade_pct: number;
  nebulosidade_pct: number;
}

export interface Stats {
  consumo_total_mw: number;
  renovavel_pct: number;
  renovavel_mw: number;
  zonas_criticas: number;
  anomalias: number;
  acoes_ia_total: number;
  economia_mwh: number;
  ciclo: number;
  evento_ativo: { nome: string; icone: string; impacto_pct: number } | null;
}

export const ZONAS_MOCK: Zona[] = [
  {
    zona_id: "zona_norte", zona_nome: "Zona Norte", perfil: "residencial",
    consumo_mw: 4.82, capacidade_mw: 18.0, pct_carga: 26.8,
    risco_xgb: "BAIXO", risco_lstm: "BAIXO", conf_xgb: 0.94,
    geracao_total_mw: 0.38, solar_mw: 0.38, eolica_mw: 0,
    frequencia_hz: 59.98, tensao_media_v: 219.2, thd_tensao_pct: 2.1,
    fator_potencia: 0.976, desequilibrio_pct: 1.2,
    bat_soc_pct: 72.4, bat_modo: "STANDBY",
    ve_postos_em_uso: 3, ve_postos_total: 8,
    clima_temp_c: 28.5, anomalia_tipo: null, evento: null,
    previsao_mw: [4.9, 5.1, 5.4, 5.8, 6.2, 6.0],
    lat: 22, lng: 38,
  },
  {
    zona_id: "zona_sul", zona_nome: "Zona Sul", perfil: "comercial",
    consumo_mw: 24.10, capacidade_mw: 30.0, pct_carga: 80.3,
    risco_xgb: "ALTO", risco_lstm: "CRÍTICO", conf_xgb: 0.87,
    geracao_total_mw: 0.62, solar_mw: 0.62, eolica_mw: 0,
    frequencia_hz: 59.85, tensao_media_v: 215.8, thd_tensao_pct: 6.4,
    fator_potencia: 0.918, desequilibrio_pct: 2.4,
    bat_soc_pct: 38.2, bat_modo: "DESCARGANDO",
    ve_postos_em_uso: 18, ve_postos_total: 25,
    clima_temp_c: 31.2, anomalia_tipo: null, evento: "Jogo de Futebol",
    previsao_mw: [25.2, 26.8, 28.1, 27.9, 26.4, 25.0],
    lat: 74, lng: 52,
  },
  {
    zona_id: "zona_oeste", zona_nome: "Zona Oeste", perfil: "industrial",
    consumo_mw: 57.20, capacidade_mw: 60.0, pct_carga: 95.3,
    risco_xgb: "CRÍTICO", risco_lstm: "CRÍTICO", conf_xgb: 0.96,
    geracao_total_mw: 4.80, solar_mw: 4.20, eolica_mw: 0.60,
    frequencia_hz: 59.62, tensao_media_v: 212.1, thd_tensao_pct: 8.9,
    fator_potencia: 0.882, desequilibrio_pct: 3.4,
    bat_soc_pct: 18.5, bat_modo: "DESCARGANDO",
    ve_postos_em_uso: 12, ve_postos_total: 15,
    clima_temp_c: 34.8, anomalia_tipo: "sobrecarga_transformador", evento: null,
    previsao_mw: [58.1, 59.2, 59.8, 58.4, 56.2, 54.0],
    lat: 48, lng: 18,
  },
  {
    zona_id: "zona_leste", zona_nome: "Zona Leste", perfil: "residencial",
    consumo_mw: 11.40, capacidade_mw: 22.0, pct_carga: 51.8,
    risco_xgb: "MÉDIO", risco_lstm: "MÉDIO", conf_xgb: 0.91,
    geracao_total_mw: 1.20, solar_mw: 1.10, eolica_mw: 0.10,
    frequencia_hz: 60.02, tensao_media_v: 220.4, thd_tensao_pct: 3.6,
    fator_potencia: 0.951, desequilibrio_pct: 1.8,
    bat_soc_pct: 58.0, bat_modo: "CARREGANDO",
    ve_postos_em_uso: 6, ve_postos_total: 12,
    clima_temp_c: 29.4, anomalia_tipo: null, evento: null,
    previsao_mw: [11.8, 12.1, 12.4, 12.8, 13.0, 12.6],
    lat: 52, lng: 78,
  },
  {
    zona_id: "zona_centro", zona_nome: "Centro Histórico", perfil: "comercial",
    consumo_mw: 18.60, capacidade_mw: 25.0, pct_carga: 74.4,
    risco_xgb: "ALTO", risco_lstm: "ALTO", conf_xgb: 0.89,
    geracao_total_mw: 0.84, solar_mw: 0.84, eolica_mw: 0,
    frequencia_hz: 59.94, tensao_media_v: 218.0, thd_tensao_pct: 5.2,
    fator_potencia: 0.935, desequilibrio_pct: 2.1,
    bat_soc_pct: 44.0, bat_modo: "STANDBY",
    ve_postos_em_uso: 14, ve_postos_total: 20,
    clima_temp_c: 32.1, anomalia_tipo: null, evento: "Jogo de Futebol",
    previsao_mw: [18.9, 19.4, 19.8, 19.2, 18.6, 18.0],
    lat: 50, lng: 50,
  },
  {
    zona_id: "zona_industrial2", zona_nome: "Distrito Industrial II", perfil: "industrial",
    consumo_mw: 42.30, capacidade_mw: 55.0, pct_carga: 76.9,
    risco_xgb: "ALTO", risco_lstm: "ALTO", conf_xgb: 0.92,
    geracao_total_mw: 3.10, solar_mw: 2.60, eolica_mw: 0.50,
    frequencia_hz: 59.91, tensao_media_v: 217.4, thd_tensao_pct: 5.8,
    fator_potencia: 0.928, desequilibrio_pct: 2.6,
    bat_soc_pct: 51.0, bat_modo: "DESCARGANDO",
    ve_postos_em_uso: 4, ve_postos_total: 10,
    clima_temp_c: 33.5, anomalia_tipo: "harmonica_alta", evento: null,
    previsao_mw: [43.1, 44.0, 44.8, 44.2, 43.0, 42.4],
    lat: 28, lng: 22,
  },
  {
    zona_id: "zona_hospitalar", zona_nome: "Polo Hospitalar", perfil: "hospitalar",
    consumo_mw: 8.90, capacidade_mw: 12.0, pct_carga: 74.2,
    risco_xgb: "MÉDIO", risco_lstm: "MÉDIO", conf_xgb: 0.95,
    geracao_total_mw: 0.94, solar_mw: 0.94, eolica_mw: 0,
    frequencia_hz: 60.00, tensao_media_v: 219.8, thd_tensao_pct: 2.8,
    fator_potencia: 0.968, desequilibrio_pct: 1.4,
    bat_soc_pct: 88.0, bat_modo: "STANDBY",
    ve_postos_em_uso: 2, ve_postos_total: 6,
    clima_temp_c: 30.0, anomalia_tipo: null, evento: null,
    previsao_mw: [9.0, 9.1, 9.3, 9.4, 9.4, 9.2],
    lat: 64, lng: 32,
  },
  {
    zona_id: "zona_praia", zona_nome: "Orla / Turismo", perfil: "turístico",
    consumo_mw: 6.20, capacidade_mw: 14.0, pct_carga: 44.3,
    risco_xgb: "BAIXO", risco_lstm: "MÉDIO", conf_xgb: 0.88,
    geracao_total_mw: 1.80, solar_mw: 1.50, eolica_mw: 0.30,
    frequencia_hz: 60.01, tensao_media_v: 220.1, thd_tensao_pct: 3.0,
    fator_potencia: 0.958, desequilibrio_pct: 1.6,
    bat_soc_pct: 65.0, bat_modo: "CARREGANDO",
    ve_postos_em_uso: 9, ve_postos_total: 14,
    clima_temp_c: 30.6, anomalia_tipo: null, evento: null,
    previsao_mw: [6.4, 6.7, 7.0, 7.3, 7.4, 7.1],
    lat: 82, lng: 84,
  },
];

export const ALERTAS_MOCK: Alerta[] = [
  { id: "a1", ts: nowMinus(0.5), min_ago: 0.5, zona_id: "zona_oeste", zona_nome: "Zona Oeste", tipo: "Redução de Carga Industrial", urgencia: "critico", origem: "xgboost", descricao: "Reduzir 12 MW em fornos não-críticos por 15 min", confianca: 0.96 },
  { id: "a2", ts: nowMinus(1), min_ago: 1, zona_id: "zona_sul", zona_nome: "Zona Sul", tipo: "Despacho de Bateria", urgencia: "alto", origem: "lstm", descricao: "Iniciar descarga 4 MW da BESS-SUL-01", confianca: 0.87 },
  { id: "a3", ts: nowMinus(2.4), min_ago: 2, zona_id: "zona_industrial2", zona_nome: "Distrito Industrial II", tipo: "Filtro Harmônico", urgencia: "alto", origem: "heuristica", descricao: "THD acima de 5% — ativar filtro passivo", confianca: 1.0 },
  { id: "a4", ts: nowMinus(3.1), min_ago: 3, zona_id: "zona_centro", zona_nome: "Centro Histórico", tipo: "Realocação de Carga", urgencia: "atencao", origem: "genetico", descricao: "Transferir 2 MW para alimentador CTR-04", confianca: 0.82 },
  { id: "a5", ts: nowMinus(4.7), min_ago: 4, zona_id: "zona_leste", zona_nome: "Zona Leste", tipo: "Pré-aquecimento Bateria", urgencia: "info", origem: "heuristica", descricao: "Carregar BESS-LES-02 até 80% antes do pico", confianca: 1.0 },
  { id: "a6", ts: nowMinus(6.2), min_ago: 6, zona_id: "zona_sul", zona_nome: "Zona Sul", tipo: "Alerta de Evento", urgencia: "alto", origem: "lstm", descricao: "Jogo de Futebol — pico esperado em 25 min", confianca: 0.91 },
  { id: "a7", ts: nowMinus(8), min_ago: 8, zona_id: "zona_oeste", zona_nome: "Zona Oeste", tipo: "Anomalia Detectada", urgencia: "critico", origem: "xgboost", descricao: "Sobrecarga em TR-OES-03 (95.3%)", confianca: 0.96 },
  { id: "a8", ts: nowMinus(12), min_ago: 12, zona_id: "zona_norte", zona_nome: "Zona Norte", tipo: "Modo Econômico", urgencia: "info", origem: "genetico", descricao: "Dimming 15% iluminação pública das 23h às 5h", confianca: 0.78 },
  { id: "a9", ts: nowMinus(18), min_ago: 18, zona_id: "zona_hospitalar", zona_nome: "Polo Hospitalar", tipo: "Reserva Ativada", urgencia: "atencao", origem: "heuristica", descricao: "Manter BESS-HOSP-01 ≥ 80% — protocolo crítico", confianca: 1.0 },
  { id: "a10", ts: nowMinus(25), min_ago: 25, zona_id: "zona_praia", zona_nome: "Orla / Turismo", tipo: "Otimização VE", urgencia: "info", origem: "genetico", descricao: "Reescalonar 4 sessões de carregamento", confianca: 0.84 },
];

export const CLIMA_MOCK: Clima = {
  temp_c: 31.2, sensacao_c: 34.8, irradiancia_wm2: 842, vento_ms: 3.4, umidade_pct: 62, nebulosidade_pct: 18,
};

export const STATS_MOCK: Stats = {
  consumo_total_mw: ZONAS_MOCK.reduce((s, z) => s + z.consumo_mw, 0),
  renovavel_mw: ZONAS_MOCK.reduce((s, z) => s + z.geracao_total_mw, 0),
  renovavel_pct: 0,
  zonas_criticas: ZONAS_MOCK.filter(z => z.risco_xgb === "CRÍTICO").length,
  anomalias: ZONAS_MOCK.filter(z => z.anomalia_tipo).length,
  acoes_ia_total: 1247,
  economia_mwh: 184.6,
  ciclo: 8432,
  evento_ativo: { nome: "Jogo de Futebol — Estádio Municipal", icone: "⚽", impacto_pct: 12.4 },
};
STATS_MOCK.renovavel_pct = (STATS_MOCK.renovavel_mw / STATS_MOCK.consumo_total_mw) * 100;



// Substations and transformers — operational fleet data
export interface Subestacao {
  id: string;
  nome: string;
  zona_id: string;
  tensao_kv: number;
  carga_pct: number;
  status: "ok" | "alerta" | "manutencao" | "falha";
  temp_c: number;
}
export const SUBESTACOES_MOCK: Subestacao[] = [
  { id: "SE-NRT-01", nome: "SE Norte 1", zona_id: "zona_norte", tensao_kv: 69, carga_pct: 32, status: "ok", temp_c: 41 },
  { id: "SE-SUL-02", nome: "SE Sul 2", zona_id: "zona_sul", tensao_kv: 138, carga_pct: 82, status: "alerta", temp_c: 58 },
  { id: "SE-OES-01", nome: "SE Oeste 1", zona_id: "zona_oeste", tensao_kv: 138, carga_pct: 96, status: "falha", temp_c: 71 },
  { id: "SE-LES-03", nome: "SE Leste 3", zona_id: "zona_leste", tensao_kv: 69, carga_pct: 54, status: "ok", temp_c: 44 },
  { id: "SE-CTR-01", nome: "SE Centro 1", zona_id: "zona_centro", tensao_kv: 138, carga_pct: 76, status: "alerta", temp_c: 52 },
  { id: "SE-IND-02", nome: "SE Industrial 2", zona_id: "zona_industrial2", tensao_kv: 230, carga_pct: 78, status: "ok", temp_c: 49 },
  { id: "SE-HSP-01", nome: "SE Hospitalar", zona_id: "zona_hospitalar", tensao_kv: 69, carga_pct: 75, status: "manutencao", temp_c: 46 },
  { id: "SE-ORL-01", nome: "SE Orla", zona_id: "zona_praia", tensao_kv: 69, carga_pct: 44, status: "ok", temp_c: 39 },
];

export interface Transformador {
  id: string;
  se: string;
  potencia_mva: number;
  carga_pct: number;
  oleo_c: number;
  enrol_c: number;
  saude: number; // 0-100
}
export const TRANSFORMADORES_MOCK: Transformador[] = [
  { id: "TR-OES-03", se: "SE-OES-01", potencia_mva: 40, carga_pct: 95.3, oleo_c: 78, enrol_c: 112, saude: 62 },
  { id: "TR-SUL-02", se: "SE-SUL-02", potencia_mva: 30, carga_pct: 82.1, oleo_c: 64, enrol_c: 98, saude: 81 },
  { id: "TR-IND-05", se: "SE-IND-02", potencia_mva: 50, carga_pct: 77.4, oleo_c: 58, enrol_c: 92, saude: 88 },
  { id: "TR-CTR-04", se: "SE-CTR-01", potencia_mva: 25, carga_pct: 74.0, oleo_c: 55, enrol_c: 88, saude: 90 },
  { id: "TR-LES-01", se: "SE-LES-03", potencia_mva: 20, carga_pct: 51.8, oleo_c: 48, enrol_c: 78, saude: 95 },
  { id: "TR-NRT-02", se: "SE-NRT-01", potencia_mva: 20, carga_pct: 26.8, oleo_c: 42, enrol_c: 68, saude: 98 },
];

export interface TarifaWindow {
  nome: string;
  inicio: string;
  fim: string;
  preco_rs_mwh: number;
  tipo: "fora-ponta" | "intermediario" | "ponta";
  ativo: boolean;
}
export const TARIFA_MOCK: TarifaWindow[] = [
  { nome: "Fora Ponta",       inicio: "00:00", fim: "17:30", preco_rs_mwh: 287.40, tipo: "fora-ponta",   ativo: false },
  { nome: "Intermediário",    inicio: "17:30", fim: "20:30", preco_rs_mwh: 412.10, tipo: "intermediario",ativo: true  },
  { nome: "Ponta",            inicio: "20:30", fim: "23:30", preco_rs_mwh: 1024.80, tipo: "ponta",        ativo: false },
  { nome: "Fora Ponta",       inicio: "23:30", fim: "24:00", preco_rs_mwh: 287.40, tipo: "fora-ponta",   ativo: false },
];

export interface ShiftInfo {
  operador: string;
  matricula: string;
  turno: string;
  inicio: string;
  fim: string;
  supervisor: string;
  centro: string;
}
export const SHIFT_MOCK: ShiftInfo = {
  operador: "Carlos R. Mendes",
  matricula: "OP-2381",
  turno: "Vespertino",
  inicio: "14:00",
  fim: "22:00",
  supervisor: "Eng. Patrícia Vieira",
  centro: "COS — Centro de Operações do Sistema",
};


export function generateHistorico(zona: Zona, n = 48): { t: number; consumo: number; previsao: number; freq: number; tensao: number; thd: number; soc: number }[] {
  const out = [];
  const base = zona.consumo_mw;
  for (let i = 0; i < n; i++) {
    const wave = Math.sin((i / n) * Math.PI * 2) * base * 0.18;
    const noise = (Math.random() - 0.5) * base * 0.06;
    const consumo = Math.max(0.1, base + wave + noise - base * 0.05);
    out.push({
      t: i,
      consumo: +consumo.toFixed(2),
      previsao: +(consumo * (1 + (Math.random() - 0.5) * 0.04)).toFixed(2),
      freq: +(zona.frequencia_hz + (Math.random() - 0.5) * 0.06).toFixed(3),
      tensao: +(zona.tensao_media_v + (Math.random() - 0.5) * 2).toFixed(1),
      thd: +(zona.thd_tensao_pct + (Math.random() - 0.5) * 0.6).toFixed(2),
      soc: +(zona.bat_soc_pct + Math.sin(i / 6) * 8 + (Math.random() - 0.5) * 2).toFixed(1),
    });
  }
  return out;
}
