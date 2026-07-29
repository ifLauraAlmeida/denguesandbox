"""Estimadores do estoque de infectados a partir de casos incidentes."""

import numpy as np
import pandas as pd
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


def compare_active_estimators(
    reported_cases: ArrayLike,
    infectious_period: int,
    detection_probabilities: ArrayLike = (1.0,),
) -> pd.DataFrame:
    """Compara estimadores de I(t) sob cenários explícitos de detecção.

    `rho` é uma hipótese de sensibilidade, não uma estimativa da subnotificação.
    Os casos corrigidos são `casos_notificados / rho`.
    """
    reported = _cases(reported_cases)
    probabilities = np.asarray(detection_probabilities, dtype=float)
    if (
        probabilities.ndim != 1
        or probabilities.size == 0
        or np.any(~np.isfinite(probabilities))
        or np.any((probabilities <= 0) | (probabilities > 1))
    ):
        raise ValueError("detection_probabilities deve conter valores em (0, 1]")
    if infectious_period < 1:
        raise ValueError(f"infectious_period deve ser >= 1; recebido {infectious_period}")

    frames = []
    gamma = 1 / infectious_period
    for rho in probabilities:
        corrected = reported / rho
        frames.append(
            pd.DataFrame(
                {
                    "tempo": np.arange(len(reported)),
                    "probabilidade_deteccao": rho,
                    "casos_notificados": reported,
                    "casos_corrigidos_hipoteticos": corrected,
                    "infectados_ativos_janela_fixa": fixed_window_active(
                        corrected,
                        infectious_period,
                    ),
                    "infectados_ativos_saida_proporcional": proportional_outflow_active(
                        corrected,
                        gamma,
                    ),
                }
            )
        )
    return pd.concat(frames, ignore_index=True)
