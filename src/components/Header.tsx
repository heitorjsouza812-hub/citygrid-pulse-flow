import { Link, useRouterState } from "@tanstack/react-router";
import { Zap, Map, Brain, Presentation } from "lucide-react";
import { StatusWebSocket } from "./StatusWebSocket";
import { useCityGrid } from "@/lib/citygrid-context";
import { formatarHorarioSimulado } from "@/lib/citygrid-api";

export const BRAND_DESTINATION = "/mapa";
export const HEADER_LINKS = [
  { to: "/mapa", label: "Mapa", icon: Map },
  { to: "/decisoes", label: "Recomendações", icon: Brain },
  { to: "/apresentador", label: "Plateia", icon: Presentation },
] as const;

export const HEADER_NAV_CLASS =
  "flex items-center justify-between sm:justify-start gap-0 w-full sm:w-auto sm:ml-2 h-10 order-3 sm:order-none";

export function Header() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { stats, status, timestampSimulado } = useCityGrid();
  if (pathname.startsWith("/participar/")) return null;

  return (
    <header className="sticky top-0 z-40 bg-card border-b border-border">
      <div className="mx-auto max-w-[1600px] px-4 lg:px-6 min-h-12 py-1 flex items-center gap-3 flex-wrap">
        <Link to={BRAND_DESTINATION} className="flex items-center gap-2.5 mr-2">
          <div className="h-7 w-7 rounded-sm border border-border bg-surface flex items-center justify-center">
            <Zap className="h-3.5 w-3.5 text-primary" strokeWidth={2.25} />
          </div>
          <div className="leading-tight">
            <div className="font-display font-semibold text-[13px] tracking-tight text-foreground">
              CityGrid Brain
            </div>
            <div className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground font-mono">
              Demonstração científica · Dados sintéticos
            </div>
          </div>
        </Link>

        <nav className={HEADER_NAV_CLASS}>
          {HEADER_LINKS.map((l) => {
            const active = pathname.startsWith(l.to);
            return (
              <Link
                key={l.to}
                to={l.to}
                className="px-2 sm:px-3 h-10 flex-1 sm:flex-none justify-center text-[11px] font-display font-medium tracking-tight flex items-center gap-1.5 transition-colors border-b-2"
                style={{
                  color: active ? "var(--foreground)" : "var(--muted-foreground)",
                  borderColor: active ? "var(--primary)" : "transparent",
                }}
              >
                <l.icon className="h-3.5 w-3.5" /> {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-4 ml-auto">
          <div className="hidden md:flex items-center gap-4 text-[10px] font-mono text-muted-foreground">
            <span>
              CICLO <span className="text-foreground">#{stats.ciclo || "—"}</span>
            </span>
            <span className="tabular-nums text-foreground" title="Horário simulado">
              SIM {formatarHorarioSimulado(timestampSimulado)}
            </span>
          </div>
          <StatusWebSocket status={status} />
        </div>
      </div>
    </header>
  );
}
