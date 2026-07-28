import numpy as np
import pytest

from dengue_rj.models.sir import SIRParameters, solve_euler, solve_sir


@pytest.mark.parametrize("solver", [solve_euler, solve_sir])
def test_population_is_conserved(solver):
    params = SIRParameters(10_000, 10, 25, 0.25, 0.1)
    result = solver(params, 60)
    assert np.allclose(result.susceptible + result.infected + result.removed, 10_000)
    assert min(result.susceptible.min(), result.infected.min(), result.removed.min()) >= 0


@pytest.mark.parametrize(
    "params",
    [
        SIRParameters(0, 0, 0, 0.2, 0.1),
        SIRParameters(100, -1, 0, 0.2, 0.1),
        SIRParameters(100, 60, 50, 0.2, 0.1),
        SIRParameters(100, 1, 0, -0.2, 0.1),
        SIRParameters(100, 1, 0, 0.2, 0),
    ],
)
def test_invalid_parameters_fail(params):
    with pytest.raises(ValueError):
        params.validate()


def test_reproduction_numbers():
    params = SIRParameters(100, 10, 0, 0.4, 0.2)
    result = solve_sir(params, 1)
    assert params.basic_reproduction_number == 2
    assert result.effective_reproduction_number[0] == pytest.approx(1.8)
