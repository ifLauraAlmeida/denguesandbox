import pandas as pd

from dengue_rj.dashboard.scenario import (
    scenario_figure,
    scenario_report,
    scenario_table,
)
from dengue_rj.models.sir import SIRParameters, solve_sir


def _scenario() -> tuple[SIRParameters, pd.DataFrame]:
    base_parameters = SIRParameters(10_000, 10, 0, 0.3, 0.1)
    intervention_parameters = SIRParameters(10_000, 10, 0, 0.24, 0.1)
    table = scenario_table(
        solve_sir(base_parameters, 30),
        solve_sir(intervention_parameters, 30),
    )
    return base_parameters, table


def test_scenario_table_contains_accumulated_and_effective_reproduction() -> None:
    _, table = _scenario()
    assert table.iloc[0]["infeccoes_acumuladas_base"] == 0
    assert table.iloc[-1]["infeccoes_acumuladas_base"] > 0
    assert table["re_efetivo_base"].is_monotonic_decreasing
    assert len(table) == 31


def test_scenario_exports_png_and_self_describing_report() -> None:
    parameters, table = _scenario()
    figure = scenario_figure(table)
    report = scenario_report(
        "Angra dos Reis",
        "3300100",
        2024,
        parameters,
        20,
        10,
        table,
    )
    assert figure.startswith(b"\x89PNG\r\n\x1a\n")
    assert "Não é previsão oficial" in report
    assert "3300100" in report
    assert "População RIPSA usada" in report
