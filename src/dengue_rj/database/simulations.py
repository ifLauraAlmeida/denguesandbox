"""Persistência append-only de execuções SIR explicitamente rotuladas."""

from pathlib import Path

import duckdb
import pandas as pd

REQUIRED_SIMULATION_COLUMNS = {
    "execution_id",
    "codigo_ibge_municipio",
    "municipio",
    "tempo",
    "cenario",
    "susceptible",
    "infected",
    "removed",
    "new_infections",
    "new_removals",
    "beta",
    "gamma",
    "basic_reproduction_number",
    "effective_reproduction_number",
    "population",
    "model_version",
}


def store_sir_simulation(
    simulation: pd.DataFrame,
    database: Path = Path("database/dengue_rj.duckdb"),
) -> int:
    """Acrescenta uma execução completa e recusa sobrescrita ou duplicação."""
    missing = REQUIRED_SIMULATION_COLUMNS.difference(simulation.columns)
    if missing:
        raise ValueError(f"Colunas ausentes na simulação: {sorted(missing)}")
    execution_ids = simulation["execution_id"].dropna().astype(str).unique()
    if len(execution_ids) != 1 or not execution_ids[0].strip():
        raise ValueError("A simulação deve conter exatamente um execution_id não vazio")
    execution_id = execution_ids[0]
    if simulation.empty:
        raise ValueError("A simulação não pode ser vazia")
    if simulation["tempo"].duplicated().any():
        raise ValueError("tempo deve ser único dentro da execução")
    if not database.exists():
        raise FileNotFoundError(f"Banco ausente: {database}")

    with duckdb.connect(str(database)) as connection:
        columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'fact_sir_simulacao'
                """
            ).fetchall()
        }
        if columns == {"_ingested_at"}:
            count = connection.execute(
                "SELECT count(*) FROM fact_sir_simulacao"
            ).fetchone()[0]
            if count:
                raise ValueError("Schema legado de fact_sir_simulacao contém dados")
            connection.execute("DROP TABLE fact_sir_simulacao")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fact_sir_simulacao (
                execution_id VARCHAR NOT NULL,
                codigo_ibge_municipio VARCHAR NOT NULL,
                municipio VARCHAR NOT NULL,
                tempo DOUBLE NOT NULL,
                cenario VARCHAR NOT NULL,
                susceptible DOUBLE NOT NULL,
                infected DOUBLE NOT NULL,
                removed DOUBLE NOT NULL,
                new_infections DOUBLE NOT NULL,
                new_removals DOUBLE NOT NULL,
                beta DOUBLE NOT NULL,
                gamma DOUBLE NOT NULL,
                basic_reproduction_number DOUBLE NOT NULL,
                effective_reproduction_number DOUBLE NOT NULL,
                population DOUBLE NOT NULL,
                model_version VARCHAR NOT NULL,
                _ingested_at TIMESTAMP WITH TIME ZONE DEFAULT current_timestamp,
                PRIMARY KEY (execution_id, tempo)
            )
            """
        )
        duplicate = connection.execute(
            "SELECT count(*) FROM fact_sir_simulacao WHERE execution_id = ?",
            [execution_id],
        ).fetchone()[0]
        if duplicate:
            raise ValueError(f"execution_id já armazenado: {execution_id}")
        frame = simulation[list(REQUIRED_SIMULATION_COLUMNS)].copy()
        connection.register("_simulation_frame", frame)
        connection.execute(
            """
            INSERT INTO fact_sir_simulacao (
                execution_id, codigo_ibge_municipio, municipio, tempo, cenario,
                susceptible, infected, removed, new_infections, new_removals,
                beta, gamma, basic_reproduction_number,
                effective_reproduction_number, population, model_version
            )
            SELECT
                execution_id, codigo_ibge_municipio, municipio, tempo, cenario,
                susceptible, infected, removed, new_infections, new_removals,
                beta, gamma, basic_reproduction_number,
                effective_reproduction_number, population, model_version
            FROM _simulation_frame
            """
        )
        connection.unregister("_simulation_frame")
    return len(simulation)
