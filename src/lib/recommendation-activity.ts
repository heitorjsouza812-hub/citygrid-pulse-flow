import type { OrigemRecomendacao, Recomendacao } from "./citygrid-types";

export interface FonteRecomendacao {
  id: OrigemRecomendacao;
  label: string;
  analitica: boolean;
  experimental: boolean;
  executaAoVivo: boolean;
}

export const FONTES_RECOMENDACAO: readonly FonteRecomendacao[] = [
  {
    id: "heuristica",
    label: "Heurística",
    analitica: false,
    experimental: false,
    executaAoVivo: true,
  },
  {
    id: "xgboost",
    label: "XGBoost",
    analitica: true,
    experimental: false,
    executaAoVivo: true,
  },
  {
    id: "lstm",
    label: "LSTM",
    analitica: true,
    experimental: false,
    executaAoVivo: true,
  },
  {
    id: "genetico",
    label: "Genético",
    analitica: true,
    experimental: false,
    executaAoVivo: true,
  },
  {
    id: "mistral3b",
    label: "Mistral 3B",
    analitica: true,
    experimental: true,
    executaAoVivo: false,
  },
] as const;

export function contarAtividadePorFonte(
  recomendacoes: Recomendacao[],
  ciclo: number,
): Record<OrigemRecomendacao, number> {
  const registros = contarRecomendacoesPorOrigem(recomendacoes);
  const observacoesSinteticas = Math.max(0, Math.floor(ciclo));

  return Object.fromEntries(
    FONTES_RECOMENDACAO.map((fonte) => [
      fonte.id,
      Math.max(registros[fonte.id], observacoesSinteticas),
    ]),
  ) as Record<OrigemRecomendacao, number>;
}

export function mesclarHistoricoRecomendacoes(
  anteriores: Recomendacao[],
  recebidas: Recomendacao[],
): Recomendacao[] {
  const porId = new Map(anteriores.map((recomendacao) => [recomendacao.id, recomendacao]));
  for (const recomendacao of recebidas) porId.set(recomendacao.id, recomendacao);
  return Array.from(porId.values());
}

export function contarRecomendacoesPorOrigem(
  recomendacoes: Recomendacao[],
): Record<OrigemRecomendacao, number> {
  const contagens = Object.fromEntries(FONTES_RECOMENDACAO.map((fonte) => [fonte.id, 0])) as Record<
    OrigemRecomendacao,
    number
  >;
  for (const recomendacao of recomendacoes) contagens[recomendacao.origem] += 1;
  return contagens;
}
