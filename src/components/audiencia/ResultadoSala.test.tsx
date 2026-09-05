// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SalaPlateia } from "@/lib/audience-types";
import { ConsequenciaRodada } from "./ResultadoSala";

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
