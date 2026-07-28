"""Interface Streamlit do sandbox com parâmetros explicitamente hipotéticos."""

import pandas as pd
import streamlit as st

from dengue_rj.models.sir import SIRParameters, solve_sir

st.set_page_config(page_title="Dengue RJ · Sandbox SIR", layout="wide")
st.title("Sandbox SIR da dengue no Estado do Rio de Janeiro")
st.warning(
    "Simulação acadêmica condicionada aos parâmetros. Não é previsão oficial nem "
    "representação completa do ciclo humano–mosquito–humano."
)
st.sidebar.header("Cenário hipotético")
municipality = st.sidebar.text_input("Município (rótulo)", "CENÁRIO SINTÉTICO")
population = st.sidebar.number_input("População N (hipotética)", 1, value=100_000)
infected = st.sidebar.number_input("Infectados ativos I₀ (estimados)", 0, value=10)
removed = st.sidebar.number_input("Recuperados ou removidos R₀ inicial", 0, value=0)
beta = st.sidebar.number_input("β por dia (hipotético)", 0.0, value=0.30, step=0.01)
infectious_period = st.sidebar.number_input("Período infeccioso em dias (hipotético)", 0.1, value=10.0)
reduction = st.sidebar.slider("Redução hipotética da transmissão", 0, 100, 20)
days = st.sidebar.slider("Horizonte (dias)", 1, 730, 180)

gamma = 1 / infectious_period
base = SIRParameters(population, infected, removed, beta, gamma)
intervention = SIRParameters(population, infected, removed, beta * (1 - reduction / 100), gamma)
base_result = solve_sir(base, days)
intervention_result = solve_sir(intervention, days)

table = pd.DataFrame(
    {
        "tempo": base_result.time,
        "S base": base_result.susceptible,
        "I base": base_result.infected,
        "R base": base_result.removed,
        "I intervenção": intervention_result.infected,
    }
).set_index("tempo")
first, second, third = st.columns(3)
first.metric("R₀ base", f"{base.basic_reproduction_number:.2f}")
peak = int(base_result.infected.argmax())
second.metric("Pico infectado", f"{base_result.infected[peak]:,.0f}")
third.metric("Dia do pico", peak)
st.subheader(municipality)
st.line_chart(table)
st.caption(
    "R significa recuperados ou removidos sob imunidade específica ao sorotipo assumido. "
    "Casos observados não representam todas as infecções."
)
st.download_button("Exportar cenário CSV", table.to_csv().encode(), "cenario_sir.csv", "text/csv")
