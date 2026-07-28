from pathlib import Path

import pandas as pd

from dengue_rj.visualization.dot_animation import generate_dot_gif


def test_gif_is_generated_reproducibly(tmp_path: Path):
    frame = pd.DataFrame(
        {
            "tempo": [0, 1],
            "susceptible": [90, 85],
            "infected": [10, 10],
            "removed": [0, 5],
            "population": [100, 100],
            "effective_reproduction_number": [1.8, 1.7],
        }
    )
    first = generate_dot_gif(frame, tmp_path / "first.gif", "Teste", dots=30, seed=7)
    second = generate_dot_gif(frame, tmp_path / "second.gif", "Teste", dots=30, seed=7)
    assert first.read_bytes() == second.read_bytes()
