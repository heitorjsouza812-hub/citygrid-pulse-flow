import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  buscarEstadoInicial,
  buscarHistorico,
  normalizarAtualizacao,
  urlWebSocket,
} from "./citygrid-api";
import type { HistoricoPonto, Recomendacao, Stats, StatusConexao, Zona } from "./citygrid-types";

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
  dados_sinteticos: true,
};

interface CityGridContextValue {
  zonas: Zona[];
  stats: Stats;
  recomendacoes: Recomendacao[];
  status: StatusConexao;
  timestampSimulado: string | null;
  erro: string | null;
  atualizar: () => Promise<void>;
  carregarHistorico: (zonaId: string) => Promise<HistoricoPonto[]>;
}

const CityGridContext = createContext<CityGridContextValue | null>(null);

export function CityGridProvider({ children }: { children: ReactNode }) {
  const [zonas, setZonas] = useState<Zona[]>([]);
  const [stats, setStats] = useState<Stats>(STATS_VAZIAS);
  const [recomendacoes, setRecomendacoes] = useState<Recomendacao[]>([]);
  const [status, setStatus] = useState<StatusConexao>("conectando");
  const [timestampSimulado, setTimestampSimulado] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const ativo = useRef(true);

  async function atualizar() {
    try {
      const estado = await buscarEstadoInicial();
      if (!ativo.current) return;
      setZonas(estado.zonas);
      setStats(estado.stats);
      setRecomendacoes(estado.recomendacoes);
      setTimestampSimulado(estado.zonas[0]?.timestamp ?? null);
      setErro(null);
    } catch (error) {
      if (!ativo.current) return;
      setErro(error instanceof Error ? error.message : "Backend indisponível");
      setStatus("offline");
    }
  }

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
          const update = normalizarAtualizacao(JSON.parse(evento.data));
          setZonas(update.zonas);
          setStats(update.stats);
          setRecomendacoes(update.recomendacoes);
          setTimestampSimulado(update.timestampSimulado);
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
  }, []);

  const valor = useMemo<CityGridContextValue>(
    () => ({
      zonas,
      stats,
      recomendacoes,
      status,
      timestampSimulado,
      erro,
      atualizar,
      carregarHistorico: buscarHistorico,
    }),
    [zonas, stats, recomendacoes, status, timestampSimulado, erro],
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
