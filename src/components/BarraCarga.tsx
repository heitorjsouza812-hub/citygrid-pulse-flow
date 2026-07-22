import { cargaColor } from "@/lib/risco";

export function BarraCarga({
  pct,
  capacidade,
  consumo,
}: {
  pct: number;
  capacidade: number;
  consumo: number;
}) {
  const color = cargaColor(pct);
  const clamped = Math.min(100, Math.max(0, pct));
  return (
    <div className="space-y-1">
      <div className="h-1.5 w-full rounded-sm bg-surface overflow-hidden border border-border">
        <div
          className="h-full transition-[width] duration-500 ease-out"
          style={{ width: `${clamped}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
        <span style={{ color }}>{pct.toFixed(1)}%</span>
        <span>
          {consumo.toFixed(2)} / {capacidade.toFixed(1)} MW
        </span>
      </div>
    </div>
  );
}
