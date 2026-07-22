import { Link } from "@tanstack/react-router";
import { AlertTriangle, CalendarClock, Zap, Battery, Car, ArrowUpRight } from "lucide-react";
import type { Zona } from "@/lib/citygrid-types";
import { RiscoBadge } from "./RiscoBadge";
import { BarraCarga } from "./BarraCarga";
import { SparklineConsumo } from "./SparklineConsumo";
import { riscoColor } from "@/lib/risco";

const perfilLabel: Record<string, string> = {
  residencial: "Residencial",
  comercial: "Comercial",
  industrial: "Industrial",
  misto: "Misto",
  hospitalar: "Hospitalar",
  turístico: "Turístico",
};

export function CardZona({ zona, compact = false }: { zona: Zona; compact?: boolean }) {
  const isCrit = zona.risco_atual === "CRÍTICO";
  const railColor = riscoColor(zona.risco_atual);

  return (
    <Link
      to="/zona/$id"
      params={{ id: zona.zona_id }}
      className={`card-surface group block p-3.5 pl-[13px] transition-colors hover:border-[color-mix(in_oklab,var(--primary)_45%,var(--border))] ${isCrit ? "animate-pulse-crit" : ""}`}
    >
      {/* Left risk rail */}
      <div className="absolute inset-y-0 left-0 w-[2px]" style={{ backgroundColor: railColor }} />

      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <h3 className="font-display font-semibold text-[14px] leading-tight truncate text-foreground">
            {zona.zona_nome}
          </h3>
          <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mt-1 font-mono">
            {perfilLabel[zona.perfil] ?? zona.perfil}
          </p>
        </div>
        <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5" />
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        <RiscoBadge risco={zona.risco_atual} label="Atual" />
        <RiscoBadge risco={zona.risco_xgb} label="XGB 30min" />
        <RiscoBadge risco={zona.risco_lstm} label="LSTM 30min" />
      </div>

      <BarraCarga pct={zona.pct_carga} capacidade={zona.capacidade_mw} consumo={zona.consumo_mw} />

      <div className="grid grid-cols-3 gap-1.5 mt-3">
        <Stat label="Consumo" val={zona.consumo_mw.toFixed(1)} unit="MW" />
        <Stat label="Renovável" val={(zona.geracao_total_mw * 1000).toFixed(0)} unit="kW" />
        <Stat
          label="Score XGB"
          val={zona.conf_xgb == null ? "—" : (zona.conf_xgb * 100).toFixed(0)}
          unit={zona.conf_xgb == null ? "" : "%"}
        />
      </div>

      <div className="mt-3 grid grid-cols-4 gap-1 text-[10px] font-mono text-muted-foreground border-t border-border/60 pt-2.5">
        <MiniData icon={<Zap className="h-3 w-3" />} val={zona.frequencia_hz.toFixed(2)} u="Hz" />
        <MiniData val={zona.fator_potencia.toFixed(3)} u="FP" />
        <MiniData val={zona.thd_tensao_pct.toFixed(1)} u="THD%" />
        <MiniData
          icon={<Car className="h-3 w-3" />}
          val={`${zona.ve_postos_em_uso}/${zona.ve_postos_total}`}
          u="VE"
        />
      </div>

      {!compact && (
        <div className="mt-3 flex items-end justify-between gap-2">
          <div className="min-w-0">
            <div className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground font-mono font-bold mb-1">
              Prev. 30min
            </div>
            <SparklineConsumo data={zona.previsao_mw} width={140} height={30} />
          </div>
          <div className="flex flex-col items-end gap-0.5 text-[10px] font-mono shrink-0">
            <span className="flex items-center gap-1 text-foreground">
              <Battery className="h-3 w-3 text-muted-foreground" /> {zona.bat_soc_pct.toFixed(0)}%
            </span>
            <span className="text-muted-foreground text-[9px] uppercase tracking-wider">
              {zona.bat_modo}
            </span>
          </div>
        </div>
      )}

      {(zona.anomalia_tipo || zona.evento) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {zona.anomalia_tipo && (
            <span
              className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-mono uppercase tracking-wide"
              style={{
                color: "var(--risk-crit)",
                backgroundColor: "color-mix(in oklab, var(--risk-crit) 12%, transparent)",
                border: "1px solid color-mix(in oklab, var(--risk-crit) 35%, transparent)",
              }}
            >
              <AlertTriangle className="h-3 w-3" /> {zona.anomalia_tipo.replace(/_/g, " ")}
            </span>
          )}
          {zona.evento && (
            <span
              className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-mono uppercase tracking-wide"
              style={{
                color: "var(--purple-elec)",
                backgroundColor: "color-mix(in oklab, var(--purple-elec) 12%, transparent)",
                border: "1px solid color-mix(in oklab, var(--purple-elec) 35%, transparent)",
              }}
            >
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
    <div className="rounded-md border border-border/60 bg-surface/30 py-1.5 px-2">
      <div className="text-[8px] uppercase tracking-[0.18em] text-muted-foreground font-mono">
        {label}
      </div>
      <div className="font-mono text-sm font-bold text-foreground tabular-nums leading-tight mt-0.5">
        {val}
        <span className="text-[10px] text-muted-foreground ml-0.5 font-normal">{unit}</span>
      </div>
    </div>
  );
}
function MiniData({ icon, val, u }: { icon?: React.ReactNode; val: string; u: string }) {
  return (
    <span className="flex items-center justify-center gap-1 truncate tabular-nums">
      {icon}
      <span className="text-foreground">{val}</span>
      <span className="opacity-70">{u}</span>
    </span>
  );
}
