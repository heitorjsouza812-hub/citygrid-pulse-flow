export type FaseSala =
  "LOBBY" | "EVENTO" | "VOTACAO_ZONA" | "VOTACAO_ACAO" | "RESULTADO" | "CONSEQUENCIA" | "ENCERRADA";
export type TipoEventoPlateia = "tempestade" | "incendio" | "pico_consumo";
export interface OpcaoSala {
  id: string;
  label: string;
  detail?: string;
}
export interface PlacarCidade {
  estabilidade: number;
  reserva: number;
  controle_custos: number;
  satisfacao: number;
  pontuacao_geral: number;
}
export interface SalaPlateia {
  codigo: string;
  fase: FaseSala;
  rodada: number;
  participantes: number;
  conectados: number;
  evento: {
    tipo: TipoEventoPlateia;
    nome: string;
    descricao: string;
    zonas_afetadas: string[];
  } | null;
  resultado_ao_vivo: boolean;
  duracao_segundos: number | null;
  votacao_termina_em: string | null;
  votacao_bloqueada: boolean;
  opcoes_zona: OpcaoSala[];
  opcoes_acao: OpcaoSala[];
  contagens: { zona: Record<string, number>; acao: Record<string, number> };
  vencedores: Record<string, string>;
  empate: { etapa: "zona" | "acao" | null; opcoes: string[] };
  placar: PlacarCidade;
  placar_antes: PlacarCidade | null;
  recomendacao: {
    zona: string;
    acao: string;
    origem: string;
    explicacao: string;
    semelhante: boolean;
    classificacao: string;
  } | null;
  consequencia: {
    projecao: boolean;
    resumo: string;
    zonas_afetadas: string[];
    zona_priorizada: string;
    acao: string;
    deltas: Record<string, number>;
    telemetria: Record<string, number>;
    alertas: string[];
  } | null;
  resumo_final: {
    rodadas: number;
    pontuacao_final: number;
    participantes: number;
    total_votos: number;
    semelhantes_ia: number;
    diferentes_ia: number;
    melhor_rodada: number;
    rodada_mais_arriscada: number;
    mensagem: string;
  } | null;
  dados_sinteticos: boolean;
}
export interface SalaCriada extends SalaPlateia {
  presenter_token: string;
  participation_url: string;
}
export type SalaMensagem = { tipo: string; sala: SalaPlateia; enviado_em: string };
