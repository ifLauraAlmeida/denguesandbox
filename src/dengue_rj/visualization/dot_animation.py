"""Animação reproduzível dos compartimentos agregados."""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = {"susceptible": "#2E8B57", "infected": "#800020", "removed": "#D62728"}


def _counts(row: pd.Series, dots: int) -> tuple[int, int, int]:
    population = float(row["population"])
    susceptible = round(float(row["susceptible"]) / population * dots)
    infected = round(float(row["infected"]) / population * dots)
    return susceptible, infected, dots - susceptible - infected


def generate_dot_gif(
    simulation: pd.DataFrame,
    output: Path,
    municipality: str,
    dots: int = 1_000,
    seed: int = 42,
    fps: int = 8,
) -> Path:
    """Gera GIF; posições são fixas e somente os estados mudam."""
    required = {"susceptible", "infected", "removed", "population", "tempo"}
    if missing := required.difference(simulation.columns):
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    if simulation.empty or dots < 3:
        raise ValueError("simulation deve ter linhas e dots deve ser >= 3")
    rng = np.random.default_rng(seed)
    positions = rng.uniform(0, 1, size=(dots, 2))
    figure, axis = plt.subplots(figsize=(8, 6))
    scatter = axis.scatter(positions[:, 0], positions[:, 1], s=9)
    axis.set(xlim=(0, 1), ylim=(0, 1))
    axis.axis("off")
    peak_index = int(simulation["infected"].to_numpy().argmax())

    def update(frame: int):
        row = simulation.iloc[frame]
        susceptible, infected, _removed = _counts(row, dots)
        colors = (
            [COLORS["susceptible"]] * susceptible
            + [COLORS["infected"]] * infected
            + [COLORS["removed"]] * (dots - susceptible - infected)
        )
        scatter.set_color(colors)
        marker = " • pico" if frame == peak_index else ""
        effective = row.get("effective_reproduction_number", float("nan"))
        axis.set_title(
            f"{municipality} | t={row['tempo']:.0f}{marker}\n"
            f"S={row['susceptible']:.0f}  I={row['infected']:.0f}  "
            f"R={row['removed']:.0f}  Rₑ={effective:.2f}"
        )
        return (scatter,)

    animation = FuncAnimation(figure, update, frames=len(simulation), interval=1000 / fps)
    output.parent.mkdir(parents=True, exist_ok=True)
    animation.save(output, writer=PillowWriter(fps=fps))
    plt.close(figure)
    return output
