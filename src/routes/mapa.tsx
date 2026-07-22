import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { X, Layers, MapPin, Zap, ThermometerSun, Activity } from "lucide-react";
import { useCityGrid } from "@/lib/citygrid-context";
import type { Zona } from "@/lib/citygrid-types";
import { riscoColor } from "@/lib/risco";
import { RiscoBadge } from "@/components/RiscoBadge";
import { BarraCarga } from "@/components/BarraCarga";

export const Route = createFileRoute("/mapa")({
  head: () => ({
    meta: [
      { title: "Mapa da Cidade — CityGrid Brain" },
      {
        name: "description",
        content: "Visualização geoespacial das 8 zonas urbanas monitoradas em tempo real.",
      },
    ],
  }),
  component: MapaPage,
});

type Layer = "risco" | "consumo" | "renovavel" | "anomalias";

function MapaPage() {
  const { zonas } = useCityGrid();
  const [sel, setSel] = useState<Zona | null>(null);
  const [layer, setLayer] = useState<Layer>("risco");

  const maxConsumo = Math.max(1, ...zonas.map((z) => z.consumo_mw));

  const colorFor = (z: Zona): string => {
    switch (layer) {
      case "consumo":
        return z.pct_carga >= 80
          ? "var(--risk-crit)"
          : z.pct_carga >= 60
            ? "var(--risk-high)"
            : z.pct_carga >= 40
              ? "var(--risk-med)"
              : "var(--risk-low)";
      case "renovavel":
        return z.geracao_total_mw > 2
          ? "var(--risk-low)"
          : z.geracao_total_mw > 0.8
            ? "var(--risk-med)"
            : "var(--muted-foreground)";
      case "anomalias":
        return z.anomalia_tipo ? "var(--risk-crit)" : "var(--muted-foreground)";
      default:
        return riscoColor(z.risco_atual);
    }
  };

  const sizeFor = (z: Zona) => 18 + (z.consumo_mw / maxConsumo) * 38;

  return (
    <main className="mx-auto max-w-[1600px] px-4 lg:px-6 py-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-extrabold text-2xl">Mapa da Cidade</h1>
          <p className="text-xs text-muted-foreground">
            Topologia simplificada das zonas monitoradas
          </p>
        </div>
        <LayerControls layer={layer} onChange={setLayer} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
        {/* Mapa */}
        <div className="card-surface relative overflow-hidden" style={{ minHeight: "560px" }}>
          <div
            className="absolute inset-x-0 top-0 h-px"
            style={{ background: "var(--gradient-accent)" }}
          />
          <div className="absolute inset-0 grid-bg" />
          {/* malha viária estilizada */}
          <svg
            className="absolute inset-0 w-full h-full"
            preserveAspectRatio="none"
            viewBox="0 0 100 100"
          >
            <path d="M0,30 L100,32" stroke="var(--border)" strokeWidth="0.3" />
            <path d="M0,55 L100,53" stroke="var(--border)" strokeWidth="0.3" />
            <path d="M0,75 L100,78" stroke="var(--border)" strokeWidth="0.3" />
            <path d="M25,0 L23,100" stroke="var(--border)" strokeWidth="0.3" />
            <path d="M50,0 L52,100" stroke="var(--border)" strokeWidth="0.3" />
            <path d="M78,0 L80,100" stroke="var(--border)" strokeWidth="0.3" />
            <path
              d="M10,10 Q50,40 90,15 T95,90"
              stroke="color-mix(in oklab, var(--cyan-elec) 18%, transparent)"
              strokeWidth="0.4"
              fill="none"
              strokeDasharray="1,1"
            />
          </svg>

          {/* Zonas */}
          <div className="relative w-full h-full" style={{ minHeight: "560px" }}>
            {zonas.map((z) => {
              const color = colorFor(z);
              const size = sizeFor(z);
              const isCrit = z.risco_atual === "CRÍTICO";
              return (
                <button
                  key={z.zona_id}
                  onClick={() => setSel(z)}
                  className="absolute -translate-x-1/2 -translate-y-1/2 group"
                  style={{ left: `${z.lng}%`, top: `${z.lat}%` }}
                  title={`${z.zona_nome} • ${z.consumo_mw.toFixed(1)} MW • ${z.pct_carga.toFixed(1)}% • atual ${z.risco_atual} • ${z.clima_temp_c.toFixed(1)}°C`}
                >
                  <span
                    className={`block rounded-full transition-transform group-hover:scale-110 ${isCrit ? "animate-pulse-crit" : ""}`}
                    style={{
                      width: size,
                      height: size,
                      backgroundColor: `color-mix(in oklab, ${color} 30%, transparent)`,
                      border: `2px solid ${color}`,
                      boxShadow: `0 0 ${size * 0.6}px color-mix(in oklab, ${color} 60%, transparent)`,
                    }}
                  />
                  <span className="absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap text-[10px] font-mono font-bold text-foreground bg-card/80 backdrop-blur px-1.5 py-0.5 rounded border border-border">
                    {z.zona_nome}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Legenda */}
          <div className="absolute bottom-3 left-3 card-surface p-3 text-[10px] font-mono space-y-1">
            <div className="uppercase tracking-wider text-muted-foreground font-display font-bold mb-1">
              Legenda
            </div>
            {(["BAIXO", "MÉDIO", "ALTO", "CRÍTICO"] as const).map((r) => (
              <div key={r} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: riscoColor(r), boxShadow: `0 0 6px ${riscoColor(r)}` }}
                />
                <span>{r}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Panel lateral */}
        <aside className="space-y-3">
          {sel ? (
            <ZonaPanel zona={sel} onClose={() => setSel(null)} />
          ) : (
            <div className="card-surface p-5 text-center">
              <MapPin className="h-8 w-8 mx-auto mb-2 text-primary" />
              <h3 className="font-display font-bold text-base mb-1">Selecione uma zona</h3>
              <p className="text-xs text-muted-foreground">
                Clique em um marcador para ver detalhes completos, qualidade elétrica e ações da IA.
              </p>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}

function LayerControls({ layer, onChange }: { layer: Layer; onChange: (l: Layer) => void }) {
  const opts: { id: Layer; label: string }[] = [
    { id: "risco", label: "Risco" },
    { id: "consumo", label: "Consumo" },
    { id: "renovavel", label: "Renovável" },
    { id: "anomalias", label: "Anomalias" },
  ];
  return (
    <div className="card-surface p-1 flex items-center gap-1">
      <Layers className="h-3.5 w-3.5 text-muted-foreground mx-1.5" />
      {opts.map((o) => (
        <button
          key={o.id}
          onClick={() => onChange(o.id)}
          className="px-3 py-1.5 rounded text-[10px] font-mono uppercase tracking-wider font-bold transition-colors"
          style={{
            color: layer === o.id ? "var(--cyan-elec)" : "var(--muted-foreground)",
            backgroundColor:
              layer === o.id
                ? "color-mix(in oklab, var(--cyan-elec) 12%, transparent)"
                : "transparent",
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function ZonaPanel({ zona, onClose }: { zona: Zona; onClose: () => void }) {
  return (
    <div className="card-surface p-4 animate-slide-in-up">
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{ background: "var(--gradient-accent)" }}
      />
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <h3 className="font-display font-extrabold text-lg leading-tight">{zona.zona_nome}</h3>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
            {zona.perfil}
          </p>
        </div>
        <button onClick={onClose} className="p-1 rounded hover:bg-surface">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        <RiscoBadge risco={zona.risco_atual} label="Atual" />
        <RiscoBadge risco={zona.risco_xgb} label="XGB analítico 30min" />
        <RiscoBadge risco={zona.risco_lstm} label="LSTM 30min" />
      </div>

      <BarraCarga pct={zona.pct_carga} capacidade={zona.capacidade_mw} consumo={zona.consumo_mw} />

      <div className="grid grid-cols-2 gap-2 mt-4 text-xs font-mono">
        <Row label="Frequência" val={`${zona.frequencia_hz.toFixed(2)} Hz`} />
        <Row label="Tensão" val={`${zona.tensao_media_v.toFixed(1)} V`} />
        <Row label="THD" val={`${zona.thd_tensao_pct.toFixed(1)}%`} />
        <Row label="Fator Pot." val={zona.fator_potencia.toFixed(3)} />
        <Row label="Bateria" val={`${zona.bat_soc_pct.toFixed(0)}% ${zona.bat_modo}`} />
        <Row label="VEs em uso" val={`${zona.ve_postos_em_uso}/${zona.ve_postos_total}`} />
        <Row label="Solar" val={`${zona.solar_mw.toFixed(2)} MW`} />
        <Row label="Eólica" val={`${zona.eolica_mw.toFixed(2)} MW`} />
      </div>

      <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground font-mono">
        <ThermometerSun className="h-3.5 w-3.5" /> {zona.clima_temp_c.toFixed(1)}°C local
      </div>

      <Link
        to="/zona/$id"
        params={{ id: zona.zona_id }}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-xs font-display font-bold uppercase tracking-wider text-primary hover:shadow-[var(--shadow-glow-cyan)] transition"
      >
        <Activity className="h-3.5 w-3.5" /> Análise completa
      </Link>
    </div>
  );
}

function Row({ label, val }: { label: string; val: string }) {
  return (
    <div className="flex flex-col rounded border border-border bg-surface/40 p-2">
      <span className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className="text-foreground font-bold">{val}</span>
    </div>
  );
}
