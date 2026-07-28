"""Criação e carga do schema analítico em DuckDB."""

from pathlib import Path

import duckdb
import pandas as pd

TABLES = (
    "raw_demografia", "raw_saneamento", "raw_dengue",
    "stg_demografia", "stg_saneamento", "stg_dengue",
    "dim_municipio", "dim_tempo", "dim_indicador",
    "fact_demografia", "fact_saneamento", "fact_dengue", "fact_sir_simulacao",
)


def build_database(path: Path = Path("database/dengue_rj.duckdb")) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as connection:
        for table in TABLES:
            connection.execute(f'CREATE TABLE IF NOT EXISTS "{table}" (_ingested_at TIMESTAMP)')
        connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata_schema_version "
            "(version VARCHAR PRIMARY KEY, applied_at TIMESTAMP DEFAULT current_timestamp)"
        )
        connection.execute("INSERT OR IGNORE INTO metadata_schema_version(version) VALUES ('0.1.0')")
    return path


EXPECTED_POPULATION_TOTALS = {
    2020: 17_222_305,
    2021: 17_220_455,
    2022: 17_211_760,
    2023: 17_213_813,
    2024: 17_219_679,
}


def load_demography(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    municipality_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
    population_file: Path = Path(
        "data/processed/demografia/populacao_ripsa_2020_2024.csv"
    ),
) -> Path:
    """Valida e materializa dimensão municipal e população RIPSA."""
    municipalities = pd.read_csv(municipality_file, dtype=str)
    population = pd.read_csv(
        population_file,
        dtype={"codigo_ibge_municipio": str, "ano": int, "populacao_residente": int},
    )
    _validate_demography(municipalities, population)

    build_database(database_path)
    with duckdb.connect(str(database_path)) as connection:
        connection.register("_municipalities", municipalities)
        connection.register("_population", population)
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(
                """
                CREATE OR REPLACE TABLE dim_municipio AS
                SELECT
                    codigo_ibge_municipio::VARCHAR AS codigo_ibge_municipio,
                    nome_municipio::VARCHAR AS nome_municipio,
                    nome_municipio_normalizado::VARCHAR AS nome_municipio_normalizado,
                    uf::VARCHAR AS uf,
                    codigo_uf::VARCHAR AS codigo_uf,
                    codigo_regiao_saude::VARCHAR AS codigo_regiao_saude,
                    regiao_saude::VARCHAR AS regiao_saude
                FROM _municipalities
                """
            )
            connection.execute(
                """
                CREATE OR REPLACE TABLE stg_demografia AS
                SELECT
                    codigo_ibge_municipio::VARCHAR AS codigo_ibge_municipio,
                    nome_municipio_origem::VARCHAR AS nome_municipio_origem,
                    ano::INTEGER AS ano,
                    populacao_residente::BIGINT AS populacao_residente,
                    fonte::VARCHAR AS fonte,
                    codificacao_origem::VARCHAR AS codificacao_origem,
                    current_timestamp AS _ingested_at
                FROM _population
                """
            )
            connection.execute(
                """
                CREATE OR REPLACE TABLE fact_demografia AS
                SELECT
                    codigo_ibge_municipio,
                    ano,
                    populacao_residente,
                    fonte AS fonte_populacao,
                    current_timestamp AS _ingested_at
                FROM stg_demografia
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_demografia
                ON fact_demografia(codigo_ibge_municipio, ano)
                """
            )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return database_path


def _validate_demography(
    municipalities: pd.DataFrame, population: pd.DataFrame
) -> None:
    required_dimension = {
        "codigo_ibge_municipio",
        "nome_municipio",
        "nome_municipio_normalizado",
        "uf",
        "codigo_uf",
        "codigo_regiao_saude",
        "regiao_saude",
    }
    missing = required_dimension.difference(municipalities.columns)
    if missing:
        raise ValueError(f"Colunas ausentes em dim_municipio: {sorted(missing)}")
    if len(municipalities) != 92 or municipalities["codigo_ibge_municipio"].nunique() != 92:
        raise ValueError("dim_municipio deve conter exatamente 92 códigos únicos")
    if len(population) != 460:
        raise ValueError(f"Esperados 460 registros demográficos; recebidos {len(population)}")
    if population.duplicated(["codigo_ibge_municipio", "ano"]).any():
        raise ValueError("Chaves município-ano duplicadas na população")
    if set(population["codigo_ibge_municipio"]).difference(
        municipalities["codigo_ibge_municipio"]
    ):
        raise ValueError("População contém código ausente na dimensão municipal")
    totals = population.groupby("ano")["populacao_residente"].sum().to_dict()
    if totals != EXPECTED_POPULATION_TOTALS:
        raise ValueError(f"Totais RIPSA divergentes: {totals}")
