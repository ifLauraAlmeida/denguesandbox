import csv
from pathlib import Path

import duckdb

from dengue_rj.database.builder import (
    TABLES,
    build_database,
    build_dengue_indicators,
    load_demography,
    load_dengue,
    load_sanitation,
)
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


def test_load_sanitation_preserves_status_and_only_direct_mapping(tmp_path: Path):
    import pandas as pd

    municipality_file = tmp_path / "municipalities.csv"
    pd.DataFrame({"codigo_ibge_municipio": ["3300100"]}).to_csv(
        municipality_file, index=False
    )
    components = (
        "abastecimento_agua",
        "esgotamento_sanitario",
        "residuos_solidos",
        "aguas_pluviais",
    )
    codes = ("IN055", "IN015", "IRS0001", "IAP0001")
    files = []
    for year, component, code in zip(range(2020, 2024), components, codes):
        path = tmp_path / f"sinisa_{component}_{year}.csv"
        pd.DataFrame(
            {
                "codigo_ibge_municipio": ["3300100"],
                "ano": [year],
                "componente": [component],
                "codigo_indicador": [code],
                "valor_origem": ["Div/0" if year == 2023 else "1"],
                "valor": [None if year == 2023 else 1.0],
                "status_valor": ["Div/0" if year == 2023 else "observado"],
            }
        ).to_csv(path, index=False)
        files.append(path)
    comparability_file = tmp_path / "comparability.csv"
    pd.DataFrame(
        {
            "codigo_snis": ["IN055", "IN015"],
            "codigo_sinisa": ["IAG0001", "IES2002"],
            "classificacao_comparabilidade": [
                "comparavel_direto",
                "similar_ruptura_definicao",
            ],
        }
    ).to_csv(comparability_file, index=False)

    database = load_sanitation(
        tmp_path / "test.duckdb",
        municipality_file,
        tuple(files),
        comparability_file,
    )
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT count(*) FROM fact_saneamento").fetchone()[0] == 4
        mappings = connection.execute(
            """
            SELECT codigo_indicador, codigo_indicador_padronizado
            FROM fact_saneamento ORDER BY codigo_indicador
            """
        ).fetchall()
        assert ("IN055", "IAG0001") in mappings
        assert ("IN015", None) in mappings
        assert connection.execute(
            "SELECT status_valor FROM fact_saneamento WHERE ano = 2023"
        ).fetchone()[0] == "Div/0"


def test_load_dengue_uses_residence_and_official_probable_rule(tmp_path: Path):
    import pandas as pd

    municipality_file = tmp_path / "municipalities.csv"
    pd.DataFrame({"codigo_ibge_municipio": ["3300100"]}).to_csv(
        municipality_file, index=False
    )
    files = []
    for year, classification in zip(range(2020, 2025), ("5", "10", "8", "0", None)):
        path = tmp_path / f"dengue_{year}.csv"
        pd.DataFrame(
            {
                "codigo_ibge_municipio": ["3300100"],
                "ANO_BASE": [year],
                "CRITERIO_TERRITORIAL": ["municipio_residencia"],
                "ID_MN_RESI": ["330010"],
                "DT_SIN_PRI": [f"{year}0101"],
                "DT_NOTIFIC": [f"{year}0103"],
                "SEM_PRI": [f"{year}01"],
                "SEM_NOT": [f"{year}01"],
                "CLASSI_FIN": [classification],
                "CRITERIO": [None],
                "EVOLUCAO": [None],
                "DT_OBITO": [None],
                "DT_ENCERRA": [None],
                "SOROTIPO": [None],
                "CS_SEXO": ["F"],
                "NU_IDADE_N": ["4030"],
            }
        ).to_csv(path, index=False)
        files.append(path)

    database = load_dengue(
        tmp_path / "test.duckdb",
        municipality_file,
        tuple(files),
    )
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT count(*) FROM fact_dengue").fetchone()[0] == 5
        assert connection.execute(
            "SELECT count(*) FROM fact_dengue WHERE caso_provavel"
        ).fetchone()[0] == 4
        assert connection.execute(
            "SELECT atraso_notificacao_dias FROM fact_dengue LIMIT 1"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT distinct criterio_territorial FROM fact_dengue"
        ).fetchall() == [("municipio_residencia",)]


def test_build_dengue_indicators_includes_zero_case_municipalities(tmp_path: Path):
    import pandas as pd

    database = tmp_path / "test.duckdb"
    codes = ["3300100", "3304557", *(f"33{position:05d}" for position in range(90))]
    municipalities = pd.DataFrame(
        {
            "codigo_ibge_municipio": codes,
            "nome_municipio": [f"Município {position}" for position in range(92)],
        }
    )
    demography = pd.DataFrame(
        [
            {
                "codigo_ibge_municipio": code,
                "ano": year,
                "populacao_residente": 100_000,
            }
            for code in municipalities["codigo_ibge_municipio"]
            for year in range(2020, 2025)
        ]
    )
    dengue = pd.DataFrame(
        {
            "codigo_ibge_municipio": ["3300100", "3300100"],
            "data_primeiros_sintomas": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "caso_provavel": [True, True],
            "caso_descartado": [False, False],
        }
    )
    with duckdb.connect(str(database)) as connection:
        connection.register("_municipalities", municipalities)
        connection.register("_demography", demography)
        connection.register("_dengue", dengue)
        connection.execute("CREATE TABLE dim_municipio AS SELECT * FROM _municipalities")
        connection.execute("CREATE TABLE fact_demografia AS SELECT * FROM _demography")
        connection.execute("CREATE TABLE fact_dengue AS SELECT * FROM _dengue")

    output = build_dengue_indicators(database, tmp_path / "indicators.csv")
    result = pd.read_csv(output, dtype={"codigo_ibge_municipio": str})
    assert len(result) == 460
    angra = result[
        (result["codigo_ibge_municipio"] == "3300100") & (result["ano"] == 2020)
    ].iloc[0]
    rio = result[
        (result["codigo_ibge_municipio"] == "3304557") & (result["ano"] == 2020)
    ].iloc[0]
    assert angra["casos_provaveis"] == 2
    assert angra["incidencia_100_mil"] == 2
    assert rio["casos_provaveis"] == 0
