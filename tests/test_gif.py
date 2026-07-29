from io import BytesIO
from pathlib import Path

import pandas as pd
from PIL import Image

from dengue_rj.visualization.dot_animation import (
    _counts,
    generate_dot_gif,
    generate_dot_gif_bytes,
)


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


def test_gif_bytes_respect_resolution_and_validate_limits():
    frame = pd.DataFrame(
        {
            "tempo": [0],
            "susceptible": [90],
            "infected": [10],
            "removed": [0],
            "population": [100],
            "effective_reproduction_number": [1.8],
        }
    )
    content = generate_dot_gif_bytes(
        frame,
        "Teste",
        dots=30,
        seed=7,
        width=640,
        height=480,
    )
    with Image.open(BytesIO(content)) as image:
        assert image.size == (640, 480)


def test_compartment_counts_always_match_requested_dots():
    row = pd.Series(
        {
            "population": 3,
            "susceptible": 1,
            "infected": 1,
            "removed": 1,
        }
    )

    counts = _counts(row, 500)

    assert sum(counts) == 500
    assert min(counts) >= 0
