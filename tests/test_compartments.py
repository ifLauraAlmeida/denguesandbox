import numpy as np
import pytest

from dengue_rj.models.compartments import (
    compare_active_estimators,
    fixed_window_active,
    proportional_outflow_active,
)


def test_fixed_window():
    assert np.array_equal(fixed_window_active([1, 2, 3, 4], 2), [1, 3, 5, 7])


def test_proportional_outflow():
    assert np.allclose(proportional_outflow_active([10, 0, 0], 0.5), [10, 5, 2.5])


@pytest.mark.parametrize("period", [0, -1])
def test_invalid_window(period):
    with pytest.raises(ValueError):
        fixed_window_active([1], period)


def test_compare_estimators_applies_explicit_detection_scenarios():
    result = compare_active_estimators(
        [10, 0, 0],
        infectious_period=2,
        detection_probabilities=[1.0, 0.5],
    )

    full_detection = result[result["probabilidade_deteccao"] == 1.0]
    half_detection = result[result["probabilidade_deteccao"] == 0.5]
    assert np.allclose(
        half_detection["casos_corrigidos_hipoteticos"],
        2 * full_detection["casos_corrigidos_hipoteticos"],
    )
    assert np.allclose(
        half_detection["infectados_ativos_janela_fixa"],
        2 * full_detection["infectados_ativos_janela_fixa"],
    )
    assert np.allclose(
        half_detection["infectados_ativos_saida_proporcional"],
        2 * full_detection["infectados_ativos_saida_proporcional"],
    )


@pytest.mark.parametrize("rho", [0, -0.1, 1.1, np.nan])
def test_detection_probability_must_be_between_zero_and_one(rho):
    with pytest.raises(ValueError):
        compare_active_estimators([1, 2], 2, [rho])
