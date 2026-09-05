"""FastAPI transport for audience room state; domain rules remain in audience_rooms."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from audience_rooms import NotFoundError, RoomError, RoomManager


class CreateRoomRequest(BaseModel):
    resultado_ao_vivo: bool = False
    duracao_segundos: int | None = Field(default=20)

class JoinRequest(BaseModel):
    participant_id: str = Field(min_length=8, max_length=96)
    apelido: str | None = Field(default=None, max_length=100)

class VoteRequest(BaseModel):
    participant_id: str = Field(min_length=8, max_length=96)
    etapa: Literal["zona", "acao"]
    opcao: str = Field(min_length=1, max_length=64)

class RoundRequest(BaseModel):
    evento: Literal["tempestade", "incendio", "pico_consumo"]
    duracao_segundos: int | None = Field(default=None)
    resultado_ao_vivo: bool | None = None

class PhaseRequest(BaseModel):
    fase: Literal["VOTACAO_ZONA", "VOTACAO_ACAO"]

class TieRequest(BaseModel):
    opcao: str


class AudienceHub:
    def __init__(self) -> None:
        self.clients: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, code: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients[code].append(websocket)

    def disconnect(self, code: str, websocket: WebSocket) -> None:
        self.clients[code] = [item for item in self.clients[code] if item is not websocket]
        if not self.clients[code]: self.clients.pop(code, None)

    async def broadcast(self, code: str, payload: dict) -> None:
        failed: list[WebSocket] = []
        for websocket in self.clients.get(code, []):
            try: await websocket.send_json(payload)
            except Exception: failed.append(websocket)
        for websocket in failed: self.disconnect(code, websocket)


def build_audience_router(rooms: RoomManager, hub: AudienceHub) -> APIRouter:
    router = APIRouter(prefix="/api/salas", tags=["Central de Decisão da Plateia"])

    def error(exc: RoomError) -> HTTPException:
        return HTTPException(status_code=exc.status_code, detail=str(exc))

    async def emit(code: str, kind: str) -> None:
        await hub.broadcast(code, rooms.message(code, kind))

    @router.post("")
    async def create(payload: CreateRoomRequest):
        try: return rooms.create_room(payload.resultado_ao_vivo, payload.duracao_segundos)
        except RoomError as exc: raise error(exc) from exc

    @router.get("/{codigo}")
    async def get_room(codigo: str):
        try: return rooms.public_state(codigo)
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/entrar")
    async def join(codigo: str, payload: JoinRequest):
        try:
            result = rooms.join(codigo, payload.participant_id, payload.apelido)
            await emit(codigo, "participante_entrou")
            return result
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/votos")
    async def vote(codigo: str, payload: VoteRequest):
        try:
            result = rooms.cast_vote(codigo, payload.participant_id, payload.etapa, payload.opcao)
            await emit(codigo, "voto_registrado")
            await emit(codigo, "contagem_atualizada")
            return result
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/rodadas")
    async def start_round(codigo: str, payload: RoundRequest, x_presenter_token: str | None = Header(default=None, alias="X-Presenter-Token")):
        try:
            state = rooms.start_round(codigo, x_presenter_token, payload.evento, payload.duracao_segundos, payload.resultado_ao_vivo)
            await emit(codigo, "rodada_iniciada"); return state
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/fase")
    async def advance_phase(codigo: str, payload: PhaseRequest, x_presenter_token: str | None = Header(default=None, alias="X-Presenter-Token")):
        try:
            state = rooms.open_zone_vote(codigo, x_presenter_token) if payload.fase == "VOTACAO_ZONA" else rooms.open_action_vote(codigo, x_presenter_token)
            await emit(codigo, "votacao_aberta"); return state
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/encerrar-votacao")
    async def close_vote(codigo: str, x_presenter_token: str | None = Header(default=None, alias="X-Presenter-Token")):
        try:
            state = rooms.close_vote(codigo, x_presenter_token); await emit(codigo, "votacao_encerrada"); return state
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/desempate")
    async def resolve_tie(codigo: str, payload: TieRequest, x_presenter_token: str | None = Header(default=None, alias="X-Presenter-Token")):
        try:
            state = rooms.resolve_tie(codigo, x_presenter_token, payload.opcao); await emit(codigo, "sala_atualizada"); return state
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/revelar")
    async def reveal(codigo: str, x_presenter_token: str | None = Header(default=None, alias="X-Presenter-Token")):
        try:
            state = rooms.reveal(codigo, x_presenter_token); await emit(codigo, "resultado_revelado"); return state
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/aplicar")
    async def apply(codigo: str, x_presenter_token: str | None = Header(default=None, alias="X-Presenter-Token")):
        try:
            state = rooms.apply(codigo, x_presenter_token); await emit(codigo, "consequencia_aplicada"); return state
        except RoomError as exc: raise error(exc) from exc

    @router.post("/{codigo}/encerrar")
    async def end(codigo: str, x_presenter_token: str | None = Header(default=None, alias="X-Presenter-Token")):
        try:
            state = rooms.end(codigo, x_presenter_token); await emit(codigo, "apresentacao_encerrada"); return state
        except RoomError as exc: raise error(exc) from exc

    @router.delete("/{codigo}")
    async def delete(codigo: str, x_presenter_token: str | None = Header(default=None, alias="X-Presenter-Token")):
        try: rooms.delete(codigo, x_presenter_token); return {"ok": True}
        except RoomError as exc: raise error(exc) from exc

    return router


async def audience_websocket(websocket: WebSocket, code: str, rooms: RoomManager, hub: AudienceHub) -> None:
    participant_id = websocket.query_params.get("participant_id")
    try:
        rooms.public_state(code)
    except NotFoundError:
        await websocket.close(code=4404); return
    await hub.connect(code, websocket)
    rooms.connect(code, participant_id)
    await hub.broadcast(code, rooms.message(code, "participante_entrou"))
    try:
        while True:
            # Clients do not control state via WS; receive keeps the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(code, websocket)
        try:
            rooms.disconnect(code, participant_id)
            await hub.broadcast(code, rooms.message(code, "participante_saiu"))
        except RoomError:
            pass


async def room_lifecycle(rooms: RoomManager, hub: AudienceHub) -> None:
    """Server time closes finite votes and expires inactive rooms."""
    while True:
        for code in rooms.tick():
            await hub.broadcast(code, rooms.message(code, "votacao_encerrada"))
        rooms.expire_inactive()
        await asyncio.sleep(1)
