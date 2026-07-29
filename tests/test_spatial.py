import numpy as np
import pandas as pd
import pytest

from dengue_rj.analysis.spatial import _weight_matrix, moran_global, moran_local
from dengue_rj.processors.spatial import _validate_neighbors


def _neighbors() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "codigo_ibge_municipio": ["1", "2", "2", "3"],
            "codigo_ibge_vizinho": ["2", "1", "3", "2"],
            "peso_normalizado_linha": [1.0, 0.5, 0.5, 1.0],
        }
    )


def test_neighbor_validation_and_weight_matrix() -> None:
    neighbors = _neighbors()
    _validate_neighbors(neighbors, {"1", "2", "3"})
    weights = _weight_matrix(neighbors, ["1", "2", "3"])
    assert np.allclose(weights.sum(axis=1), 1)
    assert weights[1, 0] == 0.5


def test_neighbor_validation_rejects_asymmetry() -> None:
    neighbors = _neighbors()
    neighbors.loc[3, "codigo_ibge_vizinho"] = "1"
    with pytest.raises(ValueError, match="simétrica"):
        _validate_neighbors(neighbors, {"1", "2", "3"})


def test_moran_is_reproducible_and_local_has_one_row_per_area() -> None:
    weights = _weight_matrix(_neighbors(), ["1", "2", "3"])
    values = np.array([1.0, 2.0, 8.0])
    observed, simulated = moran_global(values, weights, 19, np.random.default_rng(42))
    repeated, repeated_simulated = moran_global(
        values, weights, 19, np.random.default_rng(42)
    )
    local = moran_local(values, weights, 19, np.random.default_rng(42))
    assert observed == repeated
    assert np.array_equal(simulated, repeated_simulated)
    assert len(local) == 3
    assert local["p_permutacao_bilateral"].between(0, 1).all()


def test_moran_rejects_constant_values() -> None:
    weights = _weight_matrix(_neighbors(), ["1", "2", "3"])
    with pytest.raises(ValueError, match="constantes"):
        moran_global(np.ones(3), weights, 9, np.random.default_rng(1))
