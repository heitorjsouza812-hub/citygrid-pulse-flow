// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SalaPlateia } from "@/lib/audience-types";
import { ComparacaoPlateiaIA, ConsequenciaRodada, ResumoFinal } from "./ResultadoSala";

const sala = {
  consequencia: {
    projecao: true,
    resumo: "Baterias foram direcionadas para a Zona Norte.",
    zonas_afetadas: ["zona_norte", "zona_oeste", "zona_aeroporto"],
    zona_priorizada: "zona_norte",
    acao: "usar_baterias",
    deltas: { estabilidade: 12, reserva: -8, controle_custos: -3, satisfacao: 4 },
    telemetria: {},
    alertas: [],
  },
  placar: {
    estabilidade: 82,
    reserva: 62,
    controle_custos: 67,
    satisfacao: 79,
    pontuacao_geral: 75,
  },
  placar_antes: {
    estabilidade: 70,
    reserva: 70,
    controle_custos: 70,
    satisfacao: 75,
    pontuacao_geral: 72,
  },
} as unknown as SalaPlateia;

describe("ConsequenciaRodada", () => {
  it("mostra a área protegida e o placar antes e depois", () => {
    render(<ConsequenciaRodada sala={sala} />);

    expect(screen.getByText("ÁREA PROTEGIDA")).toBeInTheDocument();
    expect(screen.getByText("Norte")).toBeInTheDocument();
    expect(screen.getByText("ANTES → DEPOIS")).toBeInTheDocument();
    expect(screen.getByText("82")).toBeInTheDocument();
  });
});

describe("feedback educacional da rodada", () => {
  it("compara com a recomendação documentada sem sugerir uma IA ao vivo", () => {
    render(
      <ComparacaoPlateiaIA
        sala={
          {
            vencedores: { zona: "zona_norte", acao: "usar_baterias" },
            recomendacao: {
              zona: "zona_norte",
              acao: "usar_baterias",
              origem: "Heurística explicável + cenário sintético",
              explicacao: "Regra documentada para o cenário educacional.",
              semelhante: true,
              classificacao: "Escolha semelhante à recomendação",
            },
          } as unknown as SalaPlateia
        }
      />,
    );

    expect(screen.getByText("Recomendação documentada")).toBeInTheDocument();
    expect(screen.getByText(/referência sintética para a conversa/i)).toBeInTheDocument();
    expect(screen.queryByText(/^IA$/)).not.toBeInTheDocument();
  });

  it("encerra distinguindo pontos do jogo do desempenho projetado da cidade", () => {
    render(
      <ResumoFinal
        sala={
          {
            resumo_final: {
              rodadas: 3,
              pontuacao_final: 82,
              pontos_jogo: 250,
              meta_pontos: 300,
              bonus_alinhamento_total: 50,
              bonus_participacao_total: 50,
              participantes: 4,
              total_votos: 24,
              semelhantes_ia: 2,
              diferentes_ia: 1,
              melhor_rodada: 2,
              rodada_mais_arriscada: 3,
              mensagem: "Resumo",
            },
          } as SalaPlateia
        }
      />,
    );

    expect(screen.getByText("PONTOS DO JOGO")).toBeInTheDocument();
    expect(screen.getByText("250 / 300")).toBeInTheDocument();
    expect(screen.getByText("82% de desempenho projetado da cidade")).toBeInTheDocument();
    expect(screen.getByText("+50 alinhamento")).toBeInTheDocument();
    expect(screen.getByText("+50 participação")).toBeInTheDocument();
  });
});
