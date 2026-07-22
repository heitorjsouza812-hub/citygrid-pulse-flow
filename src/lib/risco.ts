import type { EstadoPrevisao } from "./citygrid-types";

export function riscoColor(r: EstadoPrevisao): string {
  switch (r) {
    case "BAIXO":
      return "var(--risk-low)";
    case "MÉDIO":
      return "var(--risk-med)";
    case "ALTO":
      return "var(--risk-high)";
    case "CRÍTICO":
      return "var(--risk-crit)";
    default:
      return "var(--muted-foreground)";
  }
}

export function cargaColor(pct: number): string {
  if (pct >= 90) return "var(--risk-crit)";
  if (pct >= 75) return "var(--risk-high)";
  if (pct >= 50) return "var(--risk-med)";
  return "var(--risk-low)";
}

export function urgenciaColor(u: string): string {
  switch (u) {
    case "critico":
      return "var(--risk-crit)";
    case "alto":
      return "var(--risk-high)";
    case "atencao":
      return "var(--risk-med)";
    default:
      return "var(--cyan-elec)";
  }
}

export function aneelFreq(hz: number): "verde" | "amarelo" | "vermelho" {
  if (hz >= 59.9 && hz <= 60.1) return "verde";
  if (hz >= 59.5 && hz <= 60.5) return "amarelo";
  return "vermelho";
}
export function aneelTHD(thd: number): "verde" | "amarelo" | "vermelho" {
  if (thd < 5) return "verde";
  if (thd <= 8) return "amarelo";
  return "vermelho";
}
export function aneelFP(fp: number): "verde" | "amarelo" | "vermelho" {
  return fp >= 0.92 ? "verde" : "vermelho";
}
export function aneelDeseq(d: number): "verde" | "amarelo" | "vermelho" {
  if (d < 2) return "verde";
  if (d <= 3) return "amarelo";
  return "vermelho";
}
