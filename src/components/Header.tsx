import { useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Search, Bell } from "lucide-react";
import { StatusWebSocket } from "./StatusWebSocket";
import { STATS_MOCK } from "@/lib/mock-data";

const routeLabels: Record<string, string> = {
  "/": "Dashboard",
  "/mapa": "Mapa da Rede",
  "/decisoes": "Decisões IA",
};

export function Header() {
  const [now, setNow] = useState<Date | null>(null);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const crumb = pathname.startsWith("/zona")
    ? "Análise de Zona"
    : routeLabels[pathname] ?? "Operações";

  return (
    <header className="sticky top-0 z-20 bg-card border-b border-border h-11 flex items-center px-4 lg:px-6 gap-4">
      <div className="flex items-center gap-2 text-[11px] font-mono">
        <span className="text-muted-foreground uppercase tracking-[0.14em]">COS</span>
        <span className="text-muted-foreground">/</span>
        <span className="text-foreground">{crumb}</span>
      </div>

      <div className="hidden md:flex items-center gap-2 ml-4 flex-1 max-w-md">
        <div className="flex items-center gap-2 w-full h-7 px-2.5 rounded-sm border border-border bg-surface/60 text-[11px] text-muted-foreground">
          <Search className="h-3.5 w-3.5" />
          <input
            type="text"
            placeholder="Buscar zona, subestação, transformador, alimentador…"
            className="bg-transparent flex-1 outline-none placeholder:text-muted-foreground text-foreground"
          />
          <span className="text-[9px] font-mono px-1 rounded-sm border border-border bg-card">⌘K</span>
        </div>
      </div>

      <div className="flex items-center gap-3 ml-auto">
        <button
          className="relative h-7 w-7 rounded-sm border border-border bg-surface/60 text-muted-foreground hover:text-foreground flex items-center justify-center"
          aria-label="Notificações"
        >
          <Bell className="h-3.5 w-3.5" />
          <span
            className="absolute -top-1 -right-1 h-3 min-w-3 px-0.5 rounded-full text-[9px] font-mono font-semibold flex items-center justify-center"
            style={{ backgroundColor: "var(--risk-crit)", color: "var(--background)" }}
          >
            3
          </span>
        </button>
        <div className="hidden md:flex items-center gap-3 text-[10px] font-mono text-muted-foreground">
          <span>CICLO <span className="text-foreground tabular-nums">#{STATS_MOCK.ciclo}</span></span>
          <span className="tabular-nums text-foreground" suppressHydrationWarning>
            {now ? now.toLocaleTimeString("pt-BR") : "--:--:--"}
          </span>
        </div>
        <StatusWebSocket status="conectado" />
      </div>
    </header>
  );
}
