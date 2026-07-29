from pathlib import Path

import duckdb

from dengue_rj.dashboard.data import (
    annual_dengue,
    monthly_dengue,
    municipalities,
    sanitation,
)


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "dashboard.duckdb"
    with duckdb.connect(str(path)) as connection:
        connection.execute(
            """
            CREATE TABLE dim_municipio (
                codigo_ibge_municipio VARCHAR, nome_municipio VARCHAR
            );
            INSERT INTO dim_municipio VALUES
                ('3300020', 'Aperibé'), ('3300100', 'Angra dos Reis');

            CREATE TABLE indicador_dengue_municipio_ano (
                codigo_ibge_municipio VARCHAR, ano INTEGER,
                casos_provaveis BIGINT, casos_descartados BIGINT,
                populacao_residente BIGINT, incidencia_100_mil DOUBLE,
                eixo_temporal VARCHAR, criterio_territorial VARCHAR
            );
            INSERT INTO indicador_dengue_municipio_ano VALUES
                ('3300100', 2024, 100, 3, 200000, 50,
                 'primeiros_sintomas', 'municipio_residencia');

            CREATE TABLE serie_dengue_municipio_mes (
                codigo_ibge_municipio VARCHAR, mes DATE,
                casos_provaveis BIGINT, casos_descartados BIGINT,
                eixo_temporal VARCHAR, criterio_territorial VARCHAR
            );
            INSERT INTO serie_dengue_municipio_mes VALUES
                ('3300100', DATE '2024-01-01', 10, 1,
                 'primeiros_sintomas', 'municipio_residencia');

            CREATE TABLE fact_saneamento (
                codigo_ibge_municipio VARCHAR, ano INTEGER, sistema VARCHAR,
                componente VARCHAR, codigo_indicador VARCHAR,
                codigo_indicador_padronizado VARCHAR, nome_indicador VARCHAR,
                unidade VARCHAR, valor DOUBLE, valor_origem VARCHAR,
                status_valor VARCHAR, fonte VARCHAR,
                classificacao_comparabilidade VARCHAR
            );
            INSERT INTO fact_saneamento VALUES
                ('3300100', 2023, 'SINISA', 'agua', 'IAG0001', 'IAG0001',
                 'Atendimento', '%', 90, '90', 'informado', 'SINISA', 'direta');
            """
        )
    return path


def test_dashboard_queries_preserve_residence_and_sources(tmp_path: Path) -> None:
    database = _database(tmp_path)
    city = municipalities(database)
    annual = annual_dengue(database, "3300100")
    monthly = monthly_dengue(database, "3300100")
    sanitation_table = sanitation(database, "3300100")
    assert city["nome_municipio"].tolist() == ["Angra dos Reis", "Aperibé"]
    assert annual.loc[0, "criterio_territorial"] == "municipio_residencia"
    assert monthly.loc[0, "eixo_temporal"] == "primeiros_sintomas"
    assert sanitation_table.loc[0, "fonte"] == "SINISA"


def test_dashboard_queries_parameterize_municipality_code(tmp_path: Path) -> None:
    database = _database(tmp_path)
    malicious = "3300100' OR 1=1 --"
    assert annual_dengue(database, malicious).empty
    assert sanitation(database, malicious).empty
