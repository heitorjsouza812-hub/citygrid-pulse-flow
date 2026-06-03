import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useMemo } from "react";
import { ArrowLeft, AlertTriangle } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { ZONAS_MOCK, ALERTAS_MOCK, generateHistorico } from "@/lib/mock-data";
import { RiscoBadge } from "@/components/RiscoBadge";
import { SemaforoANEEL } from "@/components/SemaforoANEEL";
import { FeedAlertas } from "@/components/FeedAlertas";
import { aneelDeseq, aneelFP, aneelFreq, aneelTHD } from "@/lib/risco";

export const Route = createFileRoute("/zona/$id")({
  head: ({ params }) => {
    const z = ZONAS_MOCK.find((x) => x.zona_id === params.id);
    return {
      meta: [
        { title: `${z?.zona_nome ?? "Zona"} — CityGrid Brain` },
        { name: "description", content: `Análise profunda da ${z?.zona_nome ?? "zona"}: histórico, previsão LSTM e qualidade de energia ANEEL PRODIST.` },
      ],
    };
  },
  loader: ({ params }) => {
    const z = ZONAS_MOCK.find((x) => x.zona_id === params.id);
    if (!z) throw notFound();
    return { zona: z };
  },
  notFoundComponent: NotFound,
  errorComponent: ErrComp,
  component: ZonaPage,
});

function NotFound() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-20 text-center">
      <h1 className="font-display font-extrabold text-4xl mb-2">Zona não encontrada</h1>
      <p className="text-muted-foreground mb-6">A zona solicitada não existe ou foi removida do monitoramento.</p>
      <Link to="/" className="text-primary underline">Voltar ao dashboard</Link>
    </main>
  );
}
function ErrComp({ error }: { error: Error }) {
  return <main className="p-8 text-destructive">Erro: {error.message}</main>;
}

function ZonaPage() {
  const { zona } = Route.useLoaderData();
  const historico = useMemo(() => generateHistorico(zona, 48), [zona]);
  const alertasZona = ALERTAS_MOCK.filter((a) => a.zona_id === zona.zona_id);

  return (
    <main className="mx-auto max-w-[1600px] px-4 lg:px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <Link to="/" className="text-xs text-muted-foreground hover:text-primary inline-flex items-center gap-1 mb-2">
            <ArrowLeft className="h-3 w-3" /> Dashboard
          </Link>
          <h1 className="font-display font-extrabold text-3xl">{zona.zona_nome}</h1>
          <p className="text-sm text-muted-foreground uppercase tracking-wider font-mono">{zona.perfil}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex gap-2">
            <RiscoBadge risco={zona.risco_xgb} />
            <RiscoBadge risco={zona.risco_lstm} prev />
          </div>
          <div className="font-mono text-sm">
            <span className="text-muted-foreground">Carga:</span>{" "}
            <span className="font-bold">{zona.consumo_mw.toFixed(2)} / {zona.capacidade_mw.toFixed(1)} MW</span>
            <span className="text-muted-foreground"> ({zona.pct_carga.toFixed(1)}%)</span>
          </div>
        </div>
      </div>

      {/* Semáforos ANEEL */}
      <section>
        <h2 className="font-display font-extrabold text-sm uppercase tracking-wider mb-2 text-muted-foreground">Qualidade de Energia — ANEEL PRODIST Módulo 8</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SemaforoANEEL estado={aneelFreq(zona.frequencia_hz)} label="Frequência" valor={zona.frequencia_hz.toFixed(2)} unidade="Hz" />
          <SemaforoANEEL estado={aneelTHD(zona.thd_tensao_pct)} label="THD Tensão" valor={zona.thd_tensao_pct.toFixed(1)} unidade="%" />
          <SemaforoANEEL estado={aneelFP(zona.fator_potencia)} label="Fator de Potência" valor={zona.fator_potencia.toFixed(3)} />
          <SemaforoANEEL estado={aneelDeseq(zona.desequilibrio_pct)} label="Desequilíbrio" valor={zona.desequilibrio_pct.toFixed(2)} unidade="%" />
        </div>
      </section>

      {/* Gráficos 2x2 */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Consumo — últimas 48 leituras" subtitle="MW por ciclo de 5 minutos">
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={historico}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--cyan-elec)" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="var(--cyan-elec)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="t" stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} />
              <YAxis stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="consumo" stroke="var(--cyan-elec)" strokeWidth={2} fill="url(#g1)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="LSTM vs Real" subtitle="Previsão (tracejado) vs medição (sólido)">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={historico}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="t" stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} />
              <YAxis stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={legendStyle} />
              <Line type="monotone" dataKey="consumo" name="Real" stroke="var(--cyan-elec)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="previsao" name="LSTM" stroke="var(--purple-elec)" strokeWidth={2} strokeDasharray="5 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Qualidade de Energia" subtitle="Frequência, tensão e THD ao longo do tempo">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={historico}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="t" stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} />
              <YAxis yAxisId="l" stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} />
              <YAxis yAxisId="r" orientation="right" stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={legendStyle} />
              <Line yAxisId="l" type="monotone" dataKey="freq" name="Freq (Hz)" stroke="var(--risk-low)" strokeWidth={1.5} dot={false} />
              <Line yAxisId="l" type="monotone" dataKey="tensao" name="Tensão (V)" stroke="var(--cyan-elec)" strokeWidth={1.5} dot={false} />
              <Line yAxisId="r" type="monotone" dataKey="thd" name="THD (%)" stroke="var(--risk-high)" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title={`Bateria — ${zona.bat_modo}`} subtitle={`SoC% ao longo das últimas 48 leituras`}>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={historico}>
              <defs>
                <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--purple-elec)" stopOpacity={0.6} />
                  <stop offset="100%" stopColor="var(--purple-elec)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="t" stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} />
              <YAxis stroke="var(--muted-foreground)" tick={{ fontSize: 10, fontFamily: "Space Mono" }} domain={[0, 100]} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="soc" name="SoC %" stroke="var(--purple-elec)" strokeWidth={2} fill="url(#g2)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      {/* Alertas */}
      <section className="card-surface p-4">
        <div className="absolute inset-x-0 top-0 h-px" style={{ background: "var(--gradient-accent)" }} />
        <h2 className="font-display font-extrabold text-sm uppercase tracking-wider mb-3 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-primary" /> Ações da IA para esta zona
        </h2>
        {alertasZona.length ? (
          <FeedAlertas alertas={alertasZona} maxHeight="24rem" />
        ) : (
          <p className="text-sm text-muted-foreground py-6 text-center">Nenhuma ação recente nesta zona.</p>
        )}
      </section>
    </main>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="card-surface p-4">
      <div className="absolute inset-x-0 top-0 h-px" style={{ background: "var(--gradient-accent)" }} />
      <h3 className="font-display font-bold text-sm">{title}</h3>
      {subtitle && <p className="text-[11px] text-muted-foreground mb-3">{subtitle}</p>}
      {children}
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
const legendStyle = { fontFamily: "Space Mono, monospace", fontSize: 10 };
