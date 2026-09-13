// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressoJogo } from "./ProgressoJogo";

describe("ProgressoJogo", () => {
  it("mostra progresso, fórmula transparente e feedback autoritativo da rodada", () => {
    render(
      <ProgressoJogo
        progressao={{
          pontos_total: 100,
          meta_pontos: 300,
          progresso_pct: 33.3,
          rodadas_concluidas: 1,
          total_rodadas: 3,
          bonus_alinhamento_total: 25,
          bonus_participacao_total: 25,
          feedback_rodada: {
            rodada: 1,
            pontos_base: 50,
            bonus_alinhamento: 25,
            bonus_participacao: 25,
            pontos_rodada: 100,
            pontos_total: 100,
            participacao_pct: 100,
            participantes_completos: 2,
            participantes_elegiveis: 2,
            alinhada_recomendacao: true,
            mensagem: "Missão concluída com alinhamento e participação total.",
          },
        }}
      />,
    );

    expect(screen.getByRole("heading", { name: "Progresso coletivo" })).toBeInTheDocument();
    expect(screen.getByText("100 / 300 pontos")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "33.3");
    expect(screen.getByText("+50 missão concluída")).toBeInTheDocument();
    expect(screen.getByText("+25 alinhamento completo")).toBeInTheDocument();
    expect(screen.getByText("+25 participação nas duas escolhas")).toBeInTheDocument();
    expect(screen.getByText(/bônus calculados pelo servidor/i)).toBeInTheDocument();
    expect(screen.getByText(/projeção sintética educacional/i)).toBeInTheDocument();
  });

  it("não derruba a rodada se um cliente receber o estado antigo sem progresso", () => {
    const { container } = render(<ProgressoJogo progressao={undefined as never} />);
    const painel = within(container);

    expect(painel.getByRole("heading", { name: "Progresso coletivo" })).toBeInTheDocument();
    expect(painel.getByText("0 / 300 pontos")).toBeInTheDocument();
    expect(painel.getByText("0 de 3 rodadas concluídas")).toBeInTheDocument();
  });
});
