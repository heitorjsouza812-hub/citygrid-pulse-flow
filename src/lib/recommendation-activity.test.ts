import { describe, expect, it } from "vitest";

import type { Recomendacao } from "./citygrid-types";
import {
  FONTES_RECOMENDACAO,
  contarAtividadePorFonte,
  contarRecomendacoesPorOrigem,
  mesclarHistoricoRecomendacoes,
} from "./recommendation-activity";

function recommendation(id: string, origem: Recomendacao["origem"]): Recomendacao {
  return {
    id,
    ts: "2026-01-01T12:00:00",
    zona_id: "zona_norte",
    zona_nome: "Zona Norte",
    tipo: "TESTE",
    urgencia: "info",
    origem,
    descricao: "Atividade sintética",
    explicacao: "",
    score: null,
  };
}

describe("atividade das fontes de recomendação", () => {
  it("lista Heurística e exatamente quatro fontes analíticas, com Mistral marcado como POC", () => {
    expect(FONTES_RECOMENDACAO.map((fonte) => fonte.label)).toEqual([
      "Heurística",
      "XGBoost",
      "LSTM",
      "Genético",
      "Mistral 3B",
    ]);
    expect(FONTES_RECOMENDACAO.filter((fonte) => fonte.analitica)).toHaveLength(4);
    expect(FONTES_RECOMENDACAO.find((fonte) => fonte.id === "mistral3b")).toMatchObject({
      experimental: true,
      executaAoVivo: false,
    });
  });

  it("faz todos os painéis avançarem por ciclo sem chamar isso de inferência do Mistral", () => {
    const atividadeNoCicloUm = contarAtividadePorFonte([], 1);
    const atividadeNoCicloDoze = contarAtividadePorFonte([recommendation("h-1", "heuristica")], 12);

    for (const fonte of FONTES_RECOMENDACAO) {
      expect(atividadeNoCicloDoze[fonte.id]).toBeGreaterThan(atividadeNoCicloUm[fonte.id]);
    }
    expect(atividadeNoCicloDoze.mistral3b).toBe(12);
  });

  it("retém decisões já vistas e nunca reduz os contadores quando a janela avança", () => {
    const cicloUm = [recommendation("h-1", "heuristica"), recommendation("x-1", "xgboost")];
    const historicoUm = mesclarHistoricoRecomendacoes([], cicloUm);
    const contagemUm = contarRecomendacoesPorOrigem(historicoUm);

    const cicloDois = [recommendation("x-1", "xgboost"), recommendation("l-1", "lstm")];
    const historicoDois = mesclarHistoricoRecomendacoes(historicoUm, cicloDois);
    const contagemDois = contarRecomendacoesPorOrigem(historicoDois);

    expect(historicoDois.map((item) => item.id)).toEqual(["h-1", "x-1", "l-1"]);
    for (const fonte of FONTES_RECOMENDACAO) {
      expect(contagemDois[fonte.id]).toBeGreaterThanOrEqual(contagemUm[fonte.id]);
    }
  });
});
