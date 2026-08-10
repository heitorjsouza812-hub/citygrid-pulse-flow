import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Cable,
  CheckCircle2,
  CircleAlert,
  Database,
  Eye,
  Gauge,
  Map,
  Network,
  RadioTower,
  ShieldCheck,
  Sparkles,
  UserRoundCheck,
  Zap,
} from "lucide-react";

import { useCityGrid } from "@/lib/citygrid-context";

export const Route = createFileRoute("/apresentacao")({
  head: () => ({
    meta: [
      { title: "O Projeto — CityGrid Brain" },
      {
        name: "description",
        content:
          "Uma visão clara da dor, da solução, da arquitetura e dos limites da demonstração CityGrid Brain.",
      },
    ],
  }),
  component: Apresentacao,
});

function Apresentacao() {
  const { zonas, stats, status, recomendacoes } = useCityGrid();
  const online = status === "conectado";

  return (
    <main className="project-page">
      <section className="project-hero">
        <div className="project-hero-copy">
          <p className="project-kicker">
            <span /> CITYGRID BRAIN · BRIEFING DE PROJETO
          </p>
          <h1>Da telemetria fragmentada à decisão explicável.</h1>
          <p className="project-lead">
            O CityGrid Brain é uma demonstração científica de uma rede elétrica urbana simulada. Ele
            transforma leituras de consumo, geração, clima e qualidade de energia em uma visão
            operacional para que uma pessoa possa entender prioridades antes de agir.
          </p>
          <div className="project-hero-actions">
            <Link to="/mapa" className="project-button project-button-primary">
              Abrir demonstração guiada <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#problema" className="project-button project-button-quiet">
              Entender a dor
            </a>
          </div>
          <p className="project-disclaimer">
            <ShieldCheck className="h-3.5 w-3.5" /> Dados integralmente sintéticos. Recomendações
            não executam comandos em uma rede real.
          </p>
        </div>

        <aside className="project-decision-map" aria-label="Fluxo de decisão do CityGrid Brain">
          <div className="project-map-topline">
            <span>MAPA DA DECISÃO</span>
            <span className={online ? "is-live" : ""}>
              {online ? "SISTEMA ONLINE" : "AGUARDANDO API"}
            </span>
          </div>
          <div className="project-signal-radar" aria-hidden="true">
            <i />
            <i />
            <i />
            <b />
          </div>
          <div className="project-map-rail" aria-hidden="true" />
          <DecisionPoint
            className="project-point-source"
            icon={<RadioTower />}
            label="Leituras"
            detail="campo"
          />
          <DecisionPoint
            className="project-point-context"
            icon={<Network />}
            label="Contexto"
            detail="rede + clima"
          />
          <DecisionPoint
            className="project-point-risk"
            icon={<Gauge />}
            label="Risco"
            detail="tendência"
          />
          <DecisionPoint
            className="project-point-action"
            icon={<UserRoundCheck />}
            label="Pessoa"
            detail="aprova"
          />
          <div className="project-map-caption">
            <span>Não é piloto automático.</span>
            <strong>É contexto para decisão.</strong>
          </div>
        </aside>
      </section>

      <section id="problema" className="project-section project-problem-section">
        <div className="project-section-heading">
          <p className="project-kicker">
            <span /> A DOR OPERACIONAL
          </p>
          <h2>Quando o sinal chega separado, a prioridade chega tarde.</h2>
        </div>
        <div className="project-problem-layout">
          <p className="project-statement">
            Operar uma rede urbana exige interpretar variáveis que mudam ao mesmo tempo. Consumo,
            geração distribuída, clima, frequência, harmônicos e condição de bateria podem estar em
            fontes diferentes — e o operador precisa formar um quadro coerente sob pressão.
          </p>
          <ol className="project-friction-list">
            <li>
              <span>01</span>
              <div>
                <strong>Visibilidade incompleta</strong>
                <p>Os sinais não aparecem juntos no momento em que uma zona começa a se desviar.</p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Alarmes sem contexto</strong>
                <p>
                  Um limite violado não explica impacto, tendência ou qual área merece atenção
                  primeiro.
                </p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Decisão difícil de auditar</strong>
                <p>
                  Sem uma trilha clara de evidências, recomendações são difíceis de revisar e
                  ensinar.
                </p>
              </div>
            </li>
          </ol>
        </div>
      </section>

      <section className="project-section project-answer-section">
        <div className="project-answer-intro">
          <p className="project-kicker">
            <span /> A PROPOSTA
          </p>
          <h2>Uma camada de leitura operacional, não uma caixa-preta.</h2>
          <p>
            O projeto une telemetria sintética, regras de risco e motores analíticos em uma
            interface que torna a hipótese de cada recomendação visível. O objetivo é reduzir a
            distância entre “algo mudou” e “o que devemos investigar agora?”.
          </p>
        </div>
        <div className="project-principles">
          <article>
            <Eye className="h-5 w-5" />
            <div>
              <strong>Ver o sistema</strong>
              <p>Mapa de zonas, estados, alertas e tendências no mesmo contexto operacional.</p>
            </div>
          </article>
          <article>
            <BrainCircuit className="h-5 w-5" />
            <div>
              <strong>Entender a sugestão</strong>
              <p>Origem, urgência, zona e leitura de cenário acompanham cada recomendação.</p>
            </div>
          </article>
          <article>
            <UserRoundCheck className="h-5 w-5" />
            <div>
              <strong>Manter decisão humana</strong>
              <p>
                O painel informa; não aciona equipamentos, não executa manobras e não promete
                resultado.
              </p>
            </div>
          </article>
        </div>
      </section>

      <section id="como-funciona" className="project-section project-system-section">
        <div className="project-section-heading project-system-heading">
          <p className="project-kicker">
            <span /> COMO FUNCIONA
          </p>
          <h2>Do dado ao operador em cinco camadas rastreáveis.</h2>
          <p>Uma demonstração de arquitetura, com dados sintéticos e ciclos acelerados.</p>
        </div>
        <div className="project-architecture" role="list">
          <ArchitectureStep
            order="A"
            icon={<RadioTower />}
            title="Sinais sintéticos"
            text="O simulador produz leituras de consumo, geração, clima, qualidade e armazenamento por zona."
          />
          <ArchitectureStep
            order="B"
            icon={<Database />}
            title="Contexto de rede"
            text="O backend organiza estado atual, histórico, alertas e cenários em uma mesma leitura temporal."
          />
          <ArchitectureStep
            order="C"
            icon={<Activity />}
            title="Análise de risco"
            text="Heurísticas e modelos experimentais destacam desvios, tendência e prioridade de investigação."
          />
          <ArchitectureStep
            order="D"
            icon={<Sparkles />}
            title="Recomendação explicável"
            text="Cada saída associa uma zona, uma urgência, uma origem e uma descrição compreensível."
          />
          <ArchitectureStep
            order="E"
            icon={<UserRoundCheck />}
            title="Avaliação humana"
            text="A decisão final permanece com a equipe responsável, com espaço para governança e auditoria."
          />
        </div>
      </section>

      <section className="project-section project-demo-section">
        <div className="project-demo-copy">
          <p className="project-kicker">
            <span /> O QUE MOSTRAR NA DEMO
          </p>
          <h2>Uma conversa de projeto em menos de três minutos.</h2>
          <p>
            Use o fluxo abaixo para apresentar a proposta sem confundir uma simulação com uma
            operação de produção.
          </p>
          <Link to="/mapa" className="project-inline-link">
            Ir para o mapa operacional <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="project-demo-runbook">
          <div>
            <span>01</span>
            <p>
              <strong>Comece pela dor.</strong> Mostre por que sinais isolados atrasam a leitura da
              rede.
            </p>
          </div>
          <div>
            <span>02</span>
            <p>
              <strong>Abra o mapa.</strong> Selecione uma zona para ligar risco, consumo, qualidade
              e bateria.
            </p>
          </div>
          <div>
            <span>03</span>
            <p>
              <strong>Ative um cenário.</strong> Use tempestade, incêndio ou pico de consumo para
              discutir prioridade.
            </p>
          </div>
          <div>
            <span>04</span>
            <p>
              <strong>Feche com governança.</strong> A IA recomenda; a equipe analisa, aprova e
              registra a decisão.
            </p>
          </div>
        </div>
      </section>

      <section className="project-live-strip" aria-label="Estado atual da demonstração">
        <div>
          <p>ESTADO DA DEMONSTRAÇÃO</p>
          <strong className={online ? "is-live" : ""}>
            {online ? "TELEMETRIA CONECTADA" : "CONECTANDO TELEMETRIA"}
          </strong>
        </div>
        <LiveData label="Zonas monitoradas" value={zonas.length ? String(zonas.length) : "—"} />
        <LiveData
          label="Recomendações no ciclo"
          value={recomendacoes.length ? String(recomendacoes.length) : "—"}
        />
        <LiveData
          label="Consumo observado"
          value={stats.consumo_total_mw ? `${stats.consumo_total_mw.toFixed(1)} MW` : "—"}
        />
        <p className="project-live-note">Leitura atual da simulação; não representa rede física.</p>
      </section>

      <section className="project-section project-boundary-section">
        <div className="project-boundary-icon">
          <CircleAlert className="h-5 w-5" />
        </div>
        <div>
          <p className="project-kicker">
            <span /> ESCOPO HONESTO
          </p>
          <h2>O que esta demonstração prova — e o que ainda exigiria produção.</h2>
        </div>
        <div className="project-boundary-grid">
          <div>
            <CheckCircle2 className="h-4 w-4" />
            <p>
              <strong>Explora a experiência.</strong> Mostra como telemetria, risco, cenário e
              recomendação podem coexistir em uma narrativa operacional.
            </p>
          </div>
          <div>
            <Cable className="h-4 w-4" />
            <p>
              <strong>Não se conecta à rede real.</strong> Integrações SCADA/IoT, segurança,
              calibração, aprovação e auditoria são etapas separadas para um ambiente produtivo.
            </p>
          </div>
        </div>
      </section>

      <section className="project-cta">
        <div>
          <p className="project-kicker">
            <span /> PRÓXIMO PASSO
          </p>
          <h2>Veja a hipótese funcionando no mapa.</h2>
          <p>
            Explore as zonas, simule um evento e acompanhe como o contexto muda as recomendações.
          </p>
        </div>
        <Link to="/mapa" className="project-button project-button-primary">
          Explorar CityGrid Brain <Map className="h-4 w-4" />
        </Link>
      </section>
    </main>
  );
}

function DecisionPoint({
  className,
  icon,
  label,
  detail,
}: {
  className: string;
  icon: React.ReactNode;
  label: string;
  detail: string;
}) {
  return (
    <div className={`project-decision-point ${className}`}>
      <span>{icon}</span>
      <div>
        <strong>{label}</strong>
        <small>{detail}</small>
      </div>
    </div>
  );
}

function ArchitectureStep({
  order,
  icon,
  title,
  text,
}: {
  order: string;
  icon: React.ReactNode;
  title: string;
  text: string;
}) {
  return (
    <article className="project-architecture-step" role="listitem">
      <span className="project-architecture-order">{order}</span>
      <div className="project-architecture-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

function LiveData({ label, value }: { label: string; value: string }) {
  return (
    <div className="project-live-data">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
