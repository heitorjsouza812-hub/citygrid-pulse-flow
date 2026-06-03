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
    <header className="sticky top-0 z-40 backdrop-blur-xl border-b border-border" style={{ backgroundColor: "color-mix(in oklab, var(--background) 80%, transparent)" }}>
      <div className="mx-auto max-w-[1600px] px-4 lg:px-6 py-3 flex items-center gap-4 flex-wrap">
        <Link to="/" className="flex items-center gap-3 mr-2">
          <div className="relative h-9 w-9 rounded-lg flex items-center justify-center"
            style={{ background: "var(--gradient-accent)", boxShadow: "0 0 20px color-mix(in oklab, var(--cyan-elec) 50%, transparent)" }}>
            <Zap className="h-5 w-5 text-background" strokeWidth={2.5} />
          </div>
          <div className="leading-tight">
            <div className="font-display font-extrabold text-base tracking-tight">CityGrid <span className="gradient-text">Brain</span></div>
            <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground font-mono">Smart City Energy Monitor</div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          {links.map((l) => {
            const active = l.to === "/" ? pathname === "/" : pathname.startsWith(l.to);
            return (
              <Link
                key={l.to}
                to={l.to}
                className="px-3 py-1.5 rounded-md text-xs font-display font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors"
                style={{
                  color: active ? "var(--cyan-elec)" : "var(--muted-foreground)",
                  backgroundColor: active ? "color-mix(in oklab, var(--cyan-elec) 10%, transparent)" : "transparent",
                }}
              >
                <l.icon className="h-3.5 w-3.5" /> {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 ml-auto">
          <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            <span className="text-primary">CICLO</span>
            <span className="text-foreground font-bold">#{STATS_MOCK.ciclo}</span>
          </span>
          <span className="hidden sm:inline font-mono text-xs text-foreground tabular-nums" suppressHydrationWarning>
            {now ? now.toLocaleTimeString("pt-BR") : "--:--:--"}
          </span>
          <StatusWebSocket status="conectado" />
        </div>
      </div>
    </header>
  );
}
