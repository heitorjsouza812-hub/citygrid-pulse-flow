import { Link } from "@tanstack/react-router";
import { AlertTriangle, CalendarClock, Cpu, Zap, Battery, Car } from "lucide-react";
import type { Zona } from "@/lib/mock-data";
import { RiscoBadge } from "./RiscoBadge";
import { BarraCarga } from "./BarraCarga";
import { SparklineConsumo } from "./SparklineConsumo";

const perfilLabel: Record<string, string> = {
  residencial: "Residencial",
  comercial: "Comercial",
  industrial: "Industrial",
  misto: "Misto",
  hospitalar: "Hospitalar",
  turístico: "Turístico",
};

export function CardZona({ zona, compact = false }: { zona: Zona; compact?: boolean }) {
  const isCrit = zona.risco_xgb === "CRÍTICO";
  return (
    <Link
      to="/zona/$id"
      params={{ id: zona.zona_id }}
      className={`card-surface group block p-4 transition-all duration-200 hover:-translate-y-0.5 ${isCrit ? "animate-pulse-crit" : "hover:shadow-[var(--shadow-glow-cyan)]"}`}
      style={isCrit ? { backgroundColor: "color-mix(in oklab, var(--risk-crit) 6%, var(--card))" } : undefined}
    >
      {/* top gradient line */}
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{ background: isCrit ? "var(--risk-crit)" : "var(--gradient-accent)" }}
      />

      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <h3 className="font-display font-bold text-base leading-tight truncate">{zona.zona_nome}</h3>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
            {perfilLabel[zona.perfil] ?? zona.perfil}
          </p>
        </div>
        <Zap className="h-4 w-4 text-primary opacity-70 shrink-0" />
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        <RiscoBadge risco={zona.risco_xgb} />
        <RiscoBadge risco={zona.risco_lstm} prev />
      </div>

      <BarraCarga pct={zona.pct_carga} capacidade={zona.capacidade_mw} consumo={zona.consumo_mw} />

      <div className="grid grid-cols-3 gap-2 mt-3 text-center">
        <Stat label="Consumo" val={zona.consumo_mw.toFixed(1)} unit="MW" />
        <Stat label="Renovável" val={(zona.geracao_total_mw * 1000).toFixed(0)} unit="kW" />
        <Stat label="Conf. IA" val={(zona.conf_xgb * 100).toFixed(0)} unit="%" />
      </div>

      <div className="mt-3 grid grid-cols-4 gap-1 text-[10px] font-mono text-muted-foreground border-t border-border pt-2">
        <MiniData icon={<Zap className="h-3 w-3" />} val={zona.frequencia_hz.toFixed(2)} u="Hz" />
        <MiniData val={zona.fator_potencia.toFixed(3)} u="FP" />
        <MiniData val={zona.thd_tensao_pct.toFixed(1)} u="THD%" />
        <MiniData icon={<Car className="h-3 w-3" />} val={`${zona.ve_postos_em_uso}/${zona.ve_postos_total}`} u="VE" />
      </div>

      {!compact && (
        <div className="mt-3 flex items-end justify-between gap-2">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-display font-bold mb-0.5">Prev. 30min</div>
            <SparklineConsumo data={zona.previsao_mw} width={140} height={30} />
          </div>
          <div className="flex flex-col items-end gap-1 text-[10px] font-mono">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Battery className="h-3 w-3" /> {zona.bat_soc_pct.toFixed(0)}%
            </span>
            <span className="text-muted-foreground">{zona.bat_modo}</span>
          </div>
        </div>
      )}

      {(zona.anomalia_tipo || zona.evento) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {zona.anomalia_tipo && (
            <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-mono uppercase tracking-wide"
              style={{
                color: "var(--risk-crit)",
                backgroundColor: "color-mix(in oklab, var(--risk-crit) 12%, transparent)",
                border: "1px solid color-mix(in oklab, var(--risk-crit) 35%, transparent)",
              }}>
              <AlertTriangle className="h-3 w-3" /> {zona.anomalia_tipo.replace(/_/g, " ")}
            </span>
          )}
          {zona.evento && (
            <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-mono uppercase tracking-wide"
              style={{
                color: "var(--purple-elec)",
                backgroundColor: "color-mix(in oklab, var(--purple-elec) 12%, transparent)",
                border: "1px solid color-mix(in oklab, var(--purple-elec) 35%, transparent)",
              }}>
              <CalendarClock className="h-3 w-3" /> {zona.evento}
            </span>
          )}
        </div>
      )}
    </Link>
  );
}

function Stat({ label, val, unit }: { label: string; val: string; unit: string }) {
  return (
    <div className="rounded-md border border-border bg-surface/40 py-1.5 px-1">
      <div className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-mono text-sm font-bold text-foreground">
        {val}<span className="text-[10px] text-muted-foreground ml-0.5">{unit}</span>
      </div>
    </div>
  );
}
function MiniData({ icon, val, u }: { icon?: React.ReactNode; val: string; u: string }) {
  return (
    <span className="flex items-center justify-center gap-1 truncate">
      {icon}
      <span className="text-foreground">{val}</span>
      <span>{u}</span>
    </span>
  );
}
