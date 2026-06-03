import { createFileRoute, Link } from "@tanstack/react-router";
import { Zap, Sun, AlertOctagon, AlertTriangle, Bot, Leaf, Wind, Cloud, Droplets, ThermometerSun, Map, Gauge, TrendingUp } from "lucide-react";
import { CardZona } from "@/components/CardZona";
import { MetricaCard } from "@/components/MetricaCard";
import { FeedAlertas } from "@/components/FeedAlertas";
import { SubestacoesPanel } from "@/components/panels/Subestacoes";
import { TransformadoresPanel } from "@/components/panels/Transformadores";
import { ConformidadeANEELPanel } from "@/components/panels/ConformidadeANEEL";
import { TarifaPanel } from "@/components/panels/Tarifa";
import { PlantaoPanel } from "@/components/panels/Plantao";
import { ZONAS_MOCK, ALERTAS_MOCK, STATS_MOCK, CLIMA_MOCK } from "@/lib/mock-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — CityGrid Brain" },
      { name: "description", content: "Visão em tempo real das 8 zonas urbanas, métricas globais, clima e ações da IA." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const stats = STATS_MOCK;
  const capacidade_total = ZONAS_MOCK.reduce((s, z) => s + z.capacidade_mw, 0);
  const carga_global = (stats.consumo_total_mw / capacidade_total) * 100;
  const reserva = capacidade_total - stats.consumo_total_mw;
  const ve_em_uso = ZONAS_MOCK.reduce((s, z) => s + z.ve_postos_em_uso, 0);
  const ve_total = ZONAS_MOCK.reduce((s, z) => s + z.ve_postos_total, 0);
  const bess_medio = ZONAS_MOCK.reduce((s, z) => s + z.bat_soc_pct, 0) / ZONAS_MOCK.length;
  const pico_previsto = Math.max(...ZONAS_MOCK.flatMap((z) => z.previsao_mw));

  return (
    <main className="mx-auto max-w-[1600px] px-4 lg:px-6 py-5 space-y-5">
      {/* Breadcrumb + heading strip */}
      <div className="flex items-end justify-between gap-4 border-b border-border pb-3">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-1">
            COS / Operações / Visão Geral
          </div>
          <h1 className="font-display font-semibold text-xl leading-none tracking-tight text-foreground">
            Painel da Rede de Distribuição
          </h1>
          <p className="text-xs text-muted-foreground mt-2 font-mono">
            8 zonas urbanas · ~400 mil consumidores · {capacidade_total.toFixed(0)} MW instalados · telemetria 1 Hz
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.14em] text-muted-foreground">
          <span className="rounded-sm border border-border bg-card px-2 py-1">PRODIST M8</span>
          <span className="rounded-sm border border-border bg-card px-2 py-1">60 Hz</span>
          <span className="rounded-sm border border-border bg-card px-2 py-1">SE-{ZONAS_MOCK.length}</span>
          <span className="rounded-sm border border-border bg-card px-2 py-1">CICLO #{stats.ciclo}</span>
        </div>
      </div>

      {/* Evento ativo */}
      {stats.evento_ativo && (
        <div className="card-surface p-3.5 flex items-center gap-4">
          <div className="h-8 w-1 rounded-sm" style={{ backgroundColor: "var(--primary)" }} />
          <div className="flex-1 min-w-0">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono">Evento ativo</div>
            <div className="font-display font-semibold text-sm leading-tight text-foreground mt-0.5">{stats.evento_ativo.nome}</div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground font-mono">Impacto</div>
            <div className="font-mono font-semibold text-lg text-foreground tabular-nums">+{stats.evento_ativo.impacto_pct.toFixed(1)}%</div>
          </div>
        </div>
      )}

      {/* Métricas globais — 8 KPIs */}
      <section className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-2.5">
        <MetricaCard icon={<Zap className="h-4 w-4" />} label="Demanda" valor={stats.consumo_total_mw.toFixed(1)} unidade="MW" sub={`${carga_global.toFixed(1)}% da capacidade`} pct={carga_global} />
        <MetricaCard icon={<Gauge className="h-4 w-4" />} label="Reserva" valor={reserva.toFixed(1)} unidade="MW" sub="margem operativa" color="var(--risk-low)" pct={(reserva / capacidade_total) * 100} />
        <MetricaCard icon={<TrendingUp className="h-4 w-4" />} label="Pico Previsto" valor={pico_previsto.toFixed(1)} unidade="MW" sub="janela 30 min · LSTM" color="var(--risk-med)" />
        <MetricaCard icon={<Sun className="h-4 w-4" />} label="Renovável" valor={stats.renovavel_pct.toFixed(1)} unidade="%" sub={`${stats.renovavel_mw.toFixed(2)} MW gerados`} color="var(--risk-low)" pct={stats.renovavel_pct} />
        <MetricaCard icon={<AlertOctagon className="h-4 w-4" />} label="Zonas Críticas" valor={stats.zonas_criticas} sub="em emergência" color="var(--risk-crit)" />
        <MetricaCard icon={<AlertTriangle className="h-4 w-4" />} label="Anomalias" valor={stats.anomalias} sub="ativas agora" color="var(--risk-high)" />
        <MetricaCard icon={<Bot className="h-4 w-4" />} label="Ações IA / 24h" valor={stats.acoes_ia_total.toLocaleString("pt-BR")} sub="decisões executadas" />
        <MetricaCard icon={<Leaf className="h-4 w-4" />} label="Economia" valor={stats.economia_mwh.toFixed(1)} unidade="MWh" sub="evitados pela IA" color="var(--risk-low)" />
      </section>

      {/* Sub-KPI strip */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        <MiniKpi label="BESS médio (SOC)" val={`${bess_medio.toFixed(0)}%`} sub="frota de baterias" />
        <MiniKpi label="Postos VE em uso" val={`${ve_em_uso} / ${ve_total}`} sub={`${((ve_em_uso / ve_total) * 100).toFixed(0)}% ocupação`} />
        <MiniKpi label="Temperatura urbana" val={`${CLIMA_MOCK.temp_c.toFixed(1)} °C`} sub={`sensação ${CLIMA_MOCK.sensacao_c.toFixed(1)} °C`} />
        <MiniKpi label="Irradiância" val={`${CLIMA_MOCK.irradiancia_wm2} W/m²`} sub={`vento ${CLIMA_MOCK.vento_ms.toFixed(1)} m/s`} />
      </section>

      {/* Grid principal */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-4">
        {/* Zonas */}
        <section>
          <div className="flex items-end justify-between mb-3">
            <div>
              <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground mb-1">Monitoramento</div>
              <h2 className="font-display font-semibold text-base tracking-tight text-foreground">Zonas Urbanas</h2>
            </div>
            <Link to="/mapa" className="inline-flex items-center gap-1.5 rounded-sm border border-border bg-card px-2.5 py-1.5 text-[10px] font-display font-medium uppercase tracking-[0.12em] text-foreground hover:border-primary/50 transition-colors">
              <Map className="h-3.5 w-3.5" /> Ver no mapa
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
            {ZONAS_MOCK.map((z) => <CardZona key={z.zona_id} zona={z} />)}
          </div>

          {/* Operational tables */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mt-4">
            <SubestacoesPanel />
            <TransformadoresPanel />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mt-3">
            <ConformidadeANEELPanel />
            <TarifaPanel />
          </div>
        </section>

        {/* Sidebar */}
        <aside className="space-y-3">
          <PlantaoPanel />
          <PainelClima />
          <PainelRenovavel />
          <PainelAlertas />
        </aside>
      </div>
    </main>
  );
}

function MiniKpi({ label, val, sub }: { label: string; val: string; sub: string }) {
  return (
    <div className="card-surface px-3.5 py-2.5 flex items-center justify-between">
      <div>
        <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-mono">{label}</div>
        <div className="text-[11px] text-muted-foreground font-mono mt-0.5">{sub}</div>
      </div>
      <div className="font-mono text-base font-semibold tabular-nums text-foreground">{val}</div>
    </div>
  );
}

function PainelClima() {
  const c = CLIMA_MOCK;
  const items = [
    { icon: <ThermometerSun className="h-3.5 w-3.5" />, label: "Temperatura", val: `${c.temp_c.toFixed(1)}`, u: "°C" },
    { icon: <ThermometerSun className="h-3.5 w-3.5" />, label: "Sensação", val: `${c.sensacao_c.toFixed(1)}`, u: "°C" },
    { icon: <Sun className="h-3.5 w-3.5" />, label: "Irradiância", val: `${c.irradiancia_wm2}`, u: "W/m²" },
    { icon: <Wind className="h-3.5 w-3.5" />, label: "Vento", val: `${c.vento_ms.toFixed(1)}`, u: "m/s" },
    { icon: <Droplets className="h-3.5 w-3.5" />, label: "Umidade", val: `${c.umidade_pct}`, u: "%" },
    { icon: <Cloud className="h-3.5 w-3.5" />, label: "Nebulosidade", val: `${c.nebulosidade_pct}`, u: "%" },
  ];
  return (
    <div className="card-surface p-4">
      <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground mb-3 flex items-center gap-2">
        <ThermometerSun className="h-3.5 w-3.5" /> Condições Climáticas
      </h3>
      <div className="grid grid-cols-2 gap-1.5">
        {items.map((i) => (
          <div key={i.label} className="rounded-sm border border-border bg-surface/40 p-2">
            <div className="text-[9px] uppercase tracking-wider text-muted-foreground flex items-center gap-1">
              {i.icon} {i.label}
            </div>
            <div className="font-mono text-sm font-semibold mt-0.5 tabular-nums">
              {i.val}<span className="text-[10px] text-muted-foreground ml-1">{i.u}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PainelRenovavel() {
  const s = STATS_MOCK;
  const solar = ZONAS_MOCK.reduce((a, z) => a + z.solar_mw, 0);
  const eolica = ZONAS_MOCK.reduce((a, z) => a + z.eolica_mw, 0);
  return (
    <div className="card-surface p-4">
      <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground mb-3 flex items-center gap-2">
        <Leaf className="h-3.5 w-3.5" /> Geração Renovável
      </h3>
      <div className="py-1">
        <div className="font-mono text-3xl font-semibold tabular-nums" style={{ color: "var(--risk-low)" }}>
          {s.renovavel_pct.toFixed(1)}<span className="text-lg text-muted-foreground ml-1">%</span>
        </div>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-1 font-mono">
          {s.renovavel_mw.toFixed(2)} MW da geração total
        </div>
      </div>
      <div className="h-1 w-full bg-surface overflow-hidden rounded-sm mt-3 border border-border">
        <div className="h-full" style={{ width: `${Math.min(100, s.renovavel_pct)}%`, backgroundColor: "var(--risk-low)" }} />
      </div>
      <div className="grid grid-cols-2 gap-1.5 mt-3">
        <div className="rounded-sm border border-border bg-surface/40 p-2">
          <div className="text-[9px] uppercase tracking-wider text-muted-foreground flex items-center gap-1"><Sun className="h-3 w-3" /> Solar</div>
          <div className="font-mono text-sm font-semibold mt-0.5 tabular-nums">{solar.toFixed(2)}<span className="text-[10px] text-muted-foreground ml-1">MW</span></div>
        </div>
        <div className="rounded-sm border border-border bg-surface/40 p-2">
          <div className="text-[9px] uppercase tracking-wider text-muted-foreground flex items-center gap-1"><Wind className="h-3 w-3" /> Eólica</div>
          <div className="font-mono text-sm font-semibold mt-0.5 tabular-nums">{eolica.toFixed(2)}<span className="text-[10px] text-muted-foreground ml-1">MW</span></div>
        </div>
      </div>
    </div>
  );
}

function PainelAlertas() {
  return (
    <div className="card-surface p-4">
      <h3 className="font-display font-semibold text-[12px] uppercase tracking-[0.14em] text-muted-foreground mb-3 flex items-center gap-2">
        <Bot className="h-3.5 w-3.5" /> Eventos do Sistema
      </h3>
      <FeedAlertas alertas={ALERTAS_MOCK} maxHeight="28rem" />
    </div>
  );
}
