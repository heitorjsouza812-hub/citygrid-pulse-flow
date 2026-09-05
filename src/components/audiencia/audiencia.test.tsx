// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PainelVotacao } from "./PainelVotacao";
import { PlacarCidade } from "./PlacarCidade";

describe("componentes da Central de Decisão da Plateia", () => {
  it("renderiza placar com quatro indicadores", () => {
    render(
      <PlacarCidade
        placar={{
          estabilidade: 75,
          reserva: 70,
          controle_custos: 70,
          satisfacao: 75,
          pontuacao_geral: 73.3,
        }}
      />,
    );
    expect(screen.getByLabelText("Placar da cidade")).toHaveTextContent("Estabilidade");
    expect(screen.getByText("73%")).toBeInTheDocument();
  });

  it("oculta contagem durante resultado oculto e registra seleção", () => {
    const vote = vi.fn();
    render(
      <PainelVotacao
        question="Qual zona deve ser priorizada?"
        options={[{ id: "zona_norte", label: "Norte" }]}
        counts={{ zona_norte: 2 }}
        visible={false}
        onVote={vote}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Norte" }));
    expect(vote).toHaveBeenCalledWith("zona_norte");
    expect(screen.getByText(/As escolhas aparecem ao final/)).toBeInTheDocument();
    expect(screen.queryByText("100%")).not.toBeInTheDocument();
  });

  it("mostra porcentagem quando resultado ao vivo é habilitado", () => {
    render(
      <PainelVotacao
        question="Ação"
        options={[{ id: "usar_baterias", label: "Utilizar baterias" }]}
        counts={{ usar_baterias: 3 }}
        visible
        onVote={() => undefined}
      />,
    );
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("explica a missão atual antes das opções de voto", () => {
    render(
      <PainelVotacao
        step="MISSÃO 1 DE 2"
        question="Onde agir primeiro?"
        options={[{ id: "zona_norte", label: "Zona Norte" }]}
        counts={{}}
        visible={false}
        onVote={() => undefined}
      />,
    );
    expect(screen.getByText("MISSÃO 1 DE 2")).toBeInTheDocument();
    expect(screen.getAllByText("Escolha uma opção para ajudar a cidade.")).toHaveLength(3);
  });
});
