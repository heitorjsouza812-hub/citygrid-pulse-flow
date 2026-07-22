import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { Download, Brain, Cpu, Zap, Dna } from "lucide-react";
import { useCityGrid } from "@/lib/citygrid-context";
import type { Recomendacao } from "@/lib/citygrid-types";
import { urgenciaColor } from "@/lib/risco";

export const Route = createFileRoute("/decisoes")({
  head: () => ({
    meta: [
      { title: "Recomendações Simuladas — CityGrid Brain" },
      {
        name: "description",
        content:
          "Histórico das recomendações geradas pelo motor experimental; nenhuma ação é executada em rede real.",
      },
    ],
  }),
  component: DecisoesPage,
});

const ORIGEM_COLOR: Record<string, string> = {
  heuristica: "var(--cyan-elec)",
  xgboost: "var(--risk-med)",
  lstm: "var(--purple-elec)",
  genetico: "var(--risk-low)",
};

function DecisoesPage() {
  const { recomendacoes, zonas } = useCityGrid();
  const [fUrg, setFUrg] = useState<string>("todos");
  const [fOri, setFOri] = useState<string>("todos");
  const [fZona, setFZona] = useState<string>("todos");

  const filtrados = useMemo(
    () =>
      recomendacoes.filter(
        (a) =>
          (fUrg === "todos" || a.urgencia === fUrg) &&
          (fOri === "todos" || a.origem === fOri) &&
          (fZona === "todos" || a.zona_id === fZona),
      ),
    [recomendacoes, fUrg, fOri, fZona],
  );

  const porOrigem = useMemo(() => {
    const m: Record<string, number> = { heuristica: 0, xgboost: 0, lstm: 0, genetico: 0 };
    recomendacoes.forEach((a) => {
      m[a.origem]++;
    });
    return Object.entries(m).map(([name, value]) => ({ name, value }));
  }, [recomendacoes]);

  const porZona = useMemo(() => {
    const m: Record<string, number> = {};
    recomendacoes.forEach((a) => {
      m[a.zona_nome] = (m[a.zona_nome] || 0) + 1;
    });
    return Object.entries(m)
      .map(([zona, count]) => ({ zona, count }))
      .sort((a, b) => b.count - a.count);
  }, [recomendacoes]);

  function exportCSV() {
    const headers = [
      "timestamp",
      "zona",
      "tipo",
      "urgencia",
      "origem",
      "descricao",
      "score_modelo",
    ];
    const rows = filtrados.map((a) =>
      [a.ts, a.zona_nome, a.tipo, a.urgencia, a.origem, a.descricao, a.score ?? "não_calibrado"]
        .map((campo) => `"${String(campo).replaceAll('"', '""')}"`)
        .join(","),
    );
    const blob = new Blob([headers.join(",") + "\n" + rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `decisoes-ia-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="mx-auto max-w-[1600px] px-4 lg:px-6 py-6 space-y-6">
      <div>
        <h1 className="font-display font-extrabold text-3xl">Recomendações da Simulação</h1>
        <p className="text-sm text-muted-foreground">
          Sugestões geradas em simulação. Elas não são comandos executados nem comprovam economia de
          energia.
        </p>
      </div>

      {/* Stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={<Zap className="h-4 w-4" />}
          label="Heurística"
          valor={porOrigem.find((p) => p.name === "heuristica")?.value ?? 0}
          color="var(--cyan-elec)"
        />
        <StatCard
          icon={<Cpu className="h-4 w-4" />}
          label="XGBoost"
          valor={porOrigem.find((p) => p.name === "xgboost")?.value ?? 0}
          color="var(--risk-med)"
        />
        <StatCard
          icon={<Brain className="h-4 w-4" />}
          label="LSTM"
          valor={porOrigem.find((p) => p.name === "lstm")?.value ?? 0}
          color="var(--purple-elec)"
        />
        <StatCard
          icon={<Dna className="h-4 w-4" />}
          label="Genético"
          valor={porOrigem.find((p) => p.name === "genetico")?.value ?? 0}
          color="var(--risk-low)"
        />
      </section>

      {/* Gráficos */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card-surface p-4">
          <div
            className="absolute inset-x-0 top-0 h-px"
            style={{ background: "var(--gradient-accent)" }}
          />
          <h3 className="font-display font-bold text-sm mb-3">Distribuição por Origem</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={porOrigem}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={90}
                innerRadius={50}
                strokeWidth={2}
                stroke="var(--card)"
              >
                {porOrigem.map((e) => (
                  <Cell key={e.name} fill={ORIGEM_COLOR[e.name]} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card-surface p-4">
          <div
            className="absolute inset-x-0 top-0 h-px"
            style={{ background: "var(--gradient-accent)" }}
          />
          <h3 className="font-display font-bold text-sm mb-3">Zonas com mais intervenções</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={porZona} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                type="number"
                stroke="var(--muted-foreground)"
                tick={{ fontSize: 10, fontFamily: "Space Mono" }}
              />
              <YAxis
                type="category"
                dataKey="zona"
                stroke="var(--muted-foreground)"
                tick={{ fontSize: 10, fontFamily: "Space Mono" }}
                width={140}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ fill: "color-mix(in oklab, var(--cyan-elec) 6%, transparent)" }}
              />
              <Bar dataKey="count" fill="var(--cyan-elec)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Filtros + tabela */}
      <section className="card-surface p-4">
        <div
          className="absolute inset-x-0 top-0 h-px"
          style={{ background: "var(--gradient-accent)" }}
        />
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <Filtro
            label="Urgência"
            value={fUrg}
            onChange={setFUrg}
            options={[
              { v: "todos", l: "Todas" },
              { v: "info", l: "Info" },
              { v: "atencao", l: "Atenção" },
              { v: "alto", l: "Alto" },
              { v: "critico", l: "Crítico" },
            ]}
          />
          <Filtro
            label="Origem"
            value={fOri}
            onChange={setFOri}
            options={[
              { v: "todos", l: "Todas" },
              { v: "heuristica", l: "Heurística" },
              { v: "xgboost", l: "XGBoost" },
              { v: "lstm", l: "LSTM" },
              { v: "genetico", l: "Genético" },
            ]}
          />
          <Filtro
            label="Zona"
            value={fZona}
            onChange={setFZona}
            options={[
              { v: "todos", l: "Todas" },
              ...zonas.map((z) => ({ v: z.zona_id, l: z.zona_nome })),
            ]}
          />
          <button
            onClick={exportCSV}
            className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-xs font-display font-bold uppercase tracking-wider text-primary hover:shadow-[var(--shadow-glow-cyan)] transition"
          >
            <Download className="h-3.5 w-3.5" /> Export CSV
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border">
                <th className="text-left py-2 px-2 font-display">Timestamp</th>
                <th className="text-left py-2 px-2 font-display">Zona</th>
                <th className="text-left py-2 px-2 font-display">Tipo</th>
                <th className="text-left py-2 px-2 font-display">Urgência</th>
                <th className="text-left py-2 px-2 font-display">Origem</th>
                <th className="text-left py-2 px-2 font-display">Descrição</th>
                <th className="text-right py-2 px-2 font-display">Score</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {filtrados.map((a) => (
                <Row key={a.id} a={a} />
              ))}
              {filtrados.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-muted-foreground">
                    Nenhuma decisão com os filtros atuais.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function Row({ a }: { a: Recomendacao }) {
  const color = urgenciaColor(a.urgencia);
  return (
    <tr className="border-b border-border/50 hover:bg-surface/40">
      <td className="py-2 px-2 text-muted-foreground whitespace-nowrap">
        {new Date(a.ts).toLocaleTimeString("pt-BR")}
      </td>
      <td className="py-2 px-2">{a.zona_nome}</td>
      <td className="py-2 px-2 font-bold">{a.tipo}</td>
      <td className="py-2 px-2">
        <span
          className="inline-flex rounded px-1.5 py-0.5 text-[10px] uppercase font-bold"
          style={{ color, backgroundColor: `color-mix(in oklab, ${color} 14%, transparent)` }}
        >
          {a.urgencia}
        </span>
      </td>
      <td className="py-2 px-2 uppercase text-[10px]" style={{ color: ORIGEM_COLOR[a.origem] }}>
        {a.origem}
      </td>
      <td className="py-2 px-2 text-muted-foreground max-w-md truncate">{a.descricao}</td>
      <td className="py-2 px-2 text-right">
        {a.score == null ? "não calibrado" : `${(a.score * 100).toFixed(0)}%`}
      </td>
    </tr>
  );
}

function Filtro({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { v: string; l: string }[];
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-display font-bold">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:border-primary"
      >
        {options.map((o) => (
          <option key={o.v} value={o.v}>
            {o.l}
          </option>
        ))}
      </select>
    </label>
  );
}

function StatCard({
  icon,
  label,
  valor,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  valor: number;
  color: string;
}) {
  return (
    <div className="card-surface p-4">
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{ background: "var(--gradient-accent)" }}
      />
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-display font-bold">
          {label}
        </span>
        <span style={{ color }}>{icon}</span>
      </div>
      <div className="font-mono text-3xl font-bold" style={{ color }}>
        {valor}
      </div>
      <div className="text-[11px] text-muted-foreground mt-1">recomendações registradas</div>
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontFamily: "Space Mono, monospace",
  fontSize: 11,
};
