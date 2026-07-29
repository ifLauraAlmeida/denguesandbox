import numpy as np
import pytest

from dengue_rj.models.calibration import (
    assess_calibration,
    calibration_sensitivity,
    fit_beta,
    fit_beta_incident_temporal,
    fit_beta_temporal,
)
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


def test_sensitivity_reports_each_infectious_period():
    result = calibration_sensitivity(
        _synthetic_active(),
        100_000,
        0,
        infectious_periods=[7, 10, 14],
        bounds=(0.05, 0.5),
        validation_size=5,
    )

    assert result["periodo_infeccioso"].tolist() == [7.0, 10.0, 14.0]
    assert result["convergiu"].all()
    assert result["rmse_validacao"].notna().all()


def test_assessment_accepts_only_when_explicit_criteria_are_met():
    result = fit_beta_temporal(
        _synthetic_active(),
        100_000,
        0,
        0.1,
        bounds=(0.05, 0.5),
        validation_size=5,
    )

    accepted = assess_calibration(
        result,
        observed_scale=float(_synthetic_active().mean()),
        max_validation_nrmse=0.01,
        boundary_tolerance_fraction=0.01,
    )

    assert accepted.accepted
    assert accepted.reasons == ()
    assert not accepted.beta_at_boundary


def test_assessment_rejects_missing_validation():
    result = fit_beta(
        _synthetic_active(),
        100_000,
        0,
        0.1,
        bounds=(0.05, 0.5),
    )

    assessment = assess_calibration(
        result,
        observed_scale=100,
        max_validation_nrmse=0.5,
        boundary_tolerance_fraction=0.01,
    )

    assert not assessment.accepted
    assert "validacao_temporal_ausente" in assessment.reasons


def test_incident_calibration_recovers_synthetic_beta_without_using_validation():
    parameters = SIRParameters(100_000, 20, 0, 0.25, 0.1)
    observed = solve_sir(parameters, 20).new_infections

    result = fit_beta_incident_temporal(
        observed,
        population=100_000,
        initial_infected=20,
        initial_removed=0,
        gamma=0.1,
        bounds=(0.05, 0.5),
        validation_size=5,
    )

    assert result.converged
    assert result.beta == pytest.approx(0.25, rel=1e-3)
    assert result.train_size == 16
    assert result.validation_size == 5
    assert result.validation_rmse == pytest.approx(0, abs=1e-4)


def test_incident_calibration_requires_explicit_valid_bounds():
    with pytest.raises(ValueError, match="bounds"):
        fit_beta_incident_temporal(
            [1, 2, 3],
            population=1000,
            initial_infected=1,
            initial_removed=0,
            gamma=0.1,
            bounds=(0.5, 0.1),
        )
