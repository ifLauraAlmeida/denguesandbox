from pathlib import Path

import duckdb
import pandas as pd
import pytest

from dengue_rj.database.builder import build_database
from dengue_rj.database.simulations import store_sir_simulation


def _simulation(execution_id: str = "run-1") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "execution_id": execution_id,
            "codigo_ibge_municipio": "3304557",
            "municipio": "CENARIO_SINTETICO",
            "tempo": [0.0, 1.0],
            "cenario": "hipotetico",
            "susceptible": [990.0, 988.0],
            "infected": [10.0, 11.0],
            "removed": [0.0, 1.0],
            "new_infections": [2.0, 2.1],
            "new_removals": [1.0, 1.1],
            "beta": 0.2,
            "gamma": 0.1,
            "basic_reproduction_number": 2.0,
            "effective_reproduction_number": [1.98, 1.976],
            "population": 1000.0,
            "model_version": "0.1.0",
        }
    )


def test_store_simulation_migrates_placeholder_and_appends_complete_run(tmp_path: Path):
    database = build_database(tmp_path / "test.duckdb")

    stored = store_sir_simulation(_simulation(), database)

    with duckdb.connect(str(database), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT execution_id, count(*)
            FROM fact_sir_simulacao
            GROUP BY execution_id
            """
        ).fetchall()
    assert stored == 2
    assert rows == [("run-1", 2)]


def test_store_simulation_refuses_duplicate_execution(tmp_path: Path):
    database = build_database(tmp_path / "test.duckdb")
    store_sir_simulation(_simulation(), database)

    with pytest.raises(ValueError, match="já armazenado"):
        store_sir_simulation(_simulation(), database)
