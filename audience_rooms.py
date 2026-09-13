"""In-memory, server-authoritative rooms for Central de Decisão da Plateia.

The store is deliberately isolated from FastAPI so it can be replaced by a Redis
adapter for multi-worker deployments. All values describe synthetic educational
scenario projections; no telemetry file or electrical equipment is changed.
"""
from __future__ import annotations

import re
import secrets
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal
from uuid import uuid4

Phase = Literal["LOBBY", "EVENTO", "VOTACAO_ZONA", "VOTACAO_ACAO", "RESULTADO", "CONSEQUENCIA", "ENCERRADA"]


class RoomError(Exception):
    status_code = 400


class NotFoundError(RoomError):
    status_code = 404


class AuthorizationError(RoomError):
    status_code = 403


class PhaseError(RoomError):
    status_code = 409


class ValidationError(RoomError):
    status_code = 422


ZONE_LABELS = {
    "zona_norte": "Norte", "zona_oeste": "Oeste", "zona_aeroporto": "Aeroporto",
    "zona_centro": "Centro", "zona_hospitalar": "Hospitalar", "zona_sul": "Sul",
    "zona_universitaria": "Universitária",
}
ACTIONS: dict[str, list[dict[str, str]]] = {
    "tempestade": [
        {"id": "usar_baterias", "label": "Utilizar baterias", "detail": "Sustenta frequência durante a queda de geração."},
        {"id": "redistribuir_energia", "label": "Redistribuir energia", "detail": "Equilibra os alimentadores disponíveis."},
        {"id": "reduzir_nao_essenciais", "label": "Reduzir cargas não essenciais", "detail": "Preserva a reserva para cargas prioritárias."},
    ],
    "incendio": [
        {"id": "priorizar_essenciais", "label": "Priorizar cargas essenciais", "detail": "Mantém contingência em serviços críticos."},
        {"id": "isolar_zona", "label": "Isolar a zona afetada", "detail": "Reduz propagação operacional do cenário."},
        {"id": "redistribuir_energia", "label": "Redistribuir energia", "detail": "Reorganiza o atendimento das zonas."},
    ],
    "pico_consumo": [
        {"id": "reduzir_nao_essenciais", "label": "Reduzir cargas não essenciais", "detail": "Diminui sobrecarga coordenada."},
        {"id": "usar_baterias", "label": "Utilizar baterias", "detail": "Apoia a reserva em pico transitório."},
        {"id": "aguardar", "label": "Aguardar novas informações", "detail": "Alternativa que exige atenção e monitoramento."},
    ],
}
# Single documented rule table. Deltas are positive when the city condition improves.
IMPACTS: dict[str, dict[str, tuple[int, int, int, int]]] = {
    "tempestade": {"usar_baterias": (15, -20, -5, 5), "redistribuir_energia": (10, -5, -10, 10), "reduzir_nao_essenciais": (20, 10, 5, -15)},
    "incendio": {"priorizar_essenciais": (15, -5, -5, 12), "isolar_zona": (20, 5, -10, -10), "redistribuir_energia": (10, -5, -10, 10)},
    "pico_consumo": {"reduzir_nao_essenciais": (20, 10, 5, -15), "usar_baterias": (15, -20, -5, 5), "aguardar": (-20, 0, 0, -10)},
}
RECOMMENDED = {
    "tempestade": ("zona_norte", "usar_baterias"),
    "incendio": ("zona_hospitalar", "priorizar_essenciais"),
    "pico_consumo": ("zona_centro", "reduzir_nao_essenciais"),
}
POINTS_PER_COMPLETED_ROUND = 50
MAX_ALIGNMENT_BONUS = 25
MAX_PARTICIPATION_BONUS = 25
GAME_POINT_TARGET = 3 * (
    POINTS_PER_COMPLETED_ROUND + MAX_ALIGNMENT_BONUS + MAX_PARTICIPATION_BONUS
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def clean_nickname(value: str | None) -> str:
    text = re.sub(r"<[^>]*>", "", value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > 28:
        text = text[:28]
    return text or "Participante"


def clamp(value: float) -> float:
    return round(max(0, min(100, value)), 1)


@dataclass
class Room:
    code: str
    presenter_token: str
    created_at: datetime
    last_activity: datetime
    phase: Phase = "LOBBY"
    round_number: int = 0
    event_type: str | None = None
    reveal_live: bool = False
    duration_seconds: int | None = 20
    vote_ends_at: datetime | None = None
    voting_locked: bool = False
    participants: dict[str, str] = field(default_factory=dict)
    connections: Counter[str] = field(default_factory=Counter)
    votes: dict[tuple[str, str], str] = field(default_factory=dict)
    winners: dict[str, str] = field(default_factory=dict)
    ties: dict[str, list[str]] = field(default_factory=dict)
    scoreboard: dict[str, float] = field(default_factory=lambda: {"estabilidade": 75, "reserva": 70, "controle_custos": 70, "satisfacao": 75})
    before_scoreboard: dict[str, float] | None = None
    recommendation: dict[str, Any] | None = None
    consequence: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    rate_limit: dict[str, datetime] = field(default_factory=dict)
    game_points: int = 0
    alignment_bonus_total: int = 0
    participation_bonus_total: int = 0
    round_feedback: dict[str, Any] | None = None


class RoomManager:
    """Pure state manager. FastAPI/WebSocket infrastructure calls this API."""
    def __init__(
        self,
        scenarios: dict[str, dict[str, Any]],
        public_app_url: str,
        ttl_minutes: int = 120,
        signal_provider: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self.scenarios = scenarios
        self.public_app_url = public_app_url.rstrip("/")
        self.ttl_minutes = ttl_minutes
        self.signal_provider = signal_provider
        self._rooms: dict[str, Room] = {}

    def set_signal_provider(self, provider: Callable[[str], dict[str, Any]] | None) -> None:
        """Inject read-only operational signals without coupling room rules to FastAPI."""
        self.signal_provider = provider

    def _room(self, code: str) -> Room:
        room = self._rooms.get(code.upper())
        if not room:
            raise NotFoundError("Sala não encontrada ou expirada")
        return room

    def _touch(self, room: Room) -> None:
        room.last_activity = utcnow()

    def create_room(self, reveal_live: bool = False, duration_seconds: int | None = 20) -> dict[str, Any]:
        if duration_seconds not in (None, 10, 15, 20, 30):
            raise ValidationError("Duração inválida")
        while True:
            code = f"CG-{secrets.randbelow(10000):04d}"
            if code not in self._rooms:
                break
        now = utcnow()
        room = Room(code=code, presenter_token=secrets.token_urlsafe(32), created_at=now, last_activity=now, reveal_live=reveal_live, duration_seconds=duration_seconds)
        self._rooms[code] = room
        return {**self.public_state(code), "presenter_token": room.presenter_token, "participation_url": f"{self.public_app_url}/participar/{code}"}

    def _require_admin(self, room: Room, token: str | None) -> None:
        if not token or not secrets.compare_digest(room.presenter_token, token):
            raise AuthorizationError("Credencial privada do apresentador inválida")

    def join(self, code: str, participant_id: str, nickname: str | None) -> dict[str, Any]:
        room = self._room(code)
        if room.phase == "ENCERRADA":
            raise PhaseError("Esta apresentação foi encerrada")
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,96}", participant_id):
            raise ValidationError("Identificador de participante inválido")
        room.participants[participant_id] = clean_nickname(nickname)
        self._touch(room)
        return {"participant_id": participant_id, "apelido": room.participants[participant_id], "sala": self.public_state(code)}

    def connect(self, code: str, participant_id: str | None) -> None:
        room = self._room(code)
        if participant_id and participant_id in room.participants:
            room.connections[participant_id] += 1
        self._touch(room)

    def disconnect(self, code: str, participant_id: str | None) -> None:
        room = self._room(code)
        if participant_id and room.connections[participant_id]:
            room.connections[participant_id] -= 1
            if not room.connections[participant_id]:
                del room.connections[participant_id]
        self._touch(room)

    def _event(self, room: Room) -> dict[str, Any]:
        if not room.event_type:
            return {}
        return self.scenarios[room.event_type]

    def start_round(self, code: str, token: str | None, event_type: str, duration_seconds: int | None = None, reveal_live: bool | None = None) -> dict[str, Any]:
        room = self._room(code); self._require_admin(room, token)
        if room.phase not in ("LOBBY", "CONSEQUENCIA"):
            raise PhaseError("A rodada atual precisa ser concluída antes de iniciar outra")
        if room.round_number >= 3:
            raise PhaseError("A apresentação já atingiu três rodadas")
        if event_type not in self.scenarios:
            raise ValidationError("Evento não disponível")
        duration = room.duration_seconds if duration_seconds is None else duration_seconds
        if duration not in (None, 10, 15, 20, 30):
            raise ValidationError("Duração inválida")
        room.round_number += 1; room.event_type = event_type; room.phase = "EVENTO"; room.duration_seconds = duration
        if reveal_live is not None: room.reveal_live = reveal_live
        room.vote_ends_at = None; room.voting_locked = False; room.votes = {}; room.winners = {}; room.ties = {}; room.recommendation = None; room.consequence = None; room.before_scoreboard = dict(room.scoreboard); room.round_feedback = None
        self._touch(room); return self.public_state(code)

    def _open(self, room: Room, phase: Phase) -> None:
        if phase == "VOTACAO_ZONA" and room.phase != "EVENTO": raise PhaseError("Apresente o evento antes de abrir a votação de zona")
        if phase == "VOTACAO_ACAO" and (room.phase != "VOTACAO_ZONA" or "zona" not in room.winners): raise PhaseError("Conclua a escolha de zona antes da ação")
        room.phase = phase; room.voting_locked = False
        room.vote_ends_at = utcnow() + timedelta(seconds=room.duration_seconds) if room.duration_seconds else None
        self._touch(room)

    def open_zone_vote(self, code: str, token: str | None) -> dict[str, Any]:
        room = self._room(code); self._require_admin(room, token); self._open(room, "VOTACAO_ZONA"); return self.public_state(code)

    def open_action_vote(self, code: str, token: str | None) -> dict[str, Any]:
        room = self._room(code); self._require_admin(room, token); self._open(room, "VOTACAO_ACAO"); return self.public_state(code)

    def _stage(self, room: Room) -> str:
        if room.phase == "VOTACAO_ZONA": return "zona"
        if room.phase == "VOTACAO_ACAO": return "acao"
        raise PhaseError("Não há votação aberta")

    def _options(self, room: Room, stage: str) -> list[str]:
        event = self._event(room)
        return event.get("zonas_afetadas", []) if stage == "zona" else [item["id"] for item in ACTIONS[room.event_type or "tempestade"]]

    def cast_vote(self, code: str, participant_id: str, stage: str, option: str) -> dict[str, Any]:
        room = self._room(code)
        if participant_id not in room.participants: raise AuthorizationError("Entre na sala antes de votar")
        expected = self._stage(room)
        if stage != expected or room.voting_locked: raise PhaseError("Voto bloqueado para a fase atual")
        if room.vote_ends_at and utcnow() >= room.vote_ends_at:
            self._finish_vote(room); raise PhaseError("Tempo de votação encerrado pelo servidor")
        if option not in self._options(room, stage): raise ValidationError("Opção não pertence a esta rodada")
        now = utcnow(); last = room.rate_limit.get(participant_id)
        # Repeated taps on the same card are idempotent; a deliberate option
        # change remains allowed during the open server-controlled window.
        if last and (now - last).total_seconds() < 0.15 and room.votes.get((participant_id, stage)) == option:
            return {"voto": option, "etapa": stage, "contagens": self._counts(room, stage), "sala": self.public_state(code)}
        room.rate_limit[participant_id] = now; room.votes[(participant_id, stage)] = option; self._touch(room)
        return {"voto": option, "etapa": stage, "contagens": self._counts(room, stage), "sala": self.public_state(code)}

    def _counts(self, room: Room, stage: str) -> dict[str, int]:
        return dict(sorted(Counter(v for (pid, s), v in room.votes.items() if s == stage).items()))

    def _finish_vote(self, room: Room) -> None:
        stage = self._stage(room); room.voting_locked = True; room.vote_ends_at = None
        counts = self._counts(room, stage)
        if not counts:
            room.ties[stage] = []
        else:
            top = max(counts.values()); winners = [key for key, value in counts.items() if value == top]
            if len(winners) == 1: room.winners[stage] = winners[0]
            else: room.ties[stage] = winners
        self._touch(room)

    def close_vote(self, code: str, token: str | None) -> dict[str, Any]:
        room = self._room(code); self._require_admin(room, token); self._finish_vote(room); return self.public_state(code)

    def resolve_tie(self, code: str, token: str | None, option: str) -> dict[str, Any]:
        room = self._room(code); self._require_admin(room, token)
        stage = self._stage(room)
        allowed = room.ties.get(stage)
        if not allowed or option not in allowed: raise ValidationError("A opção não faz parte do empate atual")
        room.winners[stage] = option; del room.ties[stage]; self._touch(room); return self.public_state(code)

    def reveal(self, code: str, token: str | None) -> dict[str, Any]:
        room = self._room(code); self._require_admin(room, token)
        if room.phase != "VOTACAO_ACAO" or not room.voting_locked or room.ties.get("acao") or "acao" not in room.winners:
            raise PhaseError("Conclua a votação de ação e qualquer desempate antes de revelar")
        rec_zone, rec_action = RECOMMENDED[room.event_type or "tempestade"]
        selected_zone = room.winners.get("zona") or rec_zone
        signals: dict[str, Any] = {}
        if self.signal_provider:
            try:
                signals = self.signal_provider(selected_zone) or {}
            except Exception:
                # The educational room remains usable if optional live signals are unavailable.
                signals = {}
        sources = ["Heurística explicável", "cenário sintético"]
        details = ["A recomendação prioriza o cenário educacional e o menor risco estimado."]
        if signals.get("risco_lstm"):
            sources.append("contexto LSTM")
            forecast = signals.get("previsao_mw")
            forecast_text = f" com previsão de {float(forecast):.1f} MW" if isinstance(forecast, (int, float)) else ""
            details.append(f"Para a zona priorizada, o LSTM indica risco futuro {signals['risco_lstm']}{forecast_text}.")
        if signals.get("risco_xgb"):
            confidence = signals.get("confianca_xgb")
            confidence_text = f" (confiança interna {float(confidence):.0%})" if isinstance(confidence, (int, float)) else ""
            details.append(f"O XGBoost sinaliza risco {signals['risco_xgb']}{confidence_text} apenas como sinal analítico; não controla a decisão enquanto seu gate estiver fechado.")
        else:
            details.append("O XGBoost, quando disponível, permanece apenas como sinal analítico; não controla decisões.")
        similar = room.winners.get("zona") == rec_zone and room.winners.get("acao") == rec_action
        room.recommendation = {
            "zona": rec_zone,
            "acao": rec_action,
            "origem": " + ".join(sources),
            "explicacao": " ".join(details),
            "semelhante": similar,
            "classificacao": "Escolha semelhante à recomendação" if similar else "Alternativa que exige atenção",
        }
        room.phase = "RESULTADO"; self._touch(room); return self.public_state(code)

    def apply(self, code: str, token: str | None) -> dict[str, Any]:
        room = self._room(code); self._require_admin(room, token)
        if room.phase != "RESULTADO" or not room.event_type or "acao" not in room.winners: raise PhaseError("Revele o resultado antes de aplicar a projeção")
        deltas = IMPACTS[room.event_type][room.winners["acao"]]
        keys = ("estabilidade", "reserva", "controle_custos", "satisfacao")
        for key, delta in zip(keys, deltas): room.scoreboard[key] = clamp(room.scoreboard[key] + delta)
        score = self.city_score(room.scoreboard)
        event = self._event(room); targeted = room.winners.get("zona")
        room.consequence = {"projecao": True, "resumo": f"Resultado da simulação educacional: {ACTIONS[room.event_type][[a['id'] for a in ACTIONS[room.event_type]].index(room.winners['acao'])]['label']} aplicada em {ZONE_LABELS.get(targeted, targeted)}.", "zonas_afetadas": event["zonas_afetadas"], "zona_priorizada": targeted, "acao": room.winners["acao"], "deltas": dict(zip(keys, deltas)), "telemetria": {"carga_delta_pct": -8 if room.winners["acao"] in ("reduzir_nao_essenciais", "isolar_zona") else -3, "bateria_delta_pct": -12 if room.winners["acao"] == "usar_baterias" else 0, "frequencia_delta_hz": 0.08 if deltas[0] > 0 else -0.08, "thd_delta_pct": -1.2 if deltas[0] > 0 else 1.8}, "alertas": ["PROJEÇÃO DE CENÁRIO", "Dados sintéticos; nenhuma ação enviada à rede real."]}
        round_score = score - self.city_score(room.before_scoreboard or room.scoreboard)
        zone_voters = {participant for participant, stage in room.votes if stage == "zona"}
        action_voters = {participant for participant, stage in room.votes if stage == "acao"}
        complete_participants = len(zone_voters & action_voters)
        eligible_participants = len(room.participants)
        participation_ratio = (
            complete_participants / eligible_participants if eligible_participants else 0
        )
        participation_bonus = int(MAX_PARTICIPATION_BONUS * participation_ratio + 0.5)
        aligned = bool(room.recommendation and room.recommendation["semelhante"])
        alignment_bonus = MAX_ALIGNMENT_BONUS if aligned else 0
        round_points = POINTS_PER_COMPLETED_ROUND + alignment_bonus + participation_bonus
        room.game_points += round_points
        room.alignment_bonus_total += alignment_bonus
        room.participation_bonus_total += participation_bonus
        if aligned and participation_ratio == 1:
            feedback_message = "Missão concluída com alinhamento e participação total."
        elif aligned:
            feedback_message = "Missão alinhada; mais participação aumenta o bônus coletivo."
        else:
            feedback_message = "Missão concluída; compare a escolha com a recomendação documentada."
        room.round_feedback = {
            "rodada": room.round_number,
            "pontos_base": POINTS_PER_COMPLETED_ROUND,
            "bonus_alinhamento": alignment_bonus,
            "bonus_participacao": participation_bonus,
            "pontos_rodada": round_points,
            "pontos_total": room.game_points,
            "participacao_pct": round(participation_ratio * 100, 1),
            "participantes_completos": complete_participants,
            "participantes_elegiveis": eligible_participants,
            "alinhada_recomendacao": aligned,
            "mensagem": feedback_message,
        }
        room.history.append({"rodada": room.round_number, "evento": room.event_type, "zona": room.winners.get("zona"), "acao": room.winners.get("acao"), "pontuacao": score, "ganho_rodada": round(round_score, 1), "semelhante_ia": aligned, "risco": abs(min(deltas)), "pontos_jogo": round_points, "bonus_alinhamento": alignment_bonus, "bonus_participacao": participation_bonus, "participacao_pct": round(participation_ratio * 100, 1), "votos_rodada": len(room.votes)})
        room.phase = "CONSEQUENCIA"; self._touch(room); return self.public_state(code)

    @staticmethod
    def city_score(scoreboard: dict[str, float]) -> float:
        return round(.40 * scoreboard["estabilidade"] + .25 * scoreboard["reserva"] + .15 * scoreboard["controle_custos"] + .20 * scoreboard["satisfacao"], 1)

    def end(self, code: str, token: str | None) -> dict[str, Any]:
        room = self._room(code); self._require_admin(room, token); room.phase = "ENCERRADA"; self._touch(room); return self.public_state(code)

    def delete(self, code: str, token: str | None) -> None:
        room = self._room(code); self._require_admin(room, token); del self._rooms[room.code]

    def tick(self) -> list[str]:
        changed: list[str] = []
        for room in self._rooms.values():
            if room.phase in ("VOTACAO_ZONA", "VOTACAO_ACAO") and room.vote_ends_at and utcnow() >= room.vote_ends_at:
                self._finish_vote(room); changed.append(room.code)
        return changed

    def expire_inactive(self) -> list[str]:
        cutoff = utcnow() - timedelta(minutes=self.ttl_minutes); expired = [code for code, room in self._rooms.items() if room.last_activity < cutoff]
        for code in expired: del self._rooms[code]
        return expired

    def _summary(self, room: Room) -> dict[str, Any] | None:
        if len(room.history) < 3: return None
        best = max(room.history, key=lambda item: item["ganho_rodada"]); risky = max(room.history, key=lambda item: item["risco"])
        alike = sum(1 for item in room.history if item["semelhante_ia"])
        return {"rodadas": len(room.history), "pontuacao_final": self.city_score(room.scoreboard), "pontos_jogo": room.game_points, "meta_pontos": GAME_POINT_TARGET, "bonus_alinhamento_total": room.alignment_bonus_total, "bonus_participacao_total": room.participation_bonus_total, "participantes": len(room.participants), "total_votos": sum(item["votos_rodada"] for item in room.history), "semelhantes_ia": alike, "diferentes_ia": len(room.history) - alike, "melhor_rodada": best["rodada"], "rodada_mais_arriscada": risky["rodada"], "mensagem": f"A cidade terminou com {self.city_score(room.scoreboard):.0f}% de desempenho geral. Em {alike} das {len(room.history)} rodadas, a decisão da plateia foi semelhante à recomendação do CityGrid Brain."}

    def _progress(self, room: Room) -> dict[str, Any]:
        return {
            "pontos_total": room.game_points,
            "meta_pontos": GAME_POINT_TARGET,
            "progresso_pct": round(min(100, room.game_points / GAME_POINT_TARGET * 100), 1),
            "rodadas_concluidas": len(room.history),
            "total_rodadas": 3,
            "bonus_alinhamento_total": room.alignment_bonus_total,
            "bonus_participacao_total": room.participation_bonus_total,
            "feedback_rodada": room.round_feedback,
        }

    def public_state(self, code: str) -> dict[str, Any]:
        room = self._room(code); event = self._event(room); stage = "zona" if room.phase == "VOTACAO_ZONA" else "acao" if room.phase == "VOTACAO_ACAO" else None
        zone_options = [{"id": z, "label": ZONE_LABELS.get(z, z)} for z in event.get("zonas_afetadas", [])]
        action_options = ACTIONS.get(room.event_type or "", [])
        return {"id": room.code, "codigo": room.code, "fase": room.phase, "rodada": room.round_number, "criada_em": iso(room.created_at), "ultima_atividade": iso(room.last_activity), "participantes": len(room.participants), "conectados": len(room.connections), "evento": {"tipo": room.event_type, "nome": event.get("nome"), "descricao": event.get("descricao"), "zonas_afetadas": event.get("zonas_afetadas", [])} if room.event_type else None, "resultado_ao_vivo": room.reveal_live, "duracao_segundos": room.duration_seconds, "votacao_termina_em": iso(room.vote_ends_at), "votacao_bloqueada": room.voting_locked, "opcoes_zona": zone_options, "opcoes_acao": action_options, "contagens": {"zona": self._counts(room, "zona"), "acao": self._counts(room, "acao")}, "vencedores": dict(room.winners), "empate": {"etapa": stage, "opcoes": room.ties.get(stage, []) if stage else []}, "placar": {**room.scoreboard, "pontuacao_geral": self.city_score(room.scoreboard)}, "placar_antes": room.before_scoreboard, "recomendacao": room.recommendation, "consequencia": room.consequence, "progressao": self._progress(room), "historico": room.history, "resumo_final": self._summary(room), "dados_sinteticos": True}

    def message(self, code: str, message_type: str) -> dict[str, Any]:
        return {"tipo": message_type, "sala": self.public_state(code), "enviado_em": iso(utcnow())}
