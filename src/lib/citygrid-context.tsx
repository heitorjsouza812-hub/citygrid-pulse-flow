import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  ativarCenario as ativarCenarioApi,
  buscarEstadoInicial,
  buscarHistorico,
  limparCenario as limparCenarioApi,
  normalizarAtualizacao,
  urlWebSocket,
} from "./citygrid-api";
import type {
  CenarioManual,
  HistoricoPonto,
  Recomendacao,
  SnapshotTelemetria,
  Stats,
  StatusConexao,
  TipoCenario,
  Zona,
} from "./citygrid-types";
import { mesclarHistoricoRecomendacoes } from "./recommendation-activity";

const STATS_VAZIAS: Stats = {
  consumo_total_mw: 0,
  renovavel_pct: 0,
  renovavel_mw: 0,
  zonas_criticas: 0,
  zonas_alto: 0,
  anomalias: 0,
  total_recomendacoes: 0,
  energia_renovavel_intervalo_mwh: 0,
  intervalo_simulado_minutos: 5,
  ciclo: 0,
  evento_ativo: null,
  cenario_manual: null,
  dados_sinteticos: true,
};

interface CityGridContextValue {
  zonas: Zona[];
  stats: Stats;
  recomendacoes: Recomendacao[];
  status: StatusConexao;
  timestampSimulado: string | null;
  snapshots: SnapshotTelemetria[];
  cenarioManual: CenarioManual | null;
  erro: string | null;
  atualizar: () => Promise<void>;
  carregarHistorico: (zonaId: string) => Promise<HistoricoPonto[]>;
  ativarCenario: (tipo: TipoCenario) => Promise<void>;
  limparCenario: () => Promise<void>;
}

const CityGridContext = createContext<CityGridContextValue | null>(null);

export function CityGridProvider({ children }: { children: ReactNode }) {
  const [zonas, setZonas] = useState<Zona[]>([]);
  const [stats, setStats] = useState<Stats>(STATS_VAZIAS);
  const [recomendacoes, setRecomendacoes] = useState<Recomendacao[]>([]);
  const [status, setStatus] = useState<StatusConexao>("conectando");
  const [timestampSimulado, setTimestampSimulado] = useState<string | null>(null);
  const [snapshots, setSnapshots] = useState<SnapshotTelemetria[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const ativo = useRef(true);

  const aplicarEstado = useCallback(
    (estado: {
      zonas: Zona[];
      stats: Stats;
      recomendacoes: Recomendacao[];
      timestampSimulado: string | null;
    }) => {
      setZonas(estado.zonas);
      setStats(estado.stats);
      setRecomendacoes((anteriores) =>
        mesclarHistoricoRecomendacoes(anteriores, estado.recomendacoes),
      );
      setTimestampSimulado(estado.timestampSimulado);
      setSnapshots((anteriores) => {
        const ultimo = anteriores.at(-1);
        if (ultimo?.ciclo === estado.stats.ciclo) return anteriores;
        return [
          ...anteriores,
          {
            ciclo: estado.stats.ciclo,
            timestamp: estado.timestampSimulado,
            zonas: estado.zonas,
            stats: estado.stats,
            recomendacoes: estado.recomendacoes,
          },
        ].slice(-48);
      });
    },
    [],
  );

  const atualizar = useCallback(async () => {
    try {
      const estado = await buscarEstadoInicial();
      if (!ativo.current) return;
      aplicarEstado({ ...estado, timestampSimulado: estado.zonas[0]?.timestamp ?? null });
      setErro(null);
    } catch (error) {
      if (!ativo.current) return;
      setErro(error instanceof Error ? error.message : "Backend indisponível");
      setStatus("offline");
    }
  }, [aplicarEstado]);

  useEffect(() => {
    ativo.current = true;
    let socket: WebSocket | null = null;
    let reconectarId: ReturnType<typeof setTimeout> | null = null;

    const conectar = () => {
      if (!ativo.current) return;
      setStatus("conectando");
      socket = new WebSocket(urlWebSocket());
      socket.onopen = () => {
        if (!ativo.current) return;
        setStatus("conectado");
        setErro(null);
      };
      socket.onmessage = (evento) => {
        if (!ativo.current) return;
        try {
          aplicarEstado(normalizarAtualizacao(JSON.parse(evento.data)));
        } catch {
          setErro("Atualização recebida em formato inválido");
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (!ativo.current) return;
        setStatus("offline");
        reconectarId = setTimeout(conectar, 2500);
      };
    };

    void atualizar().finally(conectar);
    const polling = setInterval(() => void atualizar(), 10_000);
    return () => {
      ativo.current = false;
      clearInterval(polling);
      if (reconectarId) clearTimeout(reconectarId);
      socket?.close();
    };
  }, [aplicarEstado, atualizar]);

  const ativarCenario = useCallback(async (tipo: TipoCenario) => {
    const cenario = await ativarCenarioApi(tipo);
    setStats((anterior) => ({ ...anterior, cenario_manual: cenario }));
  }, []);

  const limparCenario = useCallback(async () => {
    await limparCenarioApi();
    setStats((anterior) => ({ ...anterior, cenario_manual: null }));
  }, []);

  const valor = useMemo<CityGridContextValue>(
    () => ({
      zonas,
      stats,
      recomendacoes,
      status,
      timestampSimulado,
      snapshots,
      cenarioManual: stats.cenario_manual,
      erro,
      atualizar,
      carregarHistorico: buscarHistorico,
      ativarCenario,
      limparCenario,
    }),
    [
      zonas,
      stats,
      recomendacoes,
      status,
      timestampSimulado,
      snapshots,
      erro,
      atualizar,
      ativarCenario,
      limparCenario,
    ],
  );

  return <CityGridContext.Provider value={valor}>{children}</CityGridContext.Provider>;
}

// O provider e o hook formam uma API única de contexto.
// eslint-disable-next-line react-refresh/only-export-components
export function useCityGrid(): CityGridContextValue {
  const contexto = useContext(CityGridContext);
  if (!contexto) {
    throw new Error("useCityGrid deve ser usado dentro de CityGridProvider");
  }
  return contexto;
}
