import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Zap, Map, LayoutDashboard, Brain } from "lucide-react";
import { StatusWebSocket } from "./StatusWebSocket";
import { STATS_MOCK } from "@/lib/mock-data";

export function Header() {
  const [now, setNow] = useState<Date | null>(null);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const links = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
    { to: "/mapa", label: "Mapa", icon: Map },
    { to: "/decisoes", label: "Decisões IA", icon: Brain },
  ] as const;

  return (
    <header
      className="sticky top-0 z-40 backdrop-blur-xl border-b border-border"
      style={{ backgroundColor: "color-mix(in oklab, var(--background) 82%, transparent)" }}
    >
      {/* hairline accent */}
      <div className="absolute inset-x-0 bottom-0 h-px opacity-60" style={{ background: "var(--gradient-accent)" }} />

      <div className="mx-auto max-w-[1600px] px-4 lg:px-6 py-3 flex items-center gap-4 flex-wrap">
        <Link to="/" className="flex items-center gap-2.5 mr-2 group">
          <div
            className="relative h-9 w-9 rounded-lg flex items-center justify-center transition-transform group-hover:scale-105"
            style={{ background: "var(--gradient-accent)", boxShadow: "0 0 24px color-mix(in oklab, var(--cyan-elec) 45%, transparent)" }}
          >
            <Zap className="h-5 w-5 text-background" strokeWidth={2.75} />
          </div>
          <div className="leading-tight">
            <div className="font-display font-extrabold text-[15px] tracking-tight uppercase">
              CityGrid <span className="gradient-text">Brain</span>
            </div>
            <div className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground font-mono">
              Utility OS · v4.2
            </div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-1 ml-2">
          {links.map((l) => {
            const active = l.to === "/" ? pathname === "/" : pathname.startsWith(l.to);
            return (
              <Link
                key={l.to}
                to={l.to}
                className="px-3 py-1.5 rounded-md text-[11px] font-display font-bold uppercase tracking-[0.12em] flex items-center gap-1.5 transition-colors"
                style={{
                  color: active ? "var(--cyan-elec)" : "var(--muted-foreground)",
                  backgroundColor: active ? "color-mix(in oklab, var(--cyan-elec) 10%, transparent)" : "transparent",
                  border: active ? "1px solid color-mix(in oklab, var(--cyan-elec) 25%, transparent)" : "1px solid transparent",
                }}
              >
                <l.icon className="h-3.5 w-3.5" /> {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 ml-auto">
          <div className="hidden md:flex flex-col items-end leading-tight">
            <span className="text-[9px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
              Ciclo <span className="text-foreground font-bold">#{STATS_MOCK.ciclo}</span>
            </span>
            <span className="font-mono text-[11px] text-foreground tabular-nums" suppressHydrationWarning>
              {now ? now.toLocaleTimeString("pt-BR") : "--:--:--"}
            </span>
          </div>
          <StatusWebSocket status="conectado" />
        </div>
      </div>
    </header>
  );
}
