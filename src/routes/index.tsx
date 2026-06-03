import { createFileRoute, Link } from "@tanstack/react-router";
import { Zap, Sun, AlertOctagon, AlertTriangle, Bot, Leaf, Wind, Cloud, Droplets, ThermometerSun, Gauge, Map } from "lucide-react";
import { CardZona } from "@/components/CardZona";
import { MetricaCard } from "@/components/MetricaCard";
import { FeedAlertas } from "@/components/FeedAlertas";
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

  return (
    <main className="mx-auto max-w-[1600px] px-4 lg:px-6 py-6 space-y-6">
      {/* Page heading strip */}
      <div className="flex items-end justify-between gap-4 border-b border-border/60 pb-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-primary mb-1">Painel de Operações</div>
          <h1 className="font-display font-extrabold text-2xl leading-none tracking-tight">
            Visão Geral da <span className="gradient-text">Rede</span>
          </h1>
          <p className="text-xs text-muted-foreground mt-2 font-mono">
            8 zonas urbanas · ~400 mil habitantes · atualização contínua
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
          <span className="rounded border border-border bg-card px-2 py-1">ANEEL PRODIST M8</span>
          <span className="rounded border border-border bg-card px-2 py-1">60 Hz</span>
        </div>
      </div>

      {/* Evento ativo */}
      {stats.evento_ativo && (
        <div
          className="relative overflow-hidden rounded-xl border border-border p-4 flex items-center gap-4 animate-slide-in-up"
          style={{ background: "var(--gradient-banner)" }}
        >
          <div className="absolute inset-y-0 left-0 w-[3px]" style={{ background: "var(--purple-elec)", boxShadow: "0 0 16px var(--purple-elec)" }} />
          <div className="text-3xl pl-1">{stats.evento_ativo.icone}</div>
          <div className="flex-1 min-w-0">
            <div className="text-[10px] uppercase tracking-[0.22em] text-primary font-mono font-bold">Evento Ativo na Cidade</div>
            <div className="font-display font-extrabold text-lg leading-tight">{stats.evento_ativo.nome}</div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-[9px] uppercase tracking-[0.2em] text-muted-foreground font-mono font-bold">Impacto na rede</div>
            <div className="font-mono font-bold text-2xl gradient-text tabular-nums">+{stats.evento_ativo.impacto_pct.toFixed(1)}%</div>
          </div>
        </div>
      )}

      {/* Métricas globais */}
      <section className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <MetricaCard icon={<Zap className="h-4 w-4" />} label="Consumo Total" valor={stats.consumo_total_mw.toFixed(1)} unidade="MW" sub="consumidos agora" pct={(stats.consumo_total_mw / 250) * 100} />
        <MetricaCard icon={<Sun className="h-4 w-4" />} label="Renovável" valor={stats.renovavel_pct.toFixed(1)} unidade="%" sub={`${stats.renovavel_mw.toFixed(2)} MW de fontes limpas`} color="var(--risk-low)" gradient pct={stats.renovavel_pct} />
        <MetricaCard icon={<AlertOctagon className="h-4 w-4" />} label="Zonas Críticas" valor={stats.zonas_criticas} sub="zonas em emergência" color="var(--risk-crit)" />
        <MetricaCard icon={<AlertTriangle className="h-4 w-4" />} label="Anomalias" valor={stats.anomalias} sub="detectadas agora" color="var(--risk-high)" />
        <MetricaCard icon={<Bot className="h-4 w-4" />} label="Ações da IA" valor={stats.acoes_ia_total.toLocaleString("pt-BR")} sub="decisões acumuladas" color="var(--purple-elec)" />
        <MetricaCard icon={<Leaf className="h-4 w-4" />} label="Economia" valor={stats.economia_mwh.toFixed(1)} unidade="MWh" sub="economizados pela IA" color="var(--risk-low)" gradient />
      </section>

      {/* Grid principal */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
        {/* Zonas */}
        <section>
          <div className="flex items-end justify-between mb-3">
            <div>
              <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-primary mb-1">Monitoramento</div>
              <h2 className="font-display font-extrabold text-xl tracking-tight">Zonas Urbanas</h2>
            </div>
            <Link to="/mapa" className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-[10px] font-display font-bold uppercase tracking-[0.15em] text-primary hover:bg-surface/60 hover:shadow-[var(--shadow-glow-cyan)] transition-all">
              <Map className="h-3.5 w-3.5" /> Ver no Mapa
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
            {ZONAS_MOCK.map((z) => <CardZona key={z.zona_id} zona={z} />)}
          </div>
        </section>


        {/* Sidebar */}
        <aside className="space-y-4">
          <PainelClima />
          <PainelRenovavel />
          <PainelAlertas />
        </aside>
      </div>
    </main>
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
      <div className="absolute inset-x-0 top-0 h-px" style={{ background: "var(--gradient-accent)" }} />
      <h3 className="font-display font-extrabold text-sm uppercase tracking-wider mb-3 flex items-center gap-2">
        <ThermometerSun className="h-4 w-4 text-primary" /> Clima Atual
      </h3>
      <div className="grid grid-cols-2 gap-2">
        {items.map((i) => (
          <div key={i.label} className="rounded-md border border-border bg-surface/40 p-2">
            <div className="text-[9px] uppercase tracking-wider text-muted-foreground flex items-center gap-1">
              {i.icon} {i.label}
            </div>
            <div className="font-mono text-base font-bold mt-0.5">
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
      <div className="absolute inset-x-0 top-0 h-px" style={{ background: "var(--gradient-green)" }} />
      <h3 className="font-display font-extrabold text-sm uppercase tracking-wider mb-3 flex items-center gap-2">
        <Leaf className="h-4 w-4" style={{ color: "var(--risk-low)" }} /> Energia Renovável
      </h3>
      <div className="text-center py-2">
        <div className="font-mono text-5xl font-bold" style={{ color: "var(--risk-low)" }}>
          {s.renovavel_pct.toFixed(1)}<span className="text-2xl text-muted-foreground">%</span>
        </div>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-1 font-mono">
          {s.renovavel_mw.toFixed(2)} MW do total
        </div>
      </div>
      <div className="h-2 w-full rounded-full bg-surface overflow-hidden border border-border mt-2">
        <div className="h-full transition-[width] duration-500" style={{ width: `${Math.min(100, s.renovavel_pct)}%`, background: "var(--gradient-green)", boxShadow: "0 0 12px var(--risk-low)" }} />
      </div>
      <div className="grid grid-cols-2 gap-2 mt-3">
        <div className="rounded-md border border-border bg-surface/40 p-2">
          <div className="text-[9px] uppercase tracking-wider text-muted-foreground flex items-center gap-1"><Sun className="h-3 w-3" /> Solar</div>
          <div className="font-mono text-base font-bold mt-0.5">{solar.toFixed(2)}<span className="text-[10px] text-muted-foreground ml-1">MW</span></div>
        </div>
        <div className="rounded-md border border-border bg-surface/40 p-2">
          <div className="text-[9px] uppercase tracking-wider text-muted-foreground flex items-center gap-1"><Wind className="h-3 w-3" /> Eólica</div>
          <div className="font-mono text-base font-bold mt-0.5">{eolica.toFixed(2)}<span className="text-[10px] text-muted-foreground ml-1">MW</span></div>
        </div>
      </div>
    </div>
  );
}

function PainelAlertas() {
  return (
    <div className="card-surface p-4">
      <div className="absolute inset-x-0 top-0 h-px" style={{ background: "var(--gradient-accent)" }} />
      <h3 className="font-display font-extrabold text-sm uppercase tracking-wider mb-3 flex items-center gap-2">
        <Bot className="h-4 w-4 text-primary" /> Feed de Ações da IA
      </h3>
      <FeedAlertas alertas={ALERTAS_MOCK} maxHeight="28rem" />
    </div>
  );
}
