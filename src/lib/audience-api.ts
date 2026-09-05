import type { SalaCriada, SalaPlateia, TipoEventoPlateia } from "./audience-types";

const base = ((import.meta.env.VITE_CITYGRID_API_URL as string | undefined) ?? "").replace(
  /\/$/,
  "",
);
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string" ? body.detail : `API respondeu HTTP ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}
const auth = (token: string) => ({ "X-Presenter-Token": token });
export const audienceApi = {
  create: (resultado_ao_vivo = false, duracao_segundos: number | null = 20) =>
    request<SalaCriada>("/api/salas", {
      method: "POST",
      body: JSON.stringify({ resultado_ao_vivo, duracao_segundos }),
    }),
  get: (code: string) => request<SalaPlateia>(`/api/salas/${encodeURIComponent(code)}`),
  join: (code: string, participant_id: string, apelido?: string) =>
    request<{ sala: SalaPlateia }>(`/api/salas/${encodeURIComponent(code)}/entrar`, {
      method: "POST",
      body: JSON.stringify({ participant_id, apelido }),
    }),
  vote: (code: string, participant_id: string, etapa: "zona" | "acao", opcao: string) =>
    request<{ sala: SalaPlateia }>(`/api/salas/${encodeURIComponent(code)}/votos`, {
      method: "POST",
      body: JSON.stringify({ participant_id, etapa, opcao }),
    }),
  start: (
    code: string,
    token: string,
    evento: TipoEventoPlateia,
    duracao_segundos: number | null,
    resultado_ao_vivo: boolean,
  ) =>
    request<SalaPlateia>(`/api/salas/${code}/rodadas`, {
      method: "POST",
      headers: auth(token),
      body: JSON.stringify({ evento, duracao_segundos, resultado_ao_vivo }),
    }),
  phase: (code: string, token: string, fase: "VOTACAO_ZONA" | "VOTACAO_ACAO") =>
    request<SalaPlateia>(`/api/salas/${code}/fase`, {
      method: "POST",
      headers: auth(token),
      body: JSON.stringify({ fase }),
    }),
  close: (code: string, token: string) =>
    request<SalaPlateia>(`/api/salas/${code}/encerrar-votacao`, {
      method: "POST",
      headers: auth(token),
    }),
  tie: (code: string, token: string, opcao: string) =>
    request<SalaPlateia>(`/api/salas/${code}/desempate`, {
      method: "POST",
      headers: auth(token),
      body: JSON.stringify({ opcao }),
    }),
  reveal: (code: string, token: string) =>
    request<SalaPlateia>(`/api/salas/${code}/revelar`, { method: "POST", headers: auth(token) }),
  apply: (code: string, token: string) =>
    request<SalaPlateia>(`/api/salas/${code}/aplicar`, { method: "POST", headers: auth(token) }),
  end: (code: string, token: string) =>
    request<SalaPlateia>(`/api/salas/${code}/encerrar`, { method: "POST", headers: auth(token) }),
  delete: (code: string, token: string) =>
    request<{ ok: true }>(`/api/salas/${encodeURIComponent(code)}`, {
      method: "DELETE",
      headers: auth(token),
    }),
};
export function audienceWsUrl(code: string, participantId?: string) {
  const explicit = import.meta.env.VITE_CITYGRID_WS_URL as string | undefined;
  const root = explicit
    ? explicit.replace(/\/$/, "")
    : base
      ? base.replace(/^http/, "ws")
      : typeof window !== "undefined"
        ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`
        : "ws://127.0.0.1:8000";
  return `${root}/ws/salas/${encodeURIComponent(code)}${participantId ? `?participant_id=${encodeURIComponent(participantId)}` : ""}`;
}
