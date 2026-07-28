import numpy as np
import pytest

from dengue_rj.models.compartments import fixed_window_active, proportional_outflow_active


def test_fixed_window():
    assert np.array_equal(fixed_window_active([1, 2, 3, 4], 2), [1, 3, 5, 7])


def test_proportional_outflow():
    assert np.allclose(proportional_outflow_active([10, 0, 0], 0.5), [10, 5, 2.5])


@pytest.mark.parametrize("period", [0, -1])
def test_invalid_window(period):
    with pytest.raises(ValueError):
        fixed_window_active([1], period)
