import numpy as np
import pytest

from dengue_rj.models.calibration import fit_beta, fit_beta_temporal
from dengue_rj.models.sir import SIRParameters, solve_sir


def _synthetic_active(beta: float = 0.25) -> np.ndarray:
    parameters = SIRParameters(
        population=100_000,
        initial_infected=20,
        initial_removed=0,
        beta=beta,
        gamma=0.1,
    )
    return solve_sir(parameters, 20).infected


def test_fit_beta_records_objective_metrics_and_residuals():
    observed = _synthetic_active()

    result = fit_beta(observed, 100_000, 0, 0.1, bounds=(0.05, 0.5))

    assert result.converged
    assert result.beta == pytest.approx(0.25, rel=1e-3)
    assert result.objective_mse == pytest.approx(result.rmse**2)
    assert len(result.residuals) == len(observed)
    assert result.train_size == len(observed)
    assert result.validation_size == 0
    assert result.validation_rmse is None


def test_temporal_validation_is_not_used_for_refitting():
    observed = _synthetic_active()
    result = fit_beta_temporal(
        observed,
        100_000,
        0,
        0.1,
        bounds=(0.05, 0.5),
        validation_size=5,
    )

    assert result.train_size == 16
    assert result.validation_size == 5
    assert result.validation_mae is not None
    assert result.validation_rmse is not None
    assert result.beta == pytest.approx(0.25, rel=1e-3)


@pytest.mark.parametrize(
    ("bounds", "validation_size"),
    [
        ((0.5, 0.1), 0),
        ((-0.1, 0.5), 0),
        ((0.1, np.inf), 0),
        ((0.1, 0.5), -1),
        ((0.1, 0.5), 20),
    ],
)
def test_temporal_calibration_rejects_invalid_configuration(bounds, validation_size):
    with pytest.raises(ValueError):
        fit_beta_temporal(
            _synthetic_active(),
            100_000,
            0,
            0.1,
            bounds=bounds,
            validation_size=validation_size,
        )
