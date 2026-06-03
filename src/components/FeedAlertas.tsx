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
    <div className="overflow-y-auto pr-1 space-y-2" style={{ maxHeight }}>
      {alertas.map((a) => {
        const color = urgenciaColor(a.urgencia);
        return (
          <div
            key={a.id}
            className="animate-slide-in-up rounded-md border border-border bg-surface/40 p-2.5"
            style={{ borderLeft: `3px solid ${color}` }}
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-[10px] font-mono uppercase tracking-wider font-bold" style={{ color }}>
                  {a.urgencia}
                </span>
                <span className="text-[10px] text-muted-foreground truncate">• {a.zona_nome}</span>
              </div>
              <span className="text-[10px] font-mono text-muted-foreground shrink-0">{timeAgo(a.ts)}</span>
            </div>
            <div className="text-xs font-display font-bold text-foreground">{a.tipo}</div>
            <div className="text-[11px] text-muted-foreground mt-0.5">{a.descricao}</div>
            <div className="flex items-center justify-between mt-1.5 text-[10px] font-mono text-muted-foreground">
              <span className="inline-flex items-center gap-1 uppercase tracking-wider">
                {origemIcon[a.origem]} {a.origem}
              </span>
              <span>conf {(a.confianca * 100).toFixed(0)}%</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
