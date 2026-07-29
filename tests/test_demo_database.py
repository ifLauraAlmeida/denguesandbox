from pathlib import Path

import duckdb
import pandas as pd
import pytest

from dengue_rj.database.demo import (
    DEMO_TABLES,
    build_demo_database,
)


def _source_database(path: Path) -> Path:
    with duckdb.connect(str(path)) as connection:
        for table in DEMO_TABLES:
            if table == "indicador_dengue_municipio_ano":
                frame = pd.DataFrame(
                    {
                        "criterio_territorial": ["ID_MN_RESI"],
                        "codigo_ibge_municipio": ["3300100"],
                    }
                )
            else:
                frame = pd.DataFrame({"codigo_ibge_municipio": ["3300100"]})
            connection.register("_frame", frame)
            connection.execute(f"CREATE TABLE {table} AS SELECT * FROM _frame")
            connection.unregister("_frame")
        connection.execute("CREATE TABLE fact_dengue (registro VARCHAR)")
    return path


def test_demo_database_contains_only_aggregate_tables(tmp_path: Path) -> None:
    source = _source_database(tmp_path / "source.duckdb")
    demo = build_demo_database(source, tmp_path / "demo.duckdb")
    with duckdb.connect(str(demo), read_only=True) as connection:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
    assert tables == set(DEMO_TABLES)
    assert "fact_dengue" not in tables


def test_demo_database_refuses_to_overwrite_source(tmp_path: Path) -> None:
    source = _source_database(tmp_path / "source.duckdb")
    with pytest.raises(ValueError, match="diferente"):
        build_demo_database(source, source)
