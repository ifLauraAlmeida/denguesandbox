"""Animação reproduzível dos compartimentos agregados."""

from io import BytesIO
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = {"susceptible": "#2E8B57", "infected": "#800020", "removed": "#D62728"}


def _counts(row: pd.Series, dots: int) -> tuple[int, int, int]:
    population = float(row["population"])
    if not np.isfinite(population) or population <= 0:
        raise ValueError("population deve ser positiva e finita")
    compartments = np.array(
        [row["susceptible"], row["infected"], row["removed"]],
        dtype=float,
    )
    if not np.isfinite(compartments).all():
        raise ValueError("Compartimentos devem conter valores finitos")
    compartments = np.clip(compartments, 0, None)
    total = compartments.sum()
    if total <= 0:
        raise ValueError("A soma dos compartimentos deve ser positiva")
    exact = compartments / total * dots
    counts = np.floor(exact).astype(int)
    remainder = dots - int(counts.sum())
    if remainder:
        order = np.argsort(-(exact - counts))
        counts[order[:remainder]] += 1
    return tuple(int(value) for value in counts)


def generate_dot_gif(
    simulation: pd.DataFrame,
    output: Path,
    municipality: str,
    dots: int = 1_000,
    seed: int = 42,
    fps: int = 8,
    width: int = 800,
    height: int = 600,
) -> Path:
    """Gera GIF; posições são fixas e somente os estados mudam."""
    content = generate_dot_gif_bytes(
        simulation,
        municipality,
        dots=dots,
        seed=seed,
        fps=fps,
        width=width,
        height=height,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    return output


def generate_dot_gif_bytes(
    simulation: pd.DataFrame,
    municipality: str,
    dots: int = 1_000,
    seed: int = 42,
    fps: int = 8,
    width: int = 800,
    height: int = 600,
) -> bytes:
    """Gera GIF em memória com tamanho, semente e posições reproduzíveis."""
    required = {"susceptible", "infected", "removed", "population", "tempo"}
    if missing := required.difference(simulation.columns):
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    if simulation.empty or dots < 3:
        raise ValueError("simulation deve ter linhas e dots deve ser >= 3")
    if fps < 1 or width < 320 or height < 240:
        raise ValueError("fps >= 1, width >= 320 e height >= 240 são obrigatórios")
    rng = np.random.default_rng(seed)
    positions = rng.uniform(0, 1, size=(dots, 2))
    dpi = 100
    figure, axis = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    scatter = axis.scatter(positions[:, 0], positions[:, 1], s=9)
    axis.set(xlim=(0, 1), ylim=(0, 1))
    axis.axis("off")
    peak_index = int(simulation["infected"].to_numpy().argmax())

    frames = []
    for frame in range(len(simulation)):
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
        figure.canvas.draw()
        image = Image.fromarray(np.asarray(figure.canvas.buffer_rgba())[:, :, :3])
        frames.append(image.copy())
    plt.close(figure)
    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / fps),
        loop=0,
        optimize=False,
    )
    return output.getvalue()
