// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Recomendacao } from "@/lib/citygrid-types";
import { FontesRecomendacao } from "./FontesRecomendacao";

const recomendacao = (id: string, origem: Recomendacao["origem"]): Recomendacao => ({
  id,
  ts: "2026-01-01T12:00:00",
  zona_id: "zona_norte",
  zona_nome: "Zona Norte",
  tipo: "TESTE",
  urgencia: "info",
  origem,
  descricao: "Registro de teste",
  explicacao: "",
  score: null,
});

describe("FontesRecomendacao", () => {
  it("explica os contadores de sessão e identifica Mistral 3B sem sugerir inferência ao vivo", () => {
    render(
      <FontesRecomendacao
        recomendacoes={[
          recomendacao("h-1", "heuristica"),
          recomendacao("x-1", "xgboost"),
          recomendacao("l-1", "lstm"),
          recomendacao("g-1", "genetico"),
        ]}
        ciclo={12}
      />,
    );

    const painel = screen.getByRole("region", { name: "Atividade por fonte" });
    expect(
      within(painel).getByRole("heading", { name: "Heurística + 4 fontes analíticas" }),
    ).toBeInTheDocument();
    expect(within(painel).getAllByRole("listitem")).toHaveLength(5);
    expect(within(painel).getAllByText("12")).toHaveLength(5);
    expect(within(painel).getByText("Mistral 3B")).toBeInTheDocument();
    expect(
      within(painel).getByText("POC experimental · observação sem inferência ao vivo"),
    ).toBeInTheDocument();
    expect(
      within(painel).getByText(/cada ciclo alimenta uma observação sintética em todos os painéis/i),
    ).toBeInTheDocument();
    expect(
      within(painel).getByText(/não são métricas de produção, desempenho ou acurácia/i),
    ).toBeInTheDocument();
  });
});
