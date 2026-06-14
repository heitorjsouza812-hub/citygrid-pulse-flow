from __future__ import annotations

import json
import time
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dados_citygrid.csv"
DECISIONS_PATH = ROOT / "logs" / "decisoes.jsonl"
GRAPHICS_DIR = ROOT / "graficos"
MODELS_DIR = ROOT / "modelos"

RISK_ORDER = ["BAIXO", "MEDIO", "ALTO", "CRITICO", "AGUARDANDO", "DESCONHECIDO"]
RISK_LABELS = {
    "BAIXO": "Baixo",
    "MEDIO": "Medio",
    "ALTO": "Alto",
    "CRITICO": "Critico",
    "AGUARDANDO": "Aguardando",
    "DESCONHECIDO": "Desconhecido",
}
RISK_COLORS = {
    "BAIXO": "#1D7A63",
    "MEDIO": "#C38A2D",
    "ALTO": "#C85B3C",
    "CRITICO": "#8E1F2F",
    "AGUARDANDO": "#7B8794",
    "DESCONHECIDO": "#556270",
}
ORIGIN_COLORS = {
    "heuristica": "#8E1F2F",
    "xgboost": "#125B78",
    "lstm": "#1D7A63",
    "genetico": "#8B6F47",
}
URGENCY_ORDER = ["BAIXA", "MEDIA", "ALTA", "CRITICA"]
URGENCY_LABELS = {
    "BAIXA": "Baixa",
    "MEDIA": "Media",
    "ALTA": "Alta",
    "CRITICA": "Critica",
}
URGENCY_COLORS = {
    "BAIXA": "#1D7A63",
    "MEDIA": "#C38A2D",
    "ALTA": "#C85B3C",
    "CRITICA": "#8E1F2F",
}


def apply_theme() -> None:
    st.set_page_config(
        page_title="CityGrid Brain | Dashboard Cientifico",
        page_icon="C",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --ink: #10212b;
            --muted: #5c7280;
            --navy: #0d1b2a;
            --teal: #125b78;
            --paper: rgba(255, 255, 255, 0.78);
            --line: rgba(16, 33, 43, 0.10);
            --shadow: 0 24px 60px rgba(13, 27, 42, 0.10);
            --hero-shadow: 0 30px 70px rgba(13, 27, 42, 0.24);
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(18, 91, 120, 0.14), transparent 28%),
                radial-gradient(circle at top right, rgba(200, 91, 60, 0.12), transparent 26%),
                linear-gradient(180deg, #f4ede3 0%, #f4f7f8 48%, #fcfbf8 100%);
            color: var(--ink);
            font-family: "Trebuchet MS", "Segoe UI", sans-serif;
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(248,249,246,0.94));
            border-right: 1px solid rgba(16, 33, 43, 0.08);
        }
        .block-container {
            max-width: 1450px;
            padding-top: 1.6rem;
            padding-bottom: 2.8rem;
        }
        h1, h2, h3 {
            font-family: "Georgia", "Palatino Linotype", serif;
            letter-spacing: -0.02em;
            color: var(--ink);
        }
        .hero-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.65fr) minmax(300px, 0.95fr);
            gap: 1.3rem;
            align-items: stretch;
        }
        .hero-copy {
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .hero {
            background:
                radial-gradient(circle at 12% 16%, rgba(255,255,255,0.12), transparent 20%),
                radial-gradient(circle at 86% 18%, rgba(255,255,255,0.10), transparent 18%),
            linear-gradient(135deg, rgba(13, 27, 42, 0.98), rgba(18, 91, 120, 0.96));
            color: #f8fbfd;
            border-radius: 28px;
            padding: 2.2rem 2.3rem;
            box-shadow: var(--hero-shadow);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .hero-kicker {
            display: inline-block;
            margin-bottom: 0.9rem;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.12);
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .hero h1 { margin: 0; color: #ffffff; font-size: 3rem; line-height: 1.04; }
        .hero p {
            max-width: 880px;
            margin: 0.9rem 0 0;
            color: rgba(248, 251, 253, 0.86);
            font-size: 1.06rem;
            line-height: 1.65;
        }
        .pill-row { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 1.25rem; }
        .pill {
            padding: 0.42rem 0.8rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.15);
            font-size: 0.9rem;
        }
        .hero-metrics {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.85rem;
        }
        .hero-stat {
            border-radius: 22px;
            padding: 1rem 1rem 0.95rem;
            background: linear-gradient(180deg, rgba(255,255,255,0.15), rgba(255,255,255,0.06));
            border: 1px solid rgba(255,255,255,0.12);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
            min-height: 120px;
        }
        .hero-stat strong {
            display: block;
            color: #ffffff;
            font-size: 1.65rem;
            line-height: 1;
        }
        .hero-stat span {
            display: block;
            color: rgba(248, 251, 253, 0.78);
            margin-top: 0.35rem;
            font-size: 0.84rem;
            line-height: 1.45;
        }
        .cta-banner {
            margin-top: 1rem;
            padding: 0.95rem 1rem;
            border-radius: 18px;
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.13);
            color: rgba(248, 251, 253, 0.86);
            font-size: 0.92rem;
            line-height: 1.55;
        }
        .section-shell {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 24px;
            box-shadow: var(--shadow);
            padding: 1.2rem 1.25rem 1.1rem;
            backdrop-filter: blur(10px);
        }
        .section-title { margin-bottom: 0.25rem; font-size: 1.38rem; }
        .section-note { color: var(--muted); margin-bottom: 0.95rem; font-size: 0.94rem; }
        .product-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.95rem;
        }
        .product-card {
            padding: 1.15rem 1.05rem 1rem;
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(248,250,249,0.90));
            border: 1px solid rgba(16, 33, 43, 0.08);
            box-shadow: 0 18px 36px rgba(13, 27, 42, 0.06);
            min-height: 210px;
        }
        .product-card h4 {
            margin: 0 0 0.55rem;
            color: var(--navy);
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 1.12rem;
        }
        .product-card p {
            margin: 0;
            color: var(--muted);
            line-height: 1.62;
            font-size: 0.93rem;
        }
        .product-card strong {
            display: block;
            margin-top: 0.95rem;
            color: var(--teal);
            font-size: 0.88rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .readiness-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.8rem;
        }
        .readiness-item {
            padding: 0.95rem 0.95rem 0.88rem;
            border-radius: 18px;
            background: rgba(13, 27, 42, 0.04);
            border: 1px solid rgba(16, 33, 43, 0.07);
        }
        .readiness-item strong {
            display: block;
            color: var(--navy);
            font-size: 0.95rem;
            margin-bottom: 0.2rem;
        }
        .readiness-item span {
            color: var(--muted);
            font-size: 0.85rem;
            line-height: 1.45;
        }
        .segment-card {
            padding: 1rem 1rem 0.95rem;
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(247,248,246,0.90));
            border: 1px solid rgba(16, 33, 43, 0.08);
            min-height: 175px;
            box-shadow: 0 16px 34px rgba(13, 27, 42, 0.05);
        }
        .segment-card h4 {
            margin: 0 0 0.45rem;
            color: var(--navy);
            font-family: "Georgia", "Palatino Linotype", serif;
        }
        .segment-card p {
            margin: 0;
            color: var(--muted);
            line-height: 1.58;
            font-size: 0.92rem;
        }
        .capability-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
        }
        .capability-chip {
            padding: 0.42rem 0.75rem;
            border-radius: 999px;
            background: rgba(18, 91, 120, 0.08);
            border: 1px solid rgba(18, 91, 120, 0.14);
            color: var(--teal);
            font-size: 0.82rem;
            font-weight: 600;
        }
        .architecture-flow {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
        }
        .architecture-node {
            position: relative;
            padding: 1rem 0.95rem 0.92rem;
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(246,248,248,0.92));
            border: 1px solid rgba(16, 33, 43, 0.08);
            box-shadow: 0 16px 36px rgba(13, 27, 42, 0.05);
            min-height: 150px;
        }
        .architecture-node h4 {
            margin: 0 0 0.45rem;
            color: var(--navy);
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 1rem;
        }
        .architecture-node p {
            margin: 0;
            color: var(--muted);
            line-height: 1.56;
            font-size: 0.9rem;
        }
        .impact-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
        }
        .impact-card {
            padding: 1rem 0.95rem;
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(13, 27, 42, 0.96), rgba(18, 91, 120, 0.94));
            color: #f8fbfd;
            box-shadow: 0 18px 36px rgba(13, 27, 42, 0.12);
        }
        .impact-card strong {
            display: block;
            font-size: 1.8rem;
            line-height: 1;
        }
        .impact-card span {
            display: block;
            margin-top: 0.4rem;
            color: rgba(248, 251, 253, 0.80);
            font-size: 0.85rem;
            line-height: 1.46;
        }
        .narrative {
            padding: 1rem 1.05rem;
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(18,91,120,0.08), rgba(184,137,51,0.08));
            border: 1px solid rgba(16, 33, 43, 0.08);
            color: var(--ink);
            line-height: 1.6;
        }
        .zone-card {
            background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(248,250,249,0.90));
            border: 1px solid rgba(16, 33, 43, 0.09);
            border-radius: 22px;
            padding: 1rem 1rem 0.95rem;
            box-shadow: 0 16px 34px rgba(13, 27, 42, 0.06);
            min-height: 210px;
        }
        .zone-top { display: flex; align-items: center; justify-content: space-between; gap: 0.8rem; }
        .zone-name {
            color: var(--ink);
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 1.16rem;
            margin: 0;
        }
        .zone-risk {
            color: white;
            border-radius: 999px;
            padding: 0.28rem 0.65rem;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .zone-main { display: flex; gap: 0.85rem; align-items: baseline; margin-top: 0.8rem; }
        .zone-main strong { font-size: 2rem; line-height: 1; color: var(--navy); }
        .zone-sub { color: var(--muted); font-size: 0.88rem; }
        .zone-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
            margin-top: 0.95rem;
        }
        .zone-grid div {
            padding: 0.7rem 0.75rem;
            border-radius: 16px;
            background: rgba(13, 27, 42, 0.04);
        }
        .zone-grid span { display: block; font-size: 0.78rem; color: var(--muted); margin-top: 0.12rem; }
        .method-card {
            padding: 1rem 1rem 0.92rem;
            border-radius: 18px;
            min-height: 155px;
            background: rgba(255,255,255,0.88);
            border: 1px solid rgba(16,33,43,0.08);
            box-shadow: 0 12px 26px rgba(13, 27, 42, 0.05);
        }
        .method-card h4 {
            margin: 0 0 0.5rem;
            color: var(--navy);
            font-family: "Georgia", "Palatino Linotype", serif;
            font-size: 1.02rem;
        }
        .method-card p { color: var(--muted); font-size: 0.92rem; line-height: 1.55; margin: 0; }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(16,33,43,0.08);
            padding: 1rem 1rem 0.9rem;
            border-radius: 20px;
            box-shadow: 0 14px 30px rgba(13, 27, 42, 0.05);
        }
        .footnote { color: var(--muted); font-size: 0.86rem; line-height: 1.5; }
        .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            background: rgba(255,255,255,0.58);
            border: 1px solid rgba(16,33,43,0.08);
            padding-left: 1rem;
            padding-right: 1rem;
        }
        @media (max-width: 1100px) {
            .hero-grid,
            .product-grid,
            .readiness-grid,
            .architecture-flow,
            .impact-grid {
                grid-template-columns: 1fr;
            }
            .hero-metrics {
                grid-template-columns: 1fr 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def fix_mojibake(value):
    if not isinstance(value, str):
        return value
    if any(token in value for token in ("Ã", "â", "€", "œ", "�")):
        try:
            return value.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    return value


def normalize_risk(value: str) -> str:
    text = str(fix_mojibake(value or "")).strip().upper()
    mapping = {
        "BAIXO": "BAIXO",
        "MEDIO": "MEDIO",
        "MÉDIO": "MEDIO",
        "ALTO": "ALTO",
        "CRITICO": "CRITICO",
        "CRÍTICO": "CRITICO",
        "AGUARDANDO": "AGUARDANDO",
        "DESCONHECIDO": "DESCONHECIDO",
    }
    return mapping.get(text, text or "DESCONHECIDO")


def normalize_urgency(value: str) -> str:
    text = str(fix_mojibake(value or "")).strip().upper()
    mapping = {
        "BAIXA": "BAIXA",
        "MEDIA": "MEDIA",
        "MÉDIA": "MEDIA",
        "ALTA": "ALTA",
        "ALTO": "ALTA",
        "CRITICA": "CRITICA",
        "CRÍTICA": "CRITICA",
        "CRITICO": "CRITICA",
        "CRÍTICO": "CRITICA",
        "MEDIO": "MEDIA",
        "MÉDIO": "MEDIA",
    }
    return mapping.get(text, text or "MEDIA")


def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    object_cols = out.select_dtypes(include="object").columns
    for col in object_cols:
        out[col] = out[col].map(fix_mojibake)
    if "risco" in out.columns:
        out["risco"] = out["risco"].map(normalize_risk)
    if "urgencia" in out.columns:
        out["urgencia"] = out["urgencia"].map(normalize_urgency)
    if "origem" in out.columns:
        out["origem"] = out["origem"].astype(str).str.lower()
    return out


@st.cache_data(ttl=8, show_spinner=False)
def load_operational_data(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df = normalize_frame(df)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    numeric_cols = [
        "ciclo",
        "consumo_mw",
        "consumo_liquido_mw",
        "capacidade_mw",
        "pct_carga",
        "geracao_total_mw",
        "autoprod_pct",
        "pot_ativa_kw",
        "fator_potencia",
        "frequencia_hz",
        "tensao_media_v",
        "desequilibrio_tensao_pct",
        "thd_tensao_pct",
        "ve_ocupacao_pct",
        "ve_demanda_kw",
        "bat_soc_pct",
        "bat_disponivel_mwh",
        "clima_temp_c",
        "clima_umidade_pct",
        "clima_irrad_wm2",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["ciclo"]).reset_index(drop=True)


@st.cache_data(ttl=8, show_spinner=False)
def load_decisions(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = normalize_frame(df)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if "confianca" in df.columns:
        df["confianca"] = pd.to_numeric(df["confianca"], errors="coerce")
    return df.reset_index(drop=True)


def load_graphs() -> list[Path]:
    if not GRAPHICS_DIR.exists():
        return []
    preferred_order = [
        "comparativo_final.png",
        "comparativo_modelos.png",
        "xgboost_resultados.png",
        "lstm_resultados.png",
        "lstm_real_vs_predito.png",
        "lstm_loss_por_zona.png",
        "lstm_comparativo_zonas.png",
    ]
    existing = []
    for name in preferred_order:
        graph = GRAPHICS_DIR / name
        if graph.exists():
            existing.append(graph)
    return existing


def build_cycle_view(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grouped = (
        df.groupby("ciclo", as_index=False)
        .agg(
            timestamp=("timestamp", "max"),
            consumo_total_mw=("consumo_mw", "sum"),
            consumo_liquido_mw=("consumo_liquido_mw", "sum"),
            geracao_total_mw=("geracao_total_mw", "sum"),
            carga_media_pct=("pct_carga", "mean"),
            zonas_monitoradas=("zona_id", "nunique"),
            criticos=("risco", lambda s: (s == "CRITICO").sum()),
            altos=("risco", lambda s: (s == "ALTO").sum()),
            anomalias=("anomalia_tipo", lambda s: s.notna().sum() if hasattr(s, "notna") else 0),
        )
        .sort_values("ciclo")
    )
    grouped["renovavel_pct"] = np.where(
        grouped["consumo_total_mw"] > 0,
        grouped["geracao_total_mw"] / grouped["consumo_total_mw"] * 100,
        0,
    )
    return grouped


def build_risk_history(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ciclo", "risco", "total"])
    risk_counts = df.groupby(["ciclo", "risco"]).size().reset_index(name="total")
    risk_counts["risco_label"] = risk_counts["risco"].map(RISK_LABELS).fillna(risk_counts["risco"])
    return risk_counts


def build_decision_story(current_df: pd.DataFrame, decisions_df: pd.DataFrame) -> str:
    if current_df.empty:
        return "O painel ainda nao recebeu leituras suficientes para gerar uma narrativa operacional."
    criticos = int((current_df["risco"] == "CRITICO").sum())
    altos = int((current_df["risco"] == "ALTO").sum())
    pico = float(current_df["pct_carga"].max())
    zona_pico = current_df.sort_values("pct_carga", ascending=False).iloc[0]["zona_nome"]
    renovavel = current_df["geracao_total_mw"].sum() / max(current_df["consumo_mw"].sum(), 1e-6) * 100
    if decisions_df.empty:
        decision_sentence = "Nao ha decisoes registradas no log ate o momento."
    else:
        latest = decisions_df.sort_values("timestamp").iloc[-1]
        confidence = latest.get("confianca")
        conf_text = f"{confidence * 100:.1f}%" if pd.notna(confidence) else "n/d"
        decision_sentence = (
            f"A ultima recomendacao registrada foi '{latest.get('tipo', 'n/d')}' "
            f"na zona {latest.get('zona_alvo', 'n/d')}, com confianca de {conf_text}."
        )
    return (
        f"No ciclo mais recente, o sistema monitora {len(current_df)} zonas com pico de carga de "
        f"{pico:.1f}% em {zona_pico}. Ha {criticos} zonas em estado critico e {altos} em alto risco, "
        f"enquanto a participacao renovavel instantanea alcanca {renovavel:.1f}% da demanda. "
        f"{decision_sentence}"
    )


def create_download_payload(df: pd.DataFrame) -> bytes:
    if df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")


def build_product_snapshot(data_df: pd.DataFrame, cycle_df: pd.DataFrame, current_df: pd.DataFrame, decisions_df: pd.DataFrame) -> dict:
    total_cycles = int(data_df["ciclo"].max()) if not data_df.empty else 0
    zones = int(data_df["zona_id"].nunique()) if not data_df.empty else 0
    decisions = int(len(decisions_df))
    avg_renew = float(cycle_df["renovavel_pct"].mean()) if not cycle_df.empty else 0.0
    load_mean = float(cycle_df["consumo_total_mw"].mean()) if not cycle_df.empty else 0.0
    high_pressure_cycles = int(((cycle_df["criticos"] + cycle_df["altos"]) > 0).sum()) if not cycle_df.empty else 0
    automation_rate = decisions / max(total_cycles, 1)
    current_high_risk = int(current_df["risco"].isin(["ALTO", "CRITICO"]).sum()) if not current_df.empty else 0
    return {
        "total_cycles": total_cycles,
        "zones": zones,
        "decisions": decisions,
        "avg_renew": avg_renew,
        "load_mean": load_mean,
        "high_pressure_cycles": high_pressure_cycles,
        "automation_rate": automation_rate,
        "current_high_risk": current_high_risk,
    }


def render_hero(data_df: pd.DataFrame, decisions_df: pd.DataFrame) -> None:
    total_cycles = int(data_df["ciclo"].max()) if not data_df.empty else 0
    latest_ts = (
        data_df["timestamp"].max().strftime("%d/%m/%Y %H:%M:%S")
        if not data_df.empty and pd.notna(data_df["timestamp"].max())
        else "Sem dados"
    )
    total_decisions = len(decisions_df) if not decisions_df.empty else 0
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-kicker">Smart Grid Analytics • Pesquisa Aplicada • Demonstracao Executiva</div>
            <h1>CityGrid Brain</h1>
            <p>
                Plataforma de observabilidade urbana para monitoramento energetico, analise preditiva
                e suporte a decisoes em redes inteligentes. O painel combina leituras IoT, inferencia
                hibrida com XGBoost + LSTM e a trilha de acoes do motor de decisao em uma experiencia
                adequada para apresentacao cientifica e feira de tecnologia.
            </p>
            <div class="pill-row">
                <div class="pill">Ciclos monitorados: <strong>{total_cycles}</strong></div>
                <div class="pill">Ultima atualizacao: <strong>{latest_ts}</strong></div>
                <div class="pill">Decisoes registradas: <strong>{total_decisions}</strong></div>
                <div class="pill">Pipeline: <strong>Kafka • IA Hibrida • Analitica Operacional</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_product_hero(data_df: pd.DataFrame, decisions_df: pd.DataFrame) -> None:
    total_cycles = int(data_df["ciclo"].max()) if not data_df.empty else 0
    latest_ts = (
        data_df["timestamp"].max().strftime("%d/%m/%Y %H:%M:%S")
        if not data_df.empty and pd.notna(data_df["timestamp"].max())
        else "Sem dados"
    )
    total_decisions = len(decisions_df) if not decisions_df.empty else 0
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-grid">
                <div class="hero-copy">
                    <div class="hero-kicker">Smart Grid Analytics | AI Decision Layer | Demonstracao Executiva</div>
                    <h1>CityGrid Brain</h1>
                    <p>
                        Plataforma de inteligencia operacional para redes urbanas de energia. Em uma unica
                        interface, o produto combina observabilidade multizona, previsao de risco, recomendacao
                        automatizada e evidencias para tomada de decisao em ambientes criticos.
                    </p>
                    <div class="pill-row">
                        <div class="pill">Ciclos monitorados: <strong>{total_cycles}</strong></div>
                        <div class="pill">Ultima atualizacao: <strong>{latest_ts}</strong></div>
                        <div class="pill">Decisoes registradas: <strong>{total_decisions}</strong></div>
                        <div class="pill">Pipeline: <strong>Kafka | IA Hibrida | Analitica Operacional</strong></div>
                    </div>
                    <div class="cta-banner">
                        Posicionamento de produto: CityGrid Brain funciona como uma camada de decisao para
                        concessionarias, campi, aeroportos, distritos inteligentes e operacoes energeticas
                        que precisam reduzir risco, aumentar visibilidade e acelerar resposta.
                    </div>
                </div>
                <div class="hero-metrics">
                    <div class="hero-stat">
                        <strong>{total_cycles}</strong>
                        <span>ciclos historicos prontos para demonstracao operacional e analitica.</span>
                    </div>
                    <div class="hero-stat">
                        <strong>{total_decisions}</strong>
                        <span>decisoes auditaveis registradas pelo motor hibrido.</span>
                    </div>
                    <div class="hero-stat">
                        <strong>4 camadas</strong>
                        <span>heuristicas, XGBoost, LSTM e otimizacao genetica no mesmo fluxo.</span>
                    </div>
                    <div class="hero-stat">
                        <strong>Pronto para feira</strong>
                        <span>narrativa de produto, operacao em tempo real e evidencias para artigo.</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_product_positioning(snapshot: dict, graphs: list[Path]) -> None:
    st.markdown(
        f"""
        <div class="product-grid">
            <div class="product-card">
                <h4>Visibilidade operacional de alto nivel</h4>
                <p>
                    A plataforma transforma telemetria dispersa em um cockpit executivo capaz de mostrar
                    pressao de carga, risco, qualidade de energia, baterias, recarga de VEs e participacao
                    renovavel em tempo quase real.
                </p>
                <strong>{snapshot['zones']} zonas ativas e {snapshot['total_cycles']} ciclos historicos</strong>
            </div>
            <div class="product-card">
                <h4>IA aplicada ao centro de operacoes</h4>
                <p>
                    Em vez de apenas exibir alarmes, o produto classifica risco atual, antecipa degradacao
                    de consumo e organiza resposta priorizada para operadores, gestores e ambientes criticos.
                </p>
                <strong>{snapshot['decisions']} decisoes registradas | {snapshot['automation_rate']:.2f} acoes por ciclo</strong>
            </div>
            <div class="product-card">
                <h4>Linguagem de venda sem perder rigor tecnico</h4>
                <p>
                    O mesmo ambiente sustenta pitch comercial, demonstracao institucional e defesa
                    cientifica, com galeria dos experimentos, base exportavel e trilha auditavel das acoes.
                </p>
                <strong>{len(graphs)} artefatos analiticos prontos para apresentacao</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        """
        <div class="capability-row">
            <span class="capability-chip">Observabilidade multizona</span>
            <span class="capability-chip">Motor de decisao hibrido</span>
            <span class="capability-chip">Pronto para Kafka</span>
            <span class="capability-chip">Logs auditaveis</span>
            <span class="capability-chip">Modelos versionados</span>
            <span class="capability-chip">Exportacao para evidencias</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_readiness(snapshot: dict, graphs: list[Path]) -> None:
    st.markdown(
        f"""
        <div class="readiness-grid">
            <div class="readiness-item">
                <strong>Streaming operacional</strong>
                <span>Integrado ao fluxo Kafka para alimentacao continua do motor e do painel.</span>
            </div>
            <div class="readiness-item">
                <strong>Stack de IA aplicada</strong>
                <span>4 camadas decisorias combinadas em uma narrativa unica de produto.</span>
            </div>
            <div class="readiness-item">
                <strong>Evidencia analitica</strong>
                <span>{len(graphs)} figuras de avaliacao e base historica pronta para exposicao.</span>
            </div>
            <div class="readiness-item">
                <strong>Operacao vendavel</strong>
                <span>{snapshot['high_pressure_cycles']} ciclos com pressao operacional ajudam a contar valor real do produto.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_architecture() -> None:
    st.markdown(
        """
        <div class="architecture-flow">
            <div class="architecture-node">
                <h4>1. Camada de campo</h4>
                <p>Medidores, sensores, estacoes de recarga, baterias e sinais de clima alimentam o ecossistema de dados energeticos.</p>
            </div>
            <div class="architecture-node">
                <h4>2. Streaming e ingestao</h4>
                <p>Kafka organiza o fluxo continuo de leituras para desacoplar captura, analise e persistencia operacional.</p>
            </div>
            <div class="architecture-node">
                <h4>3. Motor de inteligencia</h4>
                <p>Heuristicas, XGBoost, LSTM e otimizacao genetica transformam dados em recomendacoes priorizadas.</p>
            </div>
            <div class="architecture-node">
                <h4>4. Cockpit executivo</h4>
                <p>O dashboard expoe visao para operadores, gestao, inovacao, comercial e frentes de demonstracao institucional.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_market_fit() -> None:
    st.markdown(
        """
        <div class="product-grid">
            <div class="segment-card">
                <h4>Concessionarias e distribuidoras</h4>
                <p>
                    Valor principal: priorizacao de risco, leitura de sobrecarga, qualidade de energia e
                    coordenacao de resposta para centros de operacao e areas de inovacao digital.
                </p>
            </div>
            <div class="segment-card">
                <h4>Campi, aeroportos e parques tecnologicos</h4>
                <p>
                    Valor principal: visibilidade consolidada da infraestrutura eletrica, protecao de ativos
                    criticos e inteligencia para cargas sensiveis, recarga eletrica e armazenamento.
                </p>
            </div>
            <div class="segment-card">
                <h4>Distritos e smart cities</h4>
                <p>
                    Valor principal: painel de cidade energetica com narrativa forte para investimento,
                    inovacao urbana, ESG e digital twins de operacao.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_delivery_models() -> None:
    st.markdown(
        """
        <div class="product-grid">
            <div class="segment-card">
                <h4>Entrega como plataforma de operacao</h4>
                <p>
                    Modelo indicado para centros de operacao e torres de monitoramento que precisam de
                    dashboard executivo, telemetria consolidada e camada de decisao contínua.
                </p>
            </div>
            <div class="segment-card">
                <h4>Entrega como piloto de inovacao</h4>
                <p>
                    Modelo indicado para programas de P&D, laboratorios vivos, distritos inteligentes e
                    demonstracoes institucionais com narrativa forte de cidade conectada e energia digital.
                </p>
            </div>
            <div class="segment-card">
                <h4>Entrega como camada analitica</h4>
                <p>
                    Modelo indicado para clientes que ja possuem sistemas legados e querem adicionar IA,
                    orquestracao de risco e visão executiva sem reescrever toda a operacao existente.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_commercial_impact(snapshot: dict, current_df: pd.DataFrame) -> None:
    pressure_share = (
        snapshot["high_pressure_cycles"] / max(snapshot["total_cycles"], 1) * 100
        if snapshot["total_cycles"] > 0
        else 0.0
    )
    flexible_load = float(current_df[current_df["risco"].isin(["ALTO", "CRITICO"])]["consumo_mw"].sum()) if not current_df.empty else 0.0
    st.markdown(
        f"""
        <div class="impact-grid">
            <div class="impact-card">
                <strong>{snapshot['load_mean']:.1f} MW</strong>
                <span>demanda media sob observabilidade da plataforma no recorte filtrado.</span>
            </div>
            <div class="impact-card">
                <strong>{snapshot['avg_renew']:.1f}%</strong>
                <span>participacao renovavel media acompanhada para narrativa ESG e eficiencia.</span>
            </div>
            <div class="impact-card">
                <strong>{pressure_share:.1f}%</strong>
                <span>dos ciclos com sinais de alta pressao operacional ou risco elevado.</span>
            </div>
            <div class="impact-card">
                <strong>{flexible_load:.1f} MW</strong>
                <span>carga atualmente em zonas de maior risco, candidata a resposta e reorquestracao.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="section-shell">
            <div class="section-title">{title}</div>
            <div class="section-note">{note}</div>
        """,
        unsafe_allow_html=True,
    )


def close_section() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_zone_cards(current_df: pd.DataFrame) -> None:
    if current_df.empty:
        st.info("Nenhuma zona disponivel para exibir no ciclo selecionado.")
        return
    ordered = current_df.copy()
    ordered["risk_rank"] = ordered["risco"].map({risk: idx for idx, risk in enumerate(RISK_ORDER)}).fillna(99)
    ordered = ordered.sort_values(["risk_rank", "pct_carga"], ascending=[False, False])
    for row_group in range(0, len(ordered), 4):
        cols = st.columns(4)
        for col, (_, row) in zip(cols, ordered.iloc[row_group: row_group + 4].iterrows()):
            risk = row["risco"]
            with col:
                st.markdown(
                    f"""
                    <div class="zone-card">
                        <div class="zone-top">
                            <h4 class="zone-name">{row['zona_nome']}</h4>
                            <span class="zone-risk" style="background:{RISK_COLORS.get(risk, '#556270')};">
                                {RISK_LABELS.get(risk, risk)}
                            </span>
                        </div>
                        <div class="zone-main">
                            <strong>{row['pct_carga']:.1f}%</strong>
                            <div class="zone-sub">ocupacao relativa da capacidade instalada</div>
                        </div>
                        <div class="zone-grid">
                            <div><strong>{row['consumo_mw']:.2f} MW</strong><span>demanda atual</span></div>
                            <div><strong>{row['geracao_total_mw']:.2f} MW</strong><span>geracao renovavel</span></div>
                            <div><strong>{row.get('bat_soc_pct', 0):.1f}%</strong><span>estado da bateria</span></div>
                            <div><strong>{row.get('ve_ocupacao_pct', 0):.1f}%</strong><span>ocupacao dos VEs</span></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_charts(cycle_df: pd.DataFrame, risk_history: pd.DataFrame, current_df: pd.DataFrame) -> None:
    chart_cols = st.columns([1.35, 1])
    with chart_cols[0]:
        if not cycle_df.empty:
            melted = cycle_df.melt(
                id_vars=["ciclo", "timestamp"],
                value_vars=["consumo_total_mw", "geracao_total_mw", "consumo_liquido_mw"],
                var_name="serie",
                value_name="mw",
            )
            melted["serie_label"] = melted["serie"].map(
                {
                    "consumo_total_mw": "Consumo total",
                    "geracao_total_mw": "Geracao renovavel",
                    "consumo_liquido_mw": "Consumo liquido",
                }
            )
            line = (
                alt.Chart(melted)
                .mark_line(point=True, strokeWidth=3)
                .encode(
                    x=alt.X("ciclo:Q", title="Ciclo"),
                    y=alt.Y("mw:Q", title="MW"),
                    color=alt.Color(
                        "serie_label:N",
                        scale=alt.Scale(
                            domain=["Consumo total", "Geracao renovavel", "Consumo liquido"],
                            range=["#0d1b2a", "#1d7a63", "#c85b3c"],
                        ),
                        title="Serie",
                    ),
                    tooltip=[
                        alt.Tooltip("ciclo:Q", title="Ciclo"),
                        alt.Tooltip("serie_label:N", title="Serie"),
                        alt.Tooltip("mw:Q", title="MW", format=".2f"),
                        alt.Tooltip("timestamp:T", title="Timestamp"),
                    ],
                )
                .properties(height=340)
            )
            st.altair_chart(line, use_container_width=True)
        else:
            st.info("Sem historico suficiente para o grafico de demanda.")
    with chart_cols[1]:
        if not risk_history.empty:
            risk_chart = (
                alt.Chart(risk_history)
                .mark_area(opacity=0.85)
                .encode(
                    x=alt.X("ciclo:Q", title="Ciclo"),
                    y=alt.Y("total:Q", stack="zero", title="Zonas"),
                    color=alt.Color(
                        "risco_label:N",
                        scale=alt.Scale(
                            domain=[RISK_LABELS[r] for r in RISK_ORDER if r in RISK_LABELS],
                            range=[RISK_COLORS[r] for r in RISK_ORDER if r in RISK_COLORS],
                        ),
                        title="Risco",
                    ),
                    tooltip=[
                        alt.Tooltip("ciclo:Q", title="Ciclo"),
                        alt.Tooltip("risco_label:N", title="Risco"),
                        alt.Tooltip("total:Q", title="Zonas"),
                    ],
                )
                .properties(height=340)
            )
            st.altair_chart(risk_chart, use_container_width=True)
        else:
            st.info("Sem historico suficiente para o grafico de risco.")
    bottom_cols = st.columns(2)
    with bottom_cols[0]:
        if not current_df.empty:
            current_plot = current_df.copy()
            current_plot["risco_label"] = current_plot["risco"].map(RISK_LABELS)
            bar = (
                alt.Chart(current_plot)
                .mark_bar(cornerRadiusTopRight=7, cornerRadiusBottomRight=7)
                .encode(
                    x=alt.X("pct_carga:Q", title="Carga relativa (%)"),
                    y=alt.Y("zona_nome:N", sort="-x", title="Zona"),
                    color=alt.Color(
                        "risco_label:N",
                        scale=alt.Scale(
                            domain=[RISK_LABELS[r] for r in RISK_ORDER if r in RISK_LABELS],
                            range=[RISK_COLORS[r] for r in RISK_ORDER if r in RISK_COLORS],
                        ),
                        title="Risco",
                    ),
                    tooltip=[
                        alt.Tooltip("zona_nome:N", title="Zona"),
                        alt.Tooltip("pct_carga:Q", title="% carga", format=".1f"),
                        alt.Tooltip("consumo_mw:Q", title="MW", format=".2f"),
                        alt.Tooltip("risco_label:N", title="Risco"),
                    ],
                )
                .properties(height=340)
            )
            st.altair_chart(bar, use_container_width=True)
        else:
            st.info("Sem snapshot atual para o grafico por zona.")
    with bottom_cols[1]:
        if not current_df.empty:
            scatter = (
                alt.Chart(current_df)
                .mark_circle(opacity=0.9, stroke="#ffffff", strokeWidth=1.5)
                .encode(
                    x=alt.X("pot_ativa_kw:Q", title="Potencia ativa (kW)"),
                    y=alt.Y("fator_potencia:Q", title="Fator de potencia"),
                    size=alt.Size("ve_ocupacao_pct:Q", title="% ocupacao VE", scale=alt.Scale(range=[120, 1000])),
                    color=alt.Color(
                        "risco:N",
                        scale=alt.Scale(domain=list(RISK_COLORS.keys()), range=list(RISK_COLORS.values())),
                        title="Risco",
                    ),
                    tooltip=[
                        alt.Tooltip("zona_nome:N", title="Zona"),
                        alt.Tooltip("pot_ativa_kw:Q", title="kW", format=".0f"),
                        alt.Tooltip("fator_potencia:Q", title="FP", format=".3f"),
                        alt.Tooltip("ve_ocupacao_pct:Q", title="VE %", format=".1f"),
                    ],
                )
                .properties(height=340)
            )
            st.altair_chart(scatter, use_container_width=True)
        else:
            st.info("Sem dados suficientes para o grafico de qualidade e mobilidade.")


def render_kpis(current_df: pd.DataFrame, cycle_df: pd.DataFrame, decisions_df: pd.DataFrame) -> None:
    if current_df.empty:
        st.warning("Nao ha snapshot operacional para exibir os indicadores.")
        return
    latest_total = current_df["consumo_mw"].sum()
    latest_renew = current_df["geracao_total_mw"].sum()
    renew_share = latest_renew / max(latest_total, 1e-6) * 100
    avg_pf = current_df["fator_potencia"].mean()
    avg_freq = current_df["frequencia_hz"].mean()
    avg_soc = current_df["bat_soc_pct"].mean()
    high_risk = int(current_df["risco"].isin(["ALTO", "CRITICO"]).sum())
    latest_cycle = int(current_df["ciclo"].max())
    total_actions = len(decisions_df) if not decisions_df.empty else 0
    previous_df = cycle_df[cycle_df["ciclo"] == latest_cycle - 1]
    delta_load = None
    if not previous_df.empty:
        delta_load = latest_total - previous_df["consumo_total_mw"].iloc[0]
    metrics = st.columns(6)
    metrics[0].metric("Demanda instantanea", f"{latest_total:.2f} MW", None if delta_load is None else f"{delta_load:+.2f} MW")
    metrics[1].metric("Participacao renovavel", f"{renew_share:.1f}%")
    metrics[2].metric("Zonas em alto risco", f"{high_risk}")
    metrics[3].metric("Fator de potencia medio", f"{avg_pf:.3f}")
    metrics[4].metric("Frequencia media", f"{avg_freq:.3f} Hz")
    metrics[5].metric("Estado medio das baterias", f"{avg_soc:.1f}%")
    stats = st.columns(3)
    stats[0].metric("Ciclo exibido", f"{latest_cycle}")
    stats[1].metric("Acoes registradas", f"{total_actions}")
    stats[2].metric("Zonas monitoradas", f"{current_df['zona_id'].nunique()}")


def render_decision_panel(decisions_df: pd.DataFrame) -> None:
    if decisions_df.empty:
        st.info("O log de decisoes ainda nao possui registros para exibir.")
        return
    decision_cols = st.columns([1, 1.1])
    with decision_cols[0]:
        origin = decisions_df.groupby("origem").size().reset_index(name="total").sort_values("total", ascending=False)
        origin["cor"] = origin["origem"].map(ORIGIN_COLORS).fillna("#556270")
        chart = (
            alt.Chart(origin)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
            .encode(
                x=alt.X("origem:N", title="Origem da decisao"),
                y=alt.Y("total:Q", title="Ocorrencias"),
                color=alt.Color("origem:N", scale=alt.Scale(domain=origin["origem"].tolist(), range=origin["cor"].tolist()), legend=None),
                tooltip=[alt.Tooltip("origem:N", title="Origem"), alt.Tooltip("total:Q", title="Total")],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)
    with decision_cols[1]:
        urgency = decisions_df.groupby("urgencia").size().reset_index(name="total")
        urgency["urgencia_label"] = urgency["urgencia"].map(URGENCY_LABELS).fillna(urgency["urgencia"])
        donut = (
            alt.Chart(urgency)
            .mark_arc(innerRadius=70, outerRadius=120)
            .encode(
                theta=alt.Theta("total:Q"),
                color=alt.Color(
                    "urgencia_label:N",
                    scale=alt.Scale(
                        domain=[URGENCY_LABELS[r] for r in URGENCY_ORDER if r in URGENCY_LABELS],
                        range=[URGENCY_COLORS[r] for r in URGENCY_ORDER if r in URGENCY_COLORS],
                    ),
                    title="Urgencia",
                ),
                tooltip=[alt.Tooltip("urgencia_label:N", title="Urgencia"), alt.Tooltip("total:Q", title="Total")],
            )
            .properties(height=300)
        )
        st.altair_chart(donut, use_container_width=True)
    latest = decisions_df.sort_values("timestamp", ascending=False).head(12).copy()
    latest["horario"] = latest["timestamp"].dt.strftime("%d/%m %H:%M")
    latest["urgencia_label"] = latest["urgencia"].map(URGENCY_LABELS).fillna(latest["urgencia"])
    latest = latest[["horario", "tipo", "origem", "urgencia_label", "zona_alvo", "confianca", "descricao"]].rename(
        columns={
            "horario": "Horario",
            "tipo": "Tipo",
            "origem": "Origem",
            "urgencia_label": "Urgencia",
            "zona_alvo": "Zona",
            "confianca": "Confianca",
            "descricao": "Descricao",
        }
    )
    st.dataframe(latest, use_container_width=True, hide_index=True)


def render_methodology() -> None:
    cols = st.columns(4)
    content = [
        ("1. Ingestao de dados", "Leituras sinteticas de distribuicao urbana sao publicadas em Kafka com informacoes de carga, qualidade de energia, armazenamento, recarga de VEs, clima e eventos."),
        ("2. Analise preditiva", "O XGBoost classifica o risco corrente por zona, enquanto o LSTM estima a evolucao de consumo em horizonte curto para acionar medidas preventivas."),
        ("3. Decisao operacional", "Heuristicas de seguranca e um algoritmo genetico priorizam resposta critica, redistribuicao de carga e preservacao de servicos essenciais."),
        ("4. Evidencia cientifica", "O mesmo painel reune operacao em tempo real, imagens de avaliacao do treinamento e trilha auditavel das decisoes para demonstracao e artigo."),
    ]
    for col, (title, text) in zip(cols, content):
        with col:
            st.markdown(
                f"""
                <div class="method-card">
                    <h4>{title}</h4>
                    <p>{text}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_graph_gallery(graphs: list[Path]) -> None:
    if not graphs:
        st.info("Nenhum grafico de treinamento foi encontrado na pasta 'graficos/'.")
        return
    for idx in range(0, len(graphs), 2):
        cols = st.columns(2)
        for col, graph in zip(cols, graphs[idx: idx + 2]):
            with col:
                st.image(str(graph), caption=graph.stem.replace("_", " ").title(), use_container_width=True)


def main() -> None:
    apply_theme()

    data_df = load_operational_data(str(DATA_PATH))
    decisions_df = load_decisions(str(DECISIONS_PATH))

    st.sidebar.title("Controle do Painel")
    st.sidebar.caption("Dashboard executivo para feira, banca e artigo cientifico.")
    if data_df.empty:
        st.sidebar.warning("Arquivo 'dados_citygrid.csv' nao encontrado ou vazio.")
    else:
        st.sidebar.success("Fonte operacional carregada.")
    if st.sidebar.button("Atualizar agora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    auto_refresh = st.sidebar.toggle("Autoatualizar a cada 10 segundos", value=False)

    max_cycle = int(data_df["ciclo"].max()) if not data_df.empty else 5
    window = st.sidebar.slider(
        "Janela recente de ciclos",
        min_value=5,
        max_value=max(5, max_cycle),
        value=min(40, max(5, max_cycle)),
    )
    available_zones = sorted(data_df["zona_nome"].dropna().unique().tolist()) if not data_df.empty else []
    selected_zones = st.sidebar.multiselect("Filtrar zonas", options=available_zones, default=available_zones)
    selected_risks = st.sidebar.multiselect(
        "Filtrar niveis de risco",
        options=RISK_ORDER[:4],
        default=RISK_ORDER[:4],
        format_func=lambda item: RISK_LABELS.get(item, item),
    )

    latest_cycle = max_cycle
    min_cycle = max(latest_cycle - window + 1, 1)
    if not data_df.empty:
        filtered = data_df[data_df["ciclo"] >= min_cycle].copy()
        if available_zones:
            filtered = filtered[filtered["zona_nome"].isin(selected_zones)] if selected_zones else filtered.iloc[0:0]
        filtered = filtered[filtered["risco"].isin(selected_risks)] if selected_risks else filtered.iloc[0:0]
    else:
        filtered = data_df

    cycle_df = build_cycle_view(filtered)
    risk_history = build_risk_history(filtered)
    current_df = filtered[filtered["ciclo"] == filtered["ciclo"].max()].copy() if not filtered.empty else pd.DataFrame()
    graphs = load_graphs()
    snapshot = build_product_snapshot(data_df, cycle_df, current_df, decisions_df)

    render_product_hero(data_df, decisions_df)
    st.write("")

    tabs = st.tabs(["Produto", "Operacao", "IA & Decisoes", "Impacto Comercial", "Resultados Cientificos"])

    with tabs[0]:
        render_section_header(
            "Proposta de valor da plataforma",
            "Leitura de produto para palco, investidores, parceiros e avaliadores de feira: o que o CityGrid Brain entrega e por que ele existe.",
        )
        render_product_positioning(snapshot, graphs)
        st.write("")
        render_readiness(snapshot, graphs)
        close_section()
        st.write("")
        render_section_header(
            "Arquitetura de implantacao",
            "A solucao se apresenta como uma camada de inteligencia operacional conectando captura de dados, streaming, IA e cockpit executivo.",
        )
        render_architecture()
        st.write("")
        render_market_fit()
        close_section()

    with tabs[1]:
        render_section_header(
            "Sintese do sistema eletrico urbano",
            "Indicadores para leitura rapida da operacao, adequados para abertura de apresentacao e conversa com banca ou avaliadores.",
        )
        render_kpis(current_df, cycle_df, decisions_df)
        st.write("")
        st.markdown(f'<div class="narrative">{build_decision_story(current_df, decisions_df)}</div>', unsafe_allow_html=True)
        close_section()
        st.write("")
        render_section_header(
            "Dinamica temporal da cidade",
            "Evolucao da demanda, participacao renovavel, pressao por risco e distribuicao operacional ao longo dos ciclos mais recentes.",
        )
        render_charts(cycle_df, risk_history, current_df)
        close_section()
        st.write("")
        render_section_header(
            "Mapa operacional por zona",
            "Cartoes executivos com o estado mais recente de cada regiao, focando carga, geracao renovavel, baterias e mobilidade eletrica.",
        )
        render_zone_cards(current_df)
        close_section()

    with tabs[2]:
        render_section_header(
            "Camadas de decisao e resposta",
            "Resumo das acoes geradas pelo motor hibrido, incluindo priorizacao heuristica, classificacao por XGBoost, previsao LSTM e otimizacao genetica.",
        )
        render_decision_panel(decisions_df)
        close_section()
        st.write("")
        render_section_header(
            "Estrutura metodologica",
            "Mostra como o produto combina dados, modelos e resposta operacional em uma arquitetura de inteligencia aplicavel em ambientes reais.",
        )
        render_methodology()
        close_section()

    with tabs[3]:
        render_section_header(
            "Drivers de valor para venda",
            "Indicadores que ajudam a converter a demonstracao tecnica em narrativa comercial: pressao operacional, energia sob gestao e alcance de automacao.",
        )
        render_commercial_impact(snapshot, current_df)
        close_section()
        st.write("")
        render_section_header(
            "Modelos de entrega e venda",
            "Sugestoes de empacotamento comercial para transformar a demonstracao em conversa de implantacao, parceria ou piloto.",
        )
        render_delivery_models()
        close_section()

    with tabs[4]:
        render_section_header(
            "Resultados graficos do treinamento",
            "As figuras abaixo sao carregadas diretamente da pasta 'graficos/' para manter o painel alinhado com os artefatos do experimento.",
        )
        render_graph_gallery(graphs)
        close_section()
        st.write("")
        render_section_header(
            "Base de dados, logs e exportacao",
            "Camada de respaldo para reproducao do experimento, trilha de auditoria e compartilhamento controlado dos recortes exibidos no painel.",
        )
        overview_cols = st.columns(4)
        overview_cols[0].metric("Linhas da base", f"{len(data_df):,}".replace(",", ".") if not data_df.empty else "0")
        overview_cols[1].metric("Zonas distintas", f"{data_df['zona_id'].nunique() if not data_df.empty else 0}")
        overview_cols[2].metric("Modelos LSTM", f"{len(list(MODELS_DIR.glob('lstm_*.pt')))}")
        overview_cols[3].metric("Scalers", f"{len(list(MODELS_DIR.glob('scaler_*.pkl')))}")
        st.write("")
        dl_cols = st.columns(2)
        with dl_cols[0]:
            st.download_button(
                "Baixar snapshot filtrado em CSV",
                data=create_download_payload(current_df),
                file_name="snapshot_citygrid.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=current_df.empty,
            )
        with dl_cols[1]:
            export_decisions = decisions_df.sort_values("timestamp", ascending=False).head(50) if not decisions_df.empty else decisions_df
            st.download_button(
                "Baixar 50 ultimas decisoes",
                data=create_download_payload(export_decisions),
                file_name="decisoes_citygrid.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=export_decisions.empty,
            )
        if not current_df.empty:
            st.write("")
            show_snapshot = current_df[
                [
                    "timestamp",
                    "ciclo",
                    "zona_nome",
                    "perfil",
                    "consumo_mw",
                    "capacidade_mw",
                    "pct_carga",
                    "risco",
                    "geracao_total_mw",
                    "bat_soc_pct",
                    "ve_ocupacao_pct",
                    "frequencia_hz",
                    "fator_potencia",
                ]
            ].copy()
            show_snapshot["risco"] = show_snapshot["risco"].map(RISK_LABELS).fillna(show_snapshot["risco"])
            st.dataframe(show_snapshot, use_container_width=True, hide_index=True)
        st.write("")
        st.markdown(
            """
            <div class="footnote">
                Este painel foi desenhado para demonstracao institucional e apresentacao tecnica.
                A composicao visual privilegia leitura rapida, narrativa cientifica e rastreabilidade
                das decisoes, sem abrir mao do detalhamento operacional necessario para avaliadores
                especializados.
            </div>
            """,
            unsafe_allow_html=True,
        )
        close_section()

    if auto_refresh:
        time.sleep(10)
        st.rerun()


if __name__ == "__main__":
    main()
