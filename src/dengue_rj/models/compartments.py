"""Estimadores do estoque de infectados a partir de casos incidentes."""

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _cases(values: ArrayLike) -> NDArray[np.float64]:
    cases = np.asarray(values, dtype=float)
    if cases.ndim != 1 or np.any(~np.isfinite(cases)) or np.any(cases < 0):
        raise ValueError("cases deve ser vetor unidimensional, finito e não negativo")
    return cases


def fixed_window_active(cases: ArrayLike, infectious_period: int) -> NDArray[np.float64]:
    """Soma casos incidentes na janela infecciosa, sem inventar granularidade."""
    values = _cases(cases)
    if infectious_period < 1:
        raise ValueError(f"infectious_period deve ser >= 1; recebido {infectious_period}")
    return np.convolve(values, np.ones(infectious_period), mode="full")[: len(values)]


def proportional_outflow_active(cases: ArrayLike, gamma: float) -> NDArray[np.float64]:
    """Atualiza I(t)=I(t-1)+C(t)-gamma*I(t-1)."""
    values = _cases(cases)
    if not 0 < gamma <= 1:
        raise ValueError(f"gamma deve estar em (0, 1]; recebido {gamma}")
    active = np.zeros_like(values)
    for index, current in enumerate(values):
        previous = 0.0 if index == 0 else active[index - 1]
        active[index] = previous + current - gamma * previous
    return active
