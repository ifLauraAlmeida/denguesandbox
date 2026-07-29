import pandas as pd
import pytest

from dengue_rj.analysis.exploratory import (
    _association_sensitivity,
    _incidence_extremes,
    _incidence_summary,
    _sanitation_associations,
)


def test_incidence_summary_uses_ratio_between_sums():
    incidence = pd.DataFrame(
        {
            "ano": [2024, 2024],
            "codigo_ibge_municipio": ["1", "2"],
            "nome_municipio": ["A", "B"],
            "casos_provaveis": [10, 90],
            "populacao_residente": [1_000, 9_000],
            "incidencia_1_mil": [10.0, 10.0],
        }
    )
    summary = _incidence_summary(incidence).iloc[0]
    assert summary["incidencia_agregada_1_mil"] == 10
    assert summary["municipios"] == 2


def test_extremes_and_associations_are_reproducible():
    incidence = pd.DataFrame(
        {
            "ano": [2023] * 12,
            "codigo_ibge_municipio": [str(value) for value in range(12)],
            "nome_municipio": [f"M{value}" for value in range(12)],
            "incidencia_1_mil": list(range(12)),
        }
    )
    extremes = _incidence_extremes(incidence)
    assert len(extremes) == 20
    assert extremes.iloc[0]["nome_municipio"] == "M11"

    cross_section = incidence.assign(
        atendimento_agua_percentual=list(range(12)),
        atendimento_esgoto_percentual=list(reversed(range(12))),
    )
    associations = _sanitation_associations(cross_section)
    assert associations.loc[0, "pearson_r"] == pytest.approx(1)
    assert associations.loc[1, "spearman_rho"] == pytest.approx(-1)
    assert set(associations["interpretacao"]) == {
        "associacao_exploratoria_nao_causal"
    }
    sensitivity = _association_sensitivity(cross_section)
    assert len(sensitivity) == 24
    assert set(sensitivity["indicador_saneamento"]) == {
        "atendimento_agua_percentual",
        "atendimento_esgoto_percentual",
    }
