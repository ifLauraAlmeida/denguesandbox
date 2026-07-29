"""Painel municipal e sandbox SIR da dengue no RJ."""

from pathlib import Path

import pandas as pd
import streamlit as st

from dengue_rj.dashboard.data import (
    annual_dengue,
    monthly_dengue,
    municipalities,
    sanitation,
)
from dengue_rj.dashboard.scenario import scenario_figure, scenario_report, scenario_table
from dengue_rj.models.sir import SIRParameters, solve_sir
from dengue_rj.visualization.dot_animation import generate_dot_gif_bytes

DATABASE = Path("database/dengue_rj.duckdb")
FIGURES = Path("outputs/figures/espacial")

st.set_page_config(page_title="Dengue RJ · Sandbox SIR", layout="wide")
st.title("Dengue nos municípios do Estado do Rio de Janeiro")
st.warning(
    "Análises observacionais e simulações acadêmicas. Associação espacial não implica "
    "causalidade e o SIR simplificado não representa o ciclo humano–mosquito–humano."
)

if not DATABASE.exists():
    st.error("Banco ausente. Execute o pipeline de construção e carga antes do painel.")
    st.stop()

municipality_table = municipalities(DATABASE)
labels = dict(
    zip(
        municipality_table["nome_municipio"],
        municipality_table["codigo_ibge_municipio"],
    )
)
selected_name = st.sidebar.selectbox(
    "Selecione explicitamente o município",
    options=list(labels),
    index=None,
    placeholder="Nenhum município selecionado",
)
if selected_name is None:
    st.info("Selecione um município na barra lateral para carregar os dados.")
    st.stop()

municipality_code = labels[selected_name]
annual = annual_dengue(DATABASE, municipality_code)
monthly = monthly_dengue(DATABASE, municipality_code)
sanitation_table = sanitation(DATABASE, municipality_code)

minimum_year, maximum_year = int(annual["ano"].min()), int(annual["ano"].max())
year_range = st.sidebar.slider(
    "Intervalo dos dados observados",
    minimum_year,
    maximum_year,
    (minimum_year, maximum_year),
)
annual_filtered = annual[annual["ano"].between(*year_range)]
monthly_filtered = monthly[
    pd.to_datetime(monthly["mes"]).dt.year.between(*year_range)
].copy()

st.header(f"{selected_name} · código IBGE {municipality_code}")
epidemiology_tab, sanitation_tab, spatial_tab, sir_tab = st.tabs(
    ["Dengue observada", "Saneamento", "Análise espacial", "Cenário SIR"]
)

with epidemiology_tab:
    latest = annual_filtered.iloc[-1]
    first, second, third = st.columns(3)
    first.metric("Casos prováveis no último ano selecionado", f"{latest.casos_provaveis:,.0f}")
    second.metric("Incidência por 100 mil", f"{latest.incidencia_100_mil:,.1f}")
    third.metric("População RIPSA", f"{latest.populacao_residente:,.0f}")
    chart = monthly_filtered.set_index("mes")[["casos_provaveis", "casos_descartados"]]
    st.line_chart(chart)
    st.caption(
        "Eixo temporal: primeiros sintomas (DT_SIN_PRI). Território: município de "
        "residência (ID_MN_RESI), nunca município de notificação."
    )
    st.dataframe(annual_filtered, hide_index=True, width="stretch")
    st.download_button(
        "Exportar indicadores de dengue",
        annual_filtered.to_csv(index=False).encode("utf-8"),
        f"dengue_{municipality_code}.csv",
        "text/csv",
    )

with sanitation_tab:
    st.caption(
        "Valores SNIS/SINISA preservam código, unidade, fonte, status e comparabilidade. "
        "Linhas de múltiplos prestadores não são agregadas silenciosamente."
    )
    st.dataframe(sanitation_table, hide_index=True, width="stretch")
    st.download_button(
        "Exportar saneamento",
        sanitation_table.to_csv(index=False).encode("utf-8"),
        f"saneamento_{municipality_code}.csv",
        "text/csv",
    )

with spatial_tab:
    map_year = st.select_slider(
        "Ano dos mapas",
        options=annual["ano"].astype(int).tolist(),
        value=int(annual["ano"].max()),
    )
    incidence_map = FIGURES / f"incidencia_dengue_{map_year}.png"
    cluster_map = FIGURES / f"moran_local_clusters_{map_year}.png"
    left, right = st.columns(2)
    if incidence_map.exists() and cluster_map.exists():
        left.image(str(incidence_map), width="stretch")
        right.image(str(cluster_map), width="stretch")
    else:
        st.error("Mapas ausentes. Execute `python -m dengue_rj.cli build-spatial-analysis`.")
    st.caption(
        "Clusters locais usam pesos rainha e p bilateral < 0,05. São diagnósticos "
        "exploratórios e não estimativas causais."
    )

with sir_tab:
    st.subheader("Parâmetros explicitamente hipotéticos")
    population = int(latest.populacao_residente)
    infected = st.number_input(
        "Infectados ativos I₀ (estimados)",
        0,
        max_value=population,
        value=10,
    )
    removed = st.number_input(
        "Recuperados ou removidos R inicial",
        0,
        max_value=population,
        value=0,
    )
    beta = st.number_input("β por dia", 0.0, value=0.30, step=0.01)
    infectious_period = st.number_input("Período infeccioso em dias", 0.1, value=10.0)
    reduction = st.slider("Redução hipotética da transmissão", 0, 100, 20)
    days = st.slider("Horizonte da simulação (dias)", 1, 730, 180)
    if infected + removed > population:
        st.error("I₀ + removidos iniciais não pode exceder a população RIPSA.")
        st.stop()
    gamma = 1 / infectious_period
    base = SIRParameters(population, infected, removed, beta, gamma)
    intervention = SIRParameters(
        population,
        infected,
        removed,
        beta * (1 - reduction / 100),
        gamma,
    )
    base_result = solve_sir(base, days)
    intervention_result = solve_sir(intervention, days)
    simulation = scenario_table(base_result, intervention_result)
    peak = int(base_result.infected.argmax())
    cumulative = simulation.iloc[-1]["infeccoes_acumuladas_base"]
    first, second, third, fourth = st.columns(4)
    first.metric("R₀ base", f"{base.basic_reproduction_number:.2f}")
    second.metric("Pico infectado", f"{base_result.infected[peak]:,.0f}")
    third.metric("Dia do pico", peak)
    fourth.metric("Infecções acumuladas", f"{cumulative:,.0f}")
    st.line_chart(
        simulation.set_index("dia")[
            ["infectados_base", "infectados_intervencao"]
        ]
    )
    st.line_chart(
        simulation.set_index("dia")[
            ["re_efetivo_base", "re_efetivo_intervencao"]
        ]
    )
    st.caption(
        "R efetivo varia com a fração suscetível. A linha de referência Rₑ=1 "
        "está disponível na figura exportável."
    )
    report = scenario_report(
        selected_name,
        municipality_code,
        int(latest.ano),
        base,
        reduction,
        infectious_period,
        simulation,
    )
    st.download_button(
        "Exportar cenário SIR",
        simulation.to_csv(index=False).encode("utf-8"),
        f"cenario_sir_{municipality_code}.csv",
        "text/csv",
    )
    st.download_button(
        "Exportar figura PNG",
        scenario_figure(simulation),
        f"cenario_sir_{municipality_code}.png",
        "image/png",
    )
    st.download_button(
        "Exportar relatório metodológico",
        report.encode("utf-8"),
        f"cenario_sir_{municipality_code}.md",
        "text/markdown",
    )
    st.subheader("GIF dos compartimentos")
    gif_first, gif_second, gif_third = st.columns(3)
    gif_seed = gif_first.number_input("Semente do GIF", 0, value=42)
    gif_dots = gif_second.slider("Pontos no GIF", 100, 2_000, 500, 100)
    gif_resolution = gif_third.selectbox(
        "Resolução do GIF",
        options=[(640, 480), (800, 600), (1_024, 768)],
        format_func=lambda size: f"{size[0]} × {size[1]} px",
        index=1,
    )
    st.caption(
        "Os pontos representam proporções agregadas, não pessoas identificáveis "
        "nem uma simulação espacial."
    )
    if st.button("Gerar GIF reproduzível"):
        gif_frame_step = max(1, len(base_result.time) // 90)
        gif_table = pd.DataFrame(
            {
                "tempo": base_result.time,
                "susceptible": base_result.susceptible,
                "infected": base_result.infected,
                "removed": base_result.removed,
                "population": population,
                "effective_reproduction_number": (
                    base_result.effective_reproduction_number
                ),
            }
        ).iloc[::gif_frame_step]
        st.session_state["sir_gif"] = generate_dot_gif_bytes(
            gif_table,
            selected_name,
            dots=gif_dots,
            seed=gif_seed,
            width=gif_resolution[0],
            height=gif_resolution[1],
        )
        st.session_state["sir_gif_key"] = (
            municipality_code,
            gif_seed,
            gif_dots,
            gif_resolution,
            beta,
            infectious_period,
            days,
        )
    current_gif_key = (
        municipality_code,
        gif_seed,
        gif_dots,
        gif_resolution,
        beta,
        infectious_period,
        days,
    )
    if st.session_state.get("sir_gif_key") == current_gif_key:
        st.download_button(
            "Baixar GIF",
            st.session_state["sir_gif"],
            f"cenario_sir_{municipality_code}.gif",
            "image/gif",
        )
