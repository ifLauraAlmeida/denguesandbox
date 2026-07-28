import csv
from pathlib import Path

import duckdb

from dengue_rj.database.builder import TABLES, build_database, load_demography
from dengue_rj.metadata.schemas import COLLECTION_COLUMNS
from dengue_rj.metadata.writer import initialize_metadata


def test_metadata_headers(tmp_path: Path):
    created = initialize_metadata(tmp_path)
    assert len(created) == 4
    with (tmp_path / "dicionario_coleta.csv").open(encoding="utf-8") as stream:
        assert next(csv.reader(stream)) == COLLECTION_COLUMNS
    assert initialize_metadata(tmp_path) == []


def test_database_tables(tmp_path: Path):
    database = build_database(tmp_path / "test.duckdb")
    with duckdb.connect(str(database)) as connection:
        names = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
    assert set(TABLES).issubset(names)


def test_load_demography_materializes_validated_facts(tmp_path: Path):
    municipality_file = tmp_path / "municipalities.csv"
    population_file = tmp_path / "population.csv"
    municipalities = []
    population = []
    totals = {
        2020: 17_222_305,
        2021: 17_220_455,
        2022: 17_211_760,
        2023: 17_213_813,
        2024: 17_219_679,
    }
    for position in range(92):
        code = f"33{position:05d}"
        municipalities.append(
            {
                "codigo_ibge_municipio": code,
                "nome_municipio": f"Município {position}",
                "nome_municipio_normalizado": f"MUNICIPIO {position}",
                "uf": "RJ",
                "codigo_uf": "33",
                "codigo_regiao_saude": "33001",
                "regiao_saude": "Teste",
            }
        )
        for year, total in totals.items():
            base, remainder = divmod(total, 92)
            population.append(
                {
                    "codigo_ibge_municipio": code,
                    "nome_municipio_origem": f"Município {position}",
                    "ano": year,
                    "populacao_residente": base + (position < remainder),
                    "fonte": "RIPSA/SES-RJ",
                    "codificacao_origem": "utf-8-sig",
                }
            )
    import pandas as pd

    pd.DataFrame(municipalities).to_csv(municipality_file, index=False)
    pd.DataFrame(population).to_csv(population_file, index=False)
    database = load_demography(
        tmp_path / "test.duckdb", municipality_file, population_file
    )
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT count(*) FROM dim_municipio").fetchone()[0] == 92
        assert connection.execute("SELECT count(*) FROM fact_demografia").fetchone()[0] == 460
