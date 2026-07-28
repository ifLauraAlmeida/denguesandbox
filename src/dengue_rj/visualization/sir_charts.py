"""Gráficos do modelo SIR."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_sir_chart(simulation: pd.DataFrame, output: Path) -> Path:
    figure, axis = plt.subplots(figsize=(10, 5))
    for column, color in (("susceptible", "#2E8B57"), ("infected", "#800020"), ("removed", "#D62728")):
        axis.plot(simulation["tempo"], simulation[column], label=column, color=color)
    axis.set(xlabel="Tempo (dias)", ylabel="Pessoas", title="Cenário SIR condicionado")
    axis.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output
