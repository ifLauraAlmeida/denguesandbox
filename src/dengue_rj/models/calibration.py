"""Calibração exploratória, não preditiva, do beta."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike
from scipy.optimize import minimize_scalar

from dengue_rj.models.sir import SIRParameters, solve_sir


@dataclass(frozen=True)
class CalibrationResult:
    beta: float
    mae: float
    rmse: float
    converged: bool
    objective_mse: float
    residuals: tuple[float, ...]
    train_size: int
    validation_size: int
    train_mae: float
    train_rmse: float
    validation_mae: float | None
    validation_rmse: float | None
    bounds: tuple[float, float]


def fit_beta(
    observed_active: ArrayLike,
    population: float,
    initial_removed: float,
    gamma: float,
    bounds: tuple[float, float] = (0.0, 5.0),
) -> CalibrationResult:
    """Ajusta beta por mínimos quadrados ao estoque ativo estimado."""
    return fit_beta_temporal(
        observed_active,
        population,
        initial_removed,
        gamma,
        bounds=bounds,
        validation_size=0,
    )


def fit_beta_temporal(
    observed_active: ArrayLike,
    population: float,
    initial_removed: float,
    gamma: float,
    bounds: tuple[float, float] = (0.0, 5.0),
    validation_size: int = 0,
) -> CalibrationResult:
    """Ajusta no início da série e avalia, sem refit, no período final."""
    observed = np.asarray(observed_active, dtype=float)
    if (
        observed.ndim != 1
        or len(observed) < 2
        or np.any(~np.isfinite(observed))
        or np.any(observed < 0)
    ):
        raise ValueError("observed_active deve ser vetor não negativo com ao menos 2 pontos")
    if (
        len(bounds) != 2
        or not np.isfinite(bounds).all()
        or bounds[0] < 0
        or bounds[0] >= bounds[1]
    ):
        raise ValueError("bounds deve ser um intervalo finito crescente e não negativo")
    if validation_size < 0 or validation_size >= len(observed) - 1:
        raise ValueError("validation_size deve deixar ao menos 2 pontos para treino")
    train_size = len(observed) - validation_size
    train = observed[:train_size]

    def objective(beta: float) -> float:
        params = SIRParameters(population, train[0], initial_removed, beta, gamma)
        modeled = solve_sir(params, len(train) - 1).infected
        return float(np.mean((modeled - train) ** 2))

    fitted = minimize_scalar(objective, bounds=bounds, method="bounded")
    params = SIRParameters(population, observed[0], initial_removed, fitted.x, gamma)
    modeled = solve_sir(params, len(observed) - 1).infected
    residuals = modeled - observed
    train_residuals = residuals[:train_size]
    validation_residuals = residuals[train_size:]

    def metrics(values: np.ndarray) -> tuple[float, float]:
        return (
            float(np.mean(np.abs(values))),
            float(np.sqrt(np.mean(values**2))),
        )

    mae, rmse = metrics(residuals)
    train_mae, train_rmse = metrics(train_residuals)
    validation_metrics = metrics(validation_residuals) if validation_size else (None, None)
    return CalibrationResult(
        beta=float(fitted.x),
        mae=mae,
        rmse=rmse,
        converged=bool(fitted.success),
        objective_mse=float(fitted.fun),
        residuals=tuple(float(value) for value in residuals),
        train_size=train_size,
        validation_size=validation_size,
        train_mae=train_mae,
        train_rmse=train_rmse,
        validation_mae=validation_metrics[0],
        validation_rmse=validation_metrics[1],
        bounds=bounds,
    )
