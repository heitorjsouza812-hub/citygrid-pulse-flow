from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from audience_rooms import AuthorizationError, PhaseError, RoomManager, ValidationError

SCENARIOS = {
    "tempestade": {
        "nome": "Tempestade severa",
        "descricao": "Teste",
        "zonas_afetadas": ["zona_norte", "zona_oeste", "zona_aeroporto"],
        "impactos": {"consumo_pct": 8, "geracao_pct": -60, "frequencia_delta_hz": -0.12, "thd_delta_pct": 4, "bateria_delta_pct": -12},
    },
    "incendio": {
        "nome": "Incêndio urbano",
        "descricao": "Teste",
        "zonas_afetadas": ["zona_centro", "zona_hospitalar"],
        "impactos": {"consumo_pct": 12, "geracao_pct": -10, "frequencia_delta_hz": -0.08, "thd_delta_pct": 3.5, "bateria_delta_pct": -16},
    },
    "pico_consumo": {
        "nome": "Pico de consumo",
        "descricao": "Teste",
        "zonas_afetadas": ["zona_sul", "zona_centro", "zona_universitaria"],
        "impactos": {"consumo_pct": 28, "geracao_pct": 0, "frequencia_delta_hz": -0.1, "thd_delta_pct": 2.8, "bateria_delta_pct": -10},
    },
}


def manager() -> RoomManager:
    return RoomManager(SCENARIOS, public_app_url="http://192.168.0.10:5173", ttl_minutes=1)


def test_room_creation_is_public_without_presenter_token_and_codes_are_unique() -> None:
    rooms = manager()
    one = rooms.create_room()
    two = rooms.create_room()
    assert one["codigo"] != two["codigo"]
    assert one["presenter_token"]
    assert one["participation_url"] == f"http://192.168.0.10:5173/participar/{one['codigo']}"
    assert "presenter_token" not in rooms.public_state(one["codigo"])
    assert rooms.public_state(one["codigo"])["fase"] == "LOBBY"


def test_participant_cannot_control_room_and_nickname_is_sanitized() -> None:
    rooms = manager()
    created = rooms.create_room()
    joined = rooms.join(created["codigo"], "participant-001", " <b> Ana </b> ")
    assert joined["apelido"] == "Ana"
    with pytest.raises(AuthorizationError):
        rooms.start_round(created["codigo"], "wrong", "tempestade", 10)


def test_vote_can_be_replaced_without_inflating_count_then_closes() -> None:
    rooms = manager()
    created = rooms.create_room()
    code, token = created["codigo"], created["presenter_token"]
    rooms.join(code, "participant-001", "Ana")
    rooms.start_round(code, token, "tempestade", 10)
    rooms.open_zone_vote(code, token)
    rooms.cast_vote(code, "participant-001", "zona", "zona_norte")
    rooms.cast_vote(code, "participant-001", "zona", "zona_oeste")
    assert rooms.public_state(code)["contagens"]["zona"] == {"zona_oeste": 1}
    rooms.close_vote(code, token)
    with pytest.raises(PhaseError):
        rooms.cast_vote(code, "participant-001", "zona", "zona_norte")


def test_tie_requires_explicit_presenter_choice() -> None:
    rooms = manager()
    created = rooms.create_room()
    code, token = created["codigo"], created["presenter_token"]
    rooms.join(code, "participant-a", "A")
    rooms.join(code, "participant-b", "B")
    rooms.start_round(code, token, "incendio", None)
    rooms.open_zone_vote(code, token)
    rooms.cast_vote(code, "participant-a", "zona", "zona_centro")
    rooms.cast_vote(code, "participant-b", "zona", "zona_hospitalar")
    rooms.close_vote(code, token)
    assert set(rooms.public_state(code)["empate"]["opcoes"]) == {"zona_centro", "zona_hospitalar"}
    with pytest.raises(ValidationError):
        rooms.resolve_tie(code, token, "zona_norte")
    rooms.resolve_tie(code, token, "zona_hospitalar")
    assert rooms.public_state(code)["vencedores"]["zona"] == "zona_hospitalar"


def test_impacts_clamp_score_and_final_summary_after_three_rounds() -> None:
    rooms = manager()
    created = rooms.create_room()
    code, token = created["codigo"], created["presenter_token"]
    rooms.join(code, "participant-main", "P")
    for event in ("tempestade", "incendio", "pico_consumo"):
        rooms.start_round(code, token, event, None)
        rooms.open_zone_vote(code, token)
        zone = rooms.public_state(code)["opcoes_zona"][0]["id"]
        rooms.cast_vote(code, "participant-main", "zona", zone)
        rooms.close_vote(code, token)
        rooms.open_action_vote(code, token)
        action = rooms.public_state(code)["opcoes_acao"][0]["id"]
        rooms.cast_vote(code, "participant-main", "acao", action)
        rooms.close_vote(code, token)
        rooms.reveal(code, token)
        state = rooms.apply(code, token)
        assert all(0 <= state["placar"][key] <= 100 for key in ("estabilidade", "reserva", "controle_custos", "satisfacao", "pontuacao_geral"))
    assert rooms.public_state(code)["resumo_final"]["rodadas"] == 3


def test_expiration_and_server_deadline_are_enforced() -> None:
    rooms = manager()
    created = rooms.create_room()
    code, token = created["codigo"], created["presenter_token"]
    rooms.join(code, "participant-main", "P")
    rooms.start_round(code, token, "tempestade", 10)
    rooms.open_zone_vote(code, token)
    room = rooms._rooms[code]
    room.vote_ends_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    changed = rooms.tick()
    assert code in changed
    assert rooms.public_state(code)["votacao_bloqueada"] is True
    with pytest.raises(PhaseError):
        rooms.cast_vote(code, "participant-main", "zona", "zona_norte")
    room.last_activity = datetime.now(timezone.utc) - timedelta(minutes=2)
    assert code in rooms.expire_inactive()


def test_recommendation_incorporates_available_lstm_and_xgboost_as_analytical_context() -> None:
    rooms = RoomManager(
        SCENARIOS,
        public_app_url="http://192.168.0.10:5173",
        signal_provider=lambda zone: {
            "risco_lstm": "ALTO",
            "previsao_mw": 42.5,
            "risco_xgb": "MÉDIO",
            "confianca_xgb": 0.78,
        },
    )
    created = rooms.create_room()
    code, token = created["codigo"], created["presenter_token"]
    rooms.join(code, "participant-main", "P")
    rooms.start_round(code, token, "tempestade", None)
    rooms.open_zone_vote(code, token)
    rooms.cast_vote(code, "participant-main", "zona", "zona_norte")
    rooms.close_vote(code, token)
    rooms.open_action_vote(code, token)
    rooms.cast_vote(code, "participant-main", "acao", "usar_baterias")
    rooms.close_vote(code, token)
    state = rooms.reveal(code, token)
    assert "LSTM" in state["recomendacao"]["origem"]
    assert "XGBoost" in state["recomendacao"]["explicacao"]
    assert "não controla" in state["recomendacao"]["explicacao"]


def test_snapshot_message_is_typed_and_never_contains_token() -> None:
    rooms = manager()
    created = rooms.create_room()
    payload = rooms.message(created["codigo"], "sala_atualizada")
    assert payload["tipo"] == "sala_atualizada"
    assert payload["sala"]["codigo"] == created["codigo"]
    assert "presenter_token" not in payload["sala"]


def test_server_scores_alignment_and_two_stage_participation_with_round_feedback() -> None:
    rooms = manager()
    created = rooms.create_room()
    code, token = created["codigo"], created["presenter_token"]
    for participant in ("participant-one", "participant-two"):
        rooms.join(code, participant, participant)

    initial = rooms.public_state(code)["progressao"]
    assert initial == {
        "pontos_total": 0,
        "meta_pontos": 300,
        "progresso_pct": 0.0,
        "rodadas_concluidas": 0,
        "total_rodadas": 3,
        "bonus_alinhamento_total": 0,
        "bonus_participacao_total": 0,
        "feedback_rodada": None,
    }

    rooms.start_round(code, token, "tempestade", None)
    rooms.open_zone_vote(code, token)
    for participant in ("participant-one", "participant-two"):
        rooms.cast_vote(code, participant, "zona", "zona_norte")
    rooms.close_vote(code, token)
    rooms.open_action_vote(code, token)
    for participant in ("participant-one", "participant-two"):
        rooms.cast_vote(code, participant, "acao", "usar_baterias")
    rooms.close_vote(code, token)
    rooms.reveal(code, token)
    first = rooms.apply(code, token)

    assert first["progressao"]["pontos_total"] == 100
    assert first["progressao"]["progresso_pct"] == pytest.approx(33.3)
    assert first["progressao"]["feedback_rodada"] == {
        "rodada": 1,
        "pontos_base": 50,
        "bonus_alinhamento": 25,
        "bonus_participacao": 25,
        "pontos_rodada": 100,
        "pontos_total": 100,
        "participacao_pct": 100.0,
        "participantes_completos": 2,
        "participantes_elegiveis": 2,
        "alinhada_recomendacao": True,
        "mensagem": "Missão concluída com alinhamento e participação total.",
    }
    assert first["historico"][0]["pontos_jogo"] == 100

    rooms.start_round(code, token, "incendio", None)
    assert rooms.public_state(code)["contagens"] == {"zona": {}, "acao": {}}
    assert rooms.public_state(code)["historico"][0]["acao"] == "usar_baterias"
