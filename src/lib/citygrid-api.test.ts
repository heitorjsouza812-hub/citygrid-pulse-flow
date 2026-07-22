import { describe, expect, it } from "vitest";

import {
  formatarHorarioSimulado,
  normalizarRecomendacao,
  normalizarStats,
  normalizarZona,
} from "./citygrid-api";

describe("normalizarZona", () => {
  it("mapeia o contrato real do backend e mantém risco atual separado da previsão", () => {
    const zona = normalizarZona({
      zona_id: "zona_universitaria",
      zona_nome: "Zona Universitária",
      perfil: "educacional",
      risco: "MÉDIO",
      risco_xgb: "ALTO",
      risco_lstm: "BAIXO",
      consumo_mw: 4.5,
      capacidade_mw: 10,
      pct_carga: 45,
      desequilibrio_tensao_pct: 1.3,
      previsao_mw: [4.6, 4.7],
    });

    expect(zona.risco_atual).toBe("MÉDIO");
    expect(zona.risco_xgb).toBe("ALTO");
    expect(zona.desequilibrio_pct).toBe(1.3);
    expect(zona.previsao_mw).toEqual([4.6, 4.7]);
    expect(zona.lat).toBeTypeOf("number");
    expect(zona.lng).toBeTypeOf("number");
  });
});

describe("normalizarStats", () => {
  it("não inventa economia e preserva a energia renovável medida", () => {
    const stats = normalizarStats({
      consumo_total_mw: 100,
      renovavel_total_mw: 12,
      pct_renovavel: 12,
      zonas_criticas: 1,
      anomalias_ativas: 2,
      total_recomendacoes: 3,
      energia_renovavel_intervalo_mwh: 1,
      intervalo_simulado_minutos: 5,
      dados_sinteticos: true,
    });

    expect(stats.energia_renovavel_intervalo_mwh).toBe(1);
    expect(stats.total_recomendacoes).toBe(3);
    expect(stats.dados_sinteticos).toBe(true);
    expect(stats).not.toHaveProperty("economia_mwh");
  });
});

describe("normalizarRecomendacao", () => {
  it("converte a saída do motor sem afirmar execução", () => {
    const recomendacao = normalizarRecomendacao(
      {
        timestamp: "2026-01-01T12:00:00",
        zona_alvo: "zona_sul",
        tipo: "ACAO_PREVENTIVA",
        urgencia: "ALTA",
        origem: "lstm",
        descricao: "Preparar resposta",
        confianca: null,
      },
      new Map([["zona_sul", "Zona Sul"]]),
      0,
    );

    expect(recomendacao.zona_nome).toBe("Zona Sul");
    expect(recomendacao.urgencia).toBe("alto");
    expect(recomendacao.score).toBeNull();
    expect(recomendacao.descricao).toBe("Preparar resposta");
  });
});

describe("formatarHorarioSimulado", () => {
  it("exibe o horário da amostra sem compará-lo ao relógio real", () => {
    expect(formatarHorarioSimulado("2026-01-01T12:34:56")).toBe("12:34:56");
    expect(formatarHorarioSimulado(null)).toBe("--:--:--");
  });
});
