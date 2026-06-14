import { urgenciaColor } from "@/lib/risco";
import type { Alerta } from "@/lib/mock-data";
import { Cpu, Brain, Zap, Dna } from "lucide-react";

const origemIcon: Record<string, React.ReactNode> = {
  heuristica: <Zap className="h-3 w-3" />,
  xgboost: <Cpu className="h-3 w-3" />,
  lstm: <Brain className="h-3 w-3" />,
  genetico: <Dna className="h-3 w-3" />,
};

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 60_000;
  if (diff < 1) return "agora";
  if (diff < 60) return `${Math.floor(diff)}m atrás`;
  return `${Math.floor(diff / 60)}h atrás`;
}

export function FeedAlertas({ alertas, maxHeight = "32rem" }: { alertas: Alerta[]; maxHeight?: string }) {
  return (
    <div className="overflow-y-auto pr-1 -mr-1" style={{ maxHeight }}>
      <div className="divide-y divide-border/60 rounded-md overflow-hidden border border-border/60 bg-surface/20">
        {alertas.map((a) => {
          const color = urgenciaColor(a.urgencia);
          return (
            <div
              key={a.id}
              className="animate-slide-in-up p-3 hover:bg-surface/50 transition-colors relative"
              style={{ boxShadow: `inset 3px 0 0 0 ${color}` }}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="text-[9px] font-mono uppercase tracking-[0.15em] font-bold px-1.5 py-0.5 rounded"
                    style={{
                      color,
                      backgroundColor: `color-mix(in oklab, ${color} 14%, transparent)`,
                    }}
                  >
                    {a.urgencia}
                  </span>
                  <span className="text-[10px] text-muted-foreground truncate font-mono">{a.zona_nome}</span>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground shrink-0 tabular-nums">{timeAgo(a.ts)}</span>
              </div>
              <div className="text-[13px] font-display font-bold text-foreground leading-tight">{a.tipo}</div>
              <div className="text-[11px] text-muted-foreground mt-0.5">{a.descricao}</div>
              <div className="flex items-center justify-between mt-2 text-[10px] font-mono">
                <span className="inline-flex items-center gap-1 uppercase tracking-[0.15em] text-muted-foreground">
                  {origemIcon[a.origem]} {a.origem}
                </span>
                <span
                  className="px-1.5 py-0.5 rounded tabular-nums"
                  style={{
                    color: "var(--risk-low)",
                    backgroundColor: "color-mix(in oklab, var(--risk-low) 10%, transparent)",
                  }}
                >
                  conf {(a.confianca * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
