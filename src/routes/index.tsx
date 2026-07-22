import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertOctagon,
  AlertTriangle,
  Bot,
  Cloud,
  Droplets,
  Gauge,
  Leaf,
  Map,
  Sun,
  ThermometerSun,
  Wind,
  Zap,
} from "lucide-react";

import { CardZona } from "@/components/CardZona";
import { FeedAlertas } from "@/components/FeedAlertas";
import { MetricaCard } from "@/components/MetricaCard";
import { useCityGrid } from "@/lib/citygrid-context";
import type { Recomendacao, Stats, Zona } from "@/lib/citygrid-types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — CityGrid Brain" },
      {
        name: "description",
        content: "Telemetria de oito zonas em uma simulação urbana acelerada com dados sintéticos.",
      },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { zonas, recomendacoes, stats, status, erro } = useCityGrid();
  const clima = zonas[0] ?? null;

  return (
    <main className="mx-auto max-w-[1600px] px-4 lg:px-6 py-5 space-y-5">
      <div className="flex items-end justify-between gap-4 border-b border-border pb-3">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-1">
            Demonstração científica · Visão geral
          </div>
          <h1 className="font-display font-semibold text-xl leading-none tracking-tight text-foreground">
            Rede Urbana Simulada
          </h1>
          <p className="text-xs text-muted-foreground mt-2 font-mono">
            {zonas.length || 8} zonas · dados integralmente sintéticos
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.14em] text-muted-foreground">
          <span className="rounded-sm border border-border bg-card px-2 py-1">
            Referências técnicas
          </span>
          <span className="rounded-sm border border-border bg-card px-2 py-1">60 Hz</span>
        </div>
      </div>

      <div className="card-surface border-primary/40 p-3.5 flex flex-wrap items-center gap-3 text-xs">
        <Gauge className="h-4 w-4 text-primary" />
        <strong>SIMULAÇÃO ACELERADA</strong>
        <span className="text-muted-foreground">
          5 segundos reais = {stats.intervalo_simulado_minutos || 5} minutos simulados. Nenhuma
          recomendação é executada em uma rede real.
        </span>
      </div>

      {status === "offline" && (
        <div className="rounded-sm border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          Backend offline. Os painéis não exibem dados substitutos ou inventados.
          {erro ? ` Detalhe: ${erro}` : ""}
        </div>
      )}

      {stats.evento_ativo && (
        <div className="card-surface p-3.5 flex items-center gap-4">
          <div className="h-8 w-1 rounded-sm" style={{ backgroundColor: "var(--primary)" }} />
          <div className="flex-1 min-w-0">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono">
              Evento sintético ativo
            </div>
            <div className="font-display font-semibold text-sm leading-tight text-foreground mt-0.5">
              {stats.evento_ativo}
            </div>
          </div>
        </div>
      )}

      <section className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <MetricaCard
          icon={<Zap className="h-4 w-4" />}
          label="Consumo Total"
          valor={stats.consumo_total_mw.toFixed(1)}
          unidade="MW"
          sub="telemetria simulada"
          pct={(stats.consumo_total_mw / 250) * 100}
        />
        <MetricaCard
          icon={<Sun className="h-4 w-4" />}
          label="Renovável"
          valor={stats.renovavel_pct.toFixed(1)}
          unidade="%"
          sub={`${stats.renovavel_mw.toFixed(2)} MW gerados`}
          color="var(--risk-low)"
          gradient
          pct={stats.renovavel_pct}
        />
        <MetricaCard
          icon={<AlertOctagon className="h-4 w-4" />}
          label="Zonas Críticas"
          valor={stats.zonas_criticas}
          sub="estado atual simulado"
          color="var(--risk-crit)"
        />
        <MetricaCard
          icon={<AlertTriangle className="h-4 w-4" />}
          label="Anomalias"
          valor={stats.anomalias}
          sub="eventos sintéticos ativos"
          color="var(--risk-high)"
        />
        <MetricaCard
          icon={<Bot className="h-4 w-4" />}
          label="Recomendações"
          valor={stats.total_recomendacoes}
          sub="registros recentes"
          color="var(--purple-elec)"
        />
        <MetricaCard
          icon={<Leaf className="h-4 w-4" />}
          label="Energia Renovável"
          valor={stats.energia_renovavel_intervalo_mwh.toFixed(3)}
          unidade="MWh"
          sub={`no intervalo simulado de ${stats.intervalo_simulado_minutos} min`}
          color="var(--risk-low)"
          gradient
        />
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
        <section>
          <div className="flex items-end justify-between mb-3">
            <div>
              <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-1">
                Monitoramento
              </div>
              <h2 className="font-display font-semibold text-base tracking-tight text-foreground">
                Zonas Urbanas
              </h2>
            </div>
            <Link
              to="/mapa"
              className="inline-flex items-center gap-1.5 rounded-sm border border-border bg-card px-2.5 py-1.5 text-[10px] font-display font-medium uppercase tracking-[0.12em] text-foreground hover:border-primary/50 transition-colors"
            >
              <Map className="h-3.5 w-3.5" /> Ver no mapa
            </Link>
          </div>
          {zonas.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
              {zonas.map((zona) => (
                <CardZona key={zona.zona_id} zona={zona} />
              ))}
            </div>
          ) : (
            <div className="card-surface p-8 text-center text-sm text-muted-foreground">
              Aguardando telemetria do simulador e do backend.
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <PainelClima zona={clima} />
          <PainelRenovavel zonas={zonas} stats={stats} />
          <PainelRecomendacoes recomendacoes={recomendacoes} />
        </aside>
      </div>
    </main>
  );
}

function PainelClima({ zona }: { zona: Zona | null }) {
  const items = zona
    ? [
        {
          icon: <ThermometerSun className="h-3.5 w-3.5" />,
          label: "Temperatura",
          val: zona.clima_temp_c.toFixed(1),
          u: "°C",
        },
        {
          icon: <ThermometerSun className="h-3.5 w-3.5" />,
          label: "Sensação",
          val: zona.clima_sensacao_c.toFixed(1),
          u: "°C",
        },
        {
          icon: <Sun className="h-3.5 w-3.5" />,
          label: "Irradiância",
          val: zona.clima_irrad_wm2.toFixed(0),
          u: "W/m²",
        },
        {
          icon: <Wind className="h-3.5 w-3.5" />,
          label: "Vento",
          val: zona.clima_vento_ms.toFixed(1),
          u: "m/s",
        },
        {
          icon: <Droplets className="h-3.5 w-3.5" />,
          label: "Umidade",
          val: zona.clima_umidade_pct.toFixed(0),
          u: "%",
        },
        { icon: <Cloud className="h-3.5 w-3.5" />, label: "Fonte", val: "SIM", u: "" },
      ]
    : [];
  return (
    <div className="card-surface p-4">
      <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground mb-3 flex items-center gap-2">
        <ThermometerSun className="h-3.5 w-3.5" /> Clima Sintético
      </h3>
      {items.length ? (
        <div className="grid grid-cols-2 gap-1.5">
          {items.map((item) => (
            <div key={item.label} className="rounded-sm border border-border bg-surface/40 p-2">
              <div className="text-[9px] uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                {item.icon} {item.label}
              </div>
              <div className="font-mono text-sm font-semibold mt-0.5 tabular-nums">
                {item.val}
                <span className="text-[10px] text-muted-foreground ml-1">{item.u}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">Aguardando dados.</p>
      )}
    </div>
  );
}

function PainelRenovavel({ zonas, stats }: { zonas: Zona[]; stats: Stats }) {
  const solar = zonas.reduce((total, zona) => total + zona.solar_mw, 0);
  const eolica = zonas.reduce((total, zona) => total + zona.eolica_mw, 0);
  return (
    <div className="card-surface p-4">
      <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground mb-3 flex items-center gap-2">
        <Leaf className="h-3.5 w-3.5" /> Geração Renovável
      </h3>
      <div
        className="font-mono text-3xl font-semibold tabular-nums"
        style={{ color: "var(--risk-low)" }}
      >
        {stats.renovavel_pct.toFixed(1)}
        <span className="text-lg text-muted-foreground ml-1">%</span>
      </div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-1 font-mono">
        {stats.renovavel_mw.toFixed(2)} MW no ciclo atual
      </div>
      <div className="grid grid-cols-2 gap-1.5 mt-3">
        <MiniFonte icon={<Sun className="h-3 w-3" />} label="Solar" valor={solar} />
        <MiniFonte icon={<Wind className="h-3 w-3" />} label="Eólica" valor={eolica} />
      </div>
    </div>
  );
}

function MiniFonte({
  icon,
  label,
  valor,
}: {
  icon: React.ReactNode;
  label: string;
  valor: number;
}) {
  return (
    <div className="rounded-sm border border-border bg-surface/40 p-2">
      <div className="text-[9px] uppercase tracking-wider text-muted-foreground flex items-center gap-1">
        {icon} {label}
      </div>
      <div className="font-mono text-sm font-semibold mt-0.5 tabular-nums">
        {valor.toFixed(2)}
        <span className="text-[10px] text-muted-foreground ml-1">MW</span>
      </div>
    </div>
  );
}

function PainelRecomendacoes({ recomendacoes }: { recomendacoes: Recomendacao[] }) {
  return (
    <div className="card-surface p-4">
      <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground mb-3 flex items-center gap-2">
        <Bot className="h-3.5 w-3.5" /> Recomendações Simuladas
      </h3>
      {recomendacoes.length ? (
        <FeedAlertas alertas={recomendacoes} maxHeight="28rem" />
      ) : (
        <p className="text-xs text-muted-foreground">Nenhuma recomendação registrada.</p>
      )}
    </div>
  );
}
