"""Saídas reproduzíveis para cenários SIR explicitamente hipotéticos."""

from io import BytesIO

import matplotlib
import pandas as pd

from dengue_rj.models.sir import SIRParameters, SIRResult

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def scenario_table(
    base: SIRResult,
    intervention: SIRResult,
) -> pd.DataFrame:
    """Materializa compartimentos, acumulados e números reprodutivos."""
    return pd.DataFrame(
        {
            "dia": base.time,
            "suscetiveis_base": base.susceptible,
            "infectados_base": base.infected,
            "removidos_base": base.removed,
            "infeccoes_acumuladas_base": base.susceptible[0] - base.susceptible,
            "re_efetivo_base": base.effective_reproduction_number,
            "infectados_intervencao": intervention.infected,
            "infeccoes_acumuladas_intervencao": (
                intervention.susceptible[0] - intervention.susceptible
            ),
            "re_efetivo_intervencao": intervention.effective_reproduction_number,
        }
    )


def scenario_figure(table: pd.DataFrame) -> bytes:
    """Renderiza uma figura PNG exportável com infectados e R efetivo."""
    figure, (infected_axis, reproduction_axis) = plt.subplots(
        2,
        1,
        figsize=(10, 7),
        sharex=True,
    )
    infected_axis.plot(table["dia"], table["infectados_base"], label="Base")
    infected_axis.plot(
        table["dia"],
        table["infectados_intervencao"],
        label="Intervenção hipotética",
    )
    infected_axis.set_ylabel("Infectados ativos")
    infected_axis.legend()
    reproduction_axis.plot(table["dia"], table["re_efetivo_base"], label="Base")
    reproduction_axis.plot(
        table["dia"],
        table["re_efetivo_intervencao"],
        label="Intervenção hipotética",
    )
    reproduction_axis.axhline(1, color="black", linestyle="--", linewidth=0.8)
    reproduction_axis.set(xlabel="Dia", ylabel="R efetivo")
    reproduction_axis.legend()
    figure.suptitle("Cenário SIR condicionado a parâmetros hipotéticos")
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
    plt.close(figure)
    return buffer.getvalue()


def scenario_report(
    municipality: str,
    municipality_code: str,
    population_year: int,
    base_parameters: SIRParameters,
    reduction_percent: int,
    infectious_period: float,
    table: pd.DataFrame,
) -> str:
    """Gera relatório Markdown autocontido das hipóteses e resultados."""
    base_peak_index = int(table["infectados_base"].idxmax())
    intervention_peak_index = int(table["infectados_intervencao"].idxmax())
    return f"""# Cenário SIR — {municipality}

- Código IBGE: `{municipality_code}`
- População RIPSA usada: {base_parameters.population:,.0f} ({population_year})
- Infectados ativos iniciais estimados: {base_parameters.initial_infected:,.0f}
- Removidos iniciais hipotéticos: {base_parameters.initial_removed:,.0f}
- β base hipotético: {base_parameters.beta:.4f} por dia
- Período infeccioso hipotético: {infectious_period:.2f} dias
- Redução hipotética de β: {reduction_percent}%
- R₀ base: {base_parameters.basic_reproduction_number:.3f}

## Resultados condicionais

- Pico base: {table.loc[base_peak_index, "infectados_base"]:,.0f} no dia
  {table.loc[base_peak_index, "dia"]:.0f}
- Pico sob intervenção: {table.loc[intervention_peak_index, "infectados_intervencao"]:,.0f}
  no dia {table.loc[intervention_peak_index, "dia"]:.0f}
- Infecções acumuladas no cenário base:
  {table.iloc[-1]["infeccoes_acumuladas_base"]:,.0f}
- Infecções acumuladas sob intervenção:
  {table.iloc[-1]["infeccoes_acumuladas_intervencao"]:,.0f}

## Limitações

Simulação acadêmica condicionada às hipóteses. Não é previsão oficial. O SIR
simplificado não representa explicitamente o vetor, sorotipos, clima,
mobilidade, imunidade heteróloga, subnotificação nem intervenções reais.
"""
