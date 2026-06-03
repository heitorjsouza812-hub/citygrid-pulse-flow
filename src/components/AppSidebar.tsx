import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard, Map, Brain, Activity, Zap, Database,
  Settings, ShieldCheck, FileText, Radio, Server, GitBranch,
  ChevronsLeft, ChevronsRight, Building2, BatteryCharging,
} from "lucide-react";
import { useState, type ComponentType } from "react";

type Item = { to: string; label: string; icon: ComponentType<{ className?: string }>; badge?: string; tone?: "crit" | "warn" };

const groups: { label: string; items: Item[] }[] = [
  {
    label: "Operações",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard },
      { to: "/mapa", label: "Mapa da Rede", icon: Map },
      { to: "/decisoes", label: "Decisões IA", icon: Brain, badge: "10" },
    ],
  },
  {
    label: "Engenharia",
    items: [
      { to: "/", label: "Subestações", icon: Building2 },
      { to: "/", label: "Transformadores", icon: Server },
      { to: "/", label: "Alimentadores", icon: GitBranch },
      { to: "/", label: "BESS / Baterias", icon: BatteryCharging },
    ],
  },
  {
    label: "Análise",
    items: [
      { to: "/", label: "Telemetria", icon: Activity },
      { to: "/", label: "Qualidade ANEEL", icon: ShieldCheck, badge: "M8" },
      { to: "/", label: "Histórico", icon: Database },
      { to: "/", label: "Relatórios", icon: FileText },
    ],
  },
  {
    label: "Sistema",
    items: [
      { to: "/", label: "SCADA Gateway", icon: Radio },
      { to: "/", label: "Modelos ML", icon: Zap },
      { to: "/", label: "Configurações", icon: Settings },
    ],
  },
];

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const width = collapsed ? "w-12" : "w-56";

  return (
    <aside
      className={`${width} shrink-0 border-r border-border bg-card flex flex-col sticky top-0 h-screen transition-[width] duration-150 z-30`}
    >
      <div className="h-12 flex items-center justify-between px-3 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-2 min-w-0">
            <div className="h-6 w-6 rounded-sm border border-border bg-surface flex items-center justify-center">
              <Zap className="h-3 w-3 text-primary" strokeWidth={2.25} />
            </div>
            <div className="leading-tight min-w-0">
              <div className="text-[11px] font-display font-semibold tracking-tight text-foreground truncate">CityGrid Brain</div>
              <div className="text-[8px] uppercase tracking-[0.18em] text-muted-foreground font-mono">SCADA v4.2</div>
            </div>
          </div>
        )}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="h-6 w-6 rounded-sm border border-border bg-surface text-muted-foreground hover:text-foreground hover:border-primary/40 flex items-center justify-center transition-colors"
          aria-label={collapsed ? "Expandir" : "Recolher"}
        >
          {collapsed ? <ChevronsRight className="h-3 w-3" /> : <ChevronsLeft className="h-3 w-3" />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {groups.map((g) => (
          <div key={g.label} className="mb-3">
            {!collapsed && (
              <div className="px-3 py-1 text-[9px] uppercase tracking-[0.18em] text-muted-foreground font-mono">
                {g.label}
              </div>
            )}
            <ul>
              {g.items.map((it, idx) => {
                const active = it.to === "/" ? pathname === "/" && idx === 0 && g.label === "Operações"
                  : pathname.startsWith(it.to);
                return (
                  <li key={`${g.label}-${it.label}`}>
                    <Link
                      to={it.to}
                      className={`group flex items-center gap-2 px-3 h-7 text-[11px] font-display border-l-2 transition-colors ${
                        active
                          ? "text-foreground border-primary bg-surface/60"
                          : "text-muted-foreground border-transparent hover:text-foreground hover:bg-surface/40"
                      }`}
                      title={collapsed ? it.label : undefined}
                    >
                      <it.icon className="h-3.5 w-3.5 shrink-0" />
                      {!collapsed && <span className="truncate flex-1">{it.label}</span>}
                      {!collapsed && it.badge && (
                        <span
                          className="text-[9px] font-mono px-1 rounded-sm border"
                          style={{
                            color: it.tone === "crit" ? "var(--risk-crit)" : "var(--muted-foreground)",
                            borderColor: "var(--border)",
                            backgroundColor: "var(--surface)",
                          }}
                        >
                          {it.badge}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {!collapsed && (
        <div className="border-t border-border p-3 space-y-2">
          <div className="flex items-center justify-between text-[9px] font-mono text-muted-foreground uppercase tracking-[0.14em]">
            <span>Operador</span>
            <span className="text-foreground">OP-2381</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-sm border border-border bg-surface flex items-center justify-center text-[10px] font-mono font-semibold text-foreground">
              CM
            </div>
            <div className="leading-tight min-w-0">
              <div className="text-[11px] text-foreground truncate">Carlos R. Mendes</div>
              <div className="text-[9px] font-mono text-muted-foreground">Turno vespertino</div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
