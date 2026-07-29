"""Banco de demonstração limitado a agregados municipais."""

from pathlib import Path

import duckdb

DEMO_TABLES = (
    "dim_municipio",
    "indicador_dengue_municipio_ano",
    "serie_dengue_municipio_mes",
    "fact_saneamento",
)
FORBIDDEN_DEMO_TABLES = (
    "fact_dengue",
    "stg_dengue",
    "raw_dengue",
)


def build_demo_database(
    source_database: Path = Path("database/dengue_rj.duckdb"),
    output_database: Path = Path("database/dengue_rj_demo.duckdb"),
) -> Path:
    """Copia somente tabelas necessárias ao painel municipal agregado."""
    if source_database.resolve() == output_database.resolve():
        raise ValueError("Banco de demonstração deve ser diferente do banco analítico")
    output_database.parent.mkdir(parents=True, exist_ok=True)
    if output_database.exists():
        output_database.unlink()
    with duckdb.connect(str(source_database), read_only=True) as source:
        available = {row[0] for row in source.execute("SHOW TABLES").fetchall()}
        missing = set(DEMO_TABLES).difference(available)
        if missing:
            raise ValueError(f"Tabelas agregadas ausentes: {sorted(missing)}")
        with duckdb.connect(str(output_database)) as destination:
            for table in DEMO_TABLES:
                frame = source.execute(f"SELECT * FROM {table}").df()
                destination.register("_demo_frame", frame)
                destination.execute(f"CREATE TABLE {table} AS SELECT * FROM _demo_frame")
                destination.unregister("_demo_frame")
    _validate_demo_database(output_database)
    return output_database


def _validate_demo_database(database: Path) -> None:
    with duckdb.connect(str(database), read_only=True) as connection:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        if tables != set(DEMO_TABLES):
            raise ValueError(f"Tabelas inesperadas no banco de demonstração: {sorted(tables)}")
        forbidden = set(FORBIDDEN_DEMO_TABLES).intersection(tables)
        if forbidden:
            raise ValueError(f"Tabelas individuais proibidas na demonstração: {sorted(forbidden)}")
        criteria = {
            row[0]
            for row in connection.execute(
                """
                SELECT DISTINCT criterio_territorial
                FROM indicador_dengue_municipio_ano
                """
            ).fetchall()
        }
        if criteria != {"ID_MN_RESI"}:
            raise ValueError("Demonstração deve usar exclusivamente município de residência")
