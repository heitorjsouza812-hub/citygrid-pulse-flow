import { ZONAS_MOCK } from "@/lib/mock-data";
import { aneelFreq, aneelTHD, aneelFP, aneelDeseq } from "@/lib/risco";
import { ShieldCheck } from "lucide-react";

const semColor: Record<string, string> = {
  verde: "var(--risk-low)",
  amarelo: "var(--risk-med)",
  vermelho: "var(--risk-crit)",
};

function pct(arr: string[], target: string) {
  return (arr.filter((s) => s === target).length / arr.length) * 100;
}

export function ConformidadeANEELPanel() {
  const freqs = ZONAS_MOCK.map((z) => aneelFreq(z.frequencia_hz));
  const thds = ZONAS_MOCK.map((z) => aneelTHD(z.thd_tensao_pct));
  const fps = ZONAS_MOCK.map((z) => aneelFP(z.fator_potencia));
  const desq = ZONAS_MOCK.map((z) => aneelDeseq(z.desequilibrio_pct));

  const rows = [
    { label: "Frequência (60 Hz ±0,1)", arr: freqs, limite: "59,9 – 60,1 Hz" },
    { label: "THD de Tensão", arr: thds, limite: "< 5% (alerta < 8%)" },
    { label: "Fator de Potência", arr: fps, limite: "≥ 0,92" },
    { label: "Desequilíbrio de Tensão", arr: desq, limite: "< 2% (alerta < 3%)" },
  ];

  return (
    <div className="card-surface">
      <div className="flex items-center justify-between px-4 h-10 border-b border-border">
        <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-2">
          <ShieldCheck className="h-3.5 w-3.5" /> Conformidade ANEEL · PRODIST M8
        </h3>
        <span className="text-[10px] font-mono text-muted-foreground tabular-nums">8 zonas</span>
      </div>
      <div className="p-4 space-y-3">
        {rows.map((r) => {
          const v = pct(r.arr, "verde");
          const a = pct(r.arr, "amarelo");
          const vm = pct(r.arr, "vermelho");
          return (
            <div key={r.label}>
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-foreground">{r.label}</span>
                <span className="font-mono text-muted-foreground text-[10px]">{r.limite}</span>
              </div>
              <div className="flex h-1.5 w-full rounded-sm overflow-hidden border border-border">
                {v > 0 && <div style={{ width: `${v}%`, backgroundColor: semColor.verde }} />}
                {a > 0 && <div style={{ width: `${a}%`, backgroundColor: semColor.amarelo }} />}
                {vm > 0 && <div style={{ width: `${vm}%`, backgroundColor: semColor.vermelho }} />}
              </div>
              <div className="flex items-center gap-3 mt-1 text-[10px] font-mono">
                <Legend color={semColor.verde} label="conforme" val={v} />
                <Legend color={semColor.amarelo} label="alerta" val={a} />
                <Legend color={semColor.vermelho} label="violação" val={vm} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Legend({ color, label, val }: { color: string; label: string; val: number }) {
  return (
    <span className="flex items-center gap-1 text-muted-foreground uppercase tracking-[0.12em]">
      <span className="h-1.5 w-1.5" style={{ backgroundColor: color }} />
      {label} <span className="text-foreground tabular-nums">{val.toFixed(0)}%</span>
    </span>
  );
}
