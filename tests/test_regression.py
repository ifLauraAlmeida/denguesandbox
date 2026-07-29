import numpy as np
import pandas as pd
import pytest

from dengue_rj.analysis.regression import _fit_liraa_models, _ols_clustered


def test_clustered_ols_recovers_linear_coefficient():
    x_value = np.arange(20, dtype=float)
    x = np.column_stack([np.ones(20), x_value])
    y = 2 + 3 * x_value
    clusters = np.repeat(np.arange(10), 2)
    result = _ols_clustered(y, x, clusters, coefficient_position=1)
    assert result["coeficiente_indicador"] == pytest.approx(3)
    assert result["r_quadrado"] == pytest.approx(1)


def test_liraa_models_include_transformations_adjustments_and_lags():
    rows = []
    for municipality in range(12):
        for survey in range(4):
            value = municipality + survey / 10
            rows.append(
                {
                    "codigo_ibge_municipio": f"33{municipality:05d}",
                    "ano": 2020 + survey,
                    "mes": survey + 1,
                    "data_referencia": f"{2020 + survey}-{survey + 1:02d}-01",
                    "iip_aedes_aegypti": value,
                    "ib_aedes_aegypti": value + 0.2,
                    "flag_outlier_ib_maior_100": False,
                    **{
                        f"incidencia_mes_{lag}_1_mil": value * (lag + 1) + 1
                        for lag in range(4)
                    },
                }
            )
    result = _fit_liraa_models(pd.DataFrame(rows))
    assert len(result) == 48
    assert set(result["transformacao_desfecho"]) == {"original", "log1p"}
    assert set(result["ajuste"]) == {"bruto", "tempo", "municipio_rodada"}
    assert set(result["defasagem_meses"]) == {0, 1, 2, 3}
