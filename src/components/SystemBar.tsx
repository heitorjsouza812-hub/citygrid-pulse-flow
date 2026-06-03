import { Activity, Database, Radio, Wifi, GitBranch, Globe2 } from "lucide-react";

export function SystemBar() {
  const items = [
    { icon: <Globe2 className="h-3 w-3" />, label: "REGIÃO", val: "BR-SE-1" },
    { icon: <GitBranch className="h-3 w-3" />, label: "BUILD", val: "4.2.0-stable" },
    { icon: <Radio className="h-3 w-3" />, label: "GATEWAY", val: "scada-01.cos" },
    { icon: <Wifi className="h-3 w-3" />, label: "LAT", val: "12 ms" },
    { icon: <Activity className="h-3 w-3" />, label: "TPS", val: "4.812" },
    { icon: <Database className="h-3 w-3" />, label: "RETENÇÃO", val: "365 d" },
  ];
  return (
    <div className="h-7 border-b border-border bg-card flex items-center px-3 gap-5 text-[10px] font-mono text-muted-foreground overflow-x-auto">
      <span className="flex items-center gap-1.5">
        <span
          className="h-1.5 w-1.5 rounded-full animate-pulse-dot"
          style={{ backgroundColor: "var(--risk-low)" }}
        />
        <span className="uppercase tracking-[0.14em] text-foreground">Operacional</span>
      </span>
      {items.map((i) => (
        <span key={i.label} className="flex items-center gap-1.5 shrink-0">
          {i.icon}
          <span className="uppercase tracking-[0.14em]">{i.label}</span>
          <span className="text-foreground tabular-nums">{i.val}</span>
        </span>
      ))}
      <span className="ml-auto shrink-0 uppercase tracking-[0.14em]">
        ANEEL · PRODIST · MÓDULO 8 · CONFORME
      </span>
    </div>
  );
}
