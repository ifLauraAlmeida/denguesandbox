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


def fit_beta(
    observed_active: ArrayLike,
    population: float,
    initial_removed: float,
    gamma: float,
    bounds: tuple[float, float] = (0.0, 5.0),
) -> CalibrationResult:
    """Ajusta beta por mínimos quadrados ao estoque ativo estimado."""
    observed = np.asarray(observed_active, dtype=float)
    if observed.ndim != 1 or len(observed) < 2 or np.any(observed < 0):
        raise ValueError("observed_active deve ser vetor não negativo com ao menos 2 pontos")

    def objective(beta: float) -> float:
        params = SIRParameters(population, observed[0], initial_removed, beta, gamma)
        modeled = solve_sir(params, len(observed) - 1).infected
        return float(np.mean((modeled - observed) ** 2))

    fitted = minimize_scalar(objective, bounds=bounds, method="bounded")
    params = SIRParameters(population, observed[0], initial_removed, fitted.x, gamma)
    residuals = solve_sir(params, len(observed) - 1).infected - observed
    return CalibrationResult(
        beta=float(fitted.x),
        mae=float(np.mean(np.abs(residuals))),
        rmse=float(np.sqrt(np.mean(residuals**2))),
        converged=bool(fitted.success),
    )
