"""Indicadores epidemiológicos com regras explícitas."""

import numpy as np
import pandas as pd


def incidence(cases: float, population: float, scale: float = 1_000) -> float:
    """Calcula casos/população na escala informada."""
    if cases < 0 or population <= 0 or scale <= 0:
        raise ValueError(f"Esperado cases>=0, population>0, scale>0; recebido {cases, population, scale}")
    return cases / population * scale


def aggregate_incidence(cases: pd.Series, populations: pd.Series) -> float:
    """Calcula razão entre somas, nunca média simples de incidências."""
    if len(cases) != len(populations) or cases.isna().any() or populations.isna().any():
        raise ValueError("Séries devem ter mesmo tamanho e não conter ausentes")
    return incidence(float(cases.sum()), float(populations.sum()))


def notification_delay(symptom_dates: pd.Series, notification_dates: pd.Series) -> pd.Series:
    """Retorna atraso, em dias, entre primeiros sintomas e notificação."""
    symptoms = pd.to_datetime(symptom_dates, errors="coerce")
    notifications = pd.to_datetime(notification_dates, errors="coerce")
    result = (notifications - symptoms).dt.days.astype("Float64")
    return result.mask(result < 0, np.nan)
