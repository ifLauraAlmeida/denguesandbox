"""Consultas somente leitura usadas pelo Streamlit."""

from pathlib import Path

import duckdb
import pandas as pd


def municipalities(database_path: Path) -> pd.DataFrame:
    """Lista municípios em ordem alfabética, sem escolher um padrão."""
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(
            """
            SELECT codigo_ibge_municipio, nome_municipio
            FROM dim_municipio
            ORDER BY nome_municipio
            """
        ).df()


def annual_dengue(database_path: Path, municipality_code: str) -> pd.DataFrame:
    """Retorna indicadores anuais calculados por residência."""
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(
            """
            SELECT ano, casos_provaveis, casos_descartados,
                   populacao_residente, incidencia_100_mil,
                   eixo_temporal, criterio_territorial
            FROM indicador_dengue_municipio_ano
            WHERE codigo_ibge_municipio = ?
            ORDER BY ano
            """,
            [municipality_code],
        ).df()


def monthly_dengue(database_path: Path, municipality_code: str) -> pd.DataFrame:
    """Retorna casos mensais pelo início dos sintomas e residência."""
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(
            """
            SELECT mes, casos_provaveis, casos_descartados,
                   eixo_temporal, criterio_territorial
            FROM serie_dengue_municipio_mes
            WHERE codigo_ibge_municipio = ?
            ORDER BY mes
            """,
            [municipality_code],
        ).df()


def sanitation(database_path: Path, municipality_code: str) -> pd.DataFrame:
    """Retorna saneamento preservando fonte, unidade e status."""
    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(
            """
            SELECT ano, sistema, componente, codigo_indicador,
                   codigo_indicador_padronizado, nome_indicador, unidade,
                   valor, valor_origem, status_valor, fonte,
                   classificacao_comparabilidade
            FROM fact_saneamento
            WHERE codigo_ibge_municipio = ?
            ORDER BY ano DESC, componente, codigo_indicador
            """,
            [municipality_code],
        ).df()
