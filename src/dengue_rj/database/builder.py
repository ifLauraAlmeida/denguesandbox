"""Criação e carga do schema analítico em DuckDB."""

from dataclasses import dataclass
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

SANITATION_FILES = (
    Path("data/processed/saneamento/snis_agua_esgoto_indicadores_2020_2022.csv"),
    Path("data/processed/saneamento/snis_residuos_solidos_indicadores_rj_2020_2022.csv"),
    Path("data/processed/saneamento/snis_aguas_pluviais_indicadores_rj_2020_2022.csv"),
    Path("data/processed/saneamento/sinisa_abastecimento_agua_indicadores_rj_2023.csv"),
    Path("data/processed/saneamento/sinisa_esgotamento_sanitario_indicadores_rj_2023.csv"),
    Path("data/processed/saneamento/sinisa_residuos_solidos_indicadores_rj_2023.csv"),
    Path("data/processed/saneamento/sinisa_aguas_pluviais_indicadores_rj_2023.csv"),
)
DENGUE_FILES = tuple(
    Path(f"data/processed/dengue/sinan_dengue_rj_residencia_{year}.csv")
    for year in range(2020, 2025)
)
LIRAA_FILE = Path("data/processed/liraa/liraa_municipio_levantamento_2020_2024.csv")


@dataclass(frozen=True)
class DengueTimeSeries:
    monthly_file: Path
    weekly_file: Path
    coverage_file: Path


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


def load_sanitation(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    municipality_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
    sanitation_files: tuple[Path, ...] = SANITATION_FILES,
    comparability_file: Path = Path(
        "data/processed/saneamento/"
        "comparabilidade_indicadores_agua_esgoto_snis_sinisa.csv"
    ),
) -> Path:
    """Valida e materializa indicadores SNIS 2020–2022 e SINISA 2023."""
    municipalities = pd.read_csv(municipality_file, dtype=str)
    sanitation = pd.concat(
        [_normalize_sanitation_file(path) for path in sanitation_files],
        ignore_index=True,
    )
    comparability = pd.read_csv(comparability_file, dtype=str)
    _validate_sanitation(municipalities, sanitation)

    direct = comparability[
        comparability["classificacao_comparabilidade"].eq("comparavel_direto")
    ][["codigo_snis", "codigo_sinisa"]]
    standard_codes = {
        code: row.codigo_sinisa
        for row in direct.itertuples()
        for code in (row.codigo_snis, row.codigo_sinisa)
    }
    classifications = {}
    for row in comparability.itertuples():
        classifications[row.codigo_snis] = row.classificacao_comparabilidade
        classifications[row.codigo_sinisa] = row.classificacao_comparabilidade
    sanitation["codigo_indicador_padronizado"] = sanitation["codigo_indicador"].map(
        standard_codes
    )
    sanitation["classificacao_comparabilidade"] = (
        sanitation["codigo_indicador"].map(classifications).fillna("nao_avaliado")
    )

    build_database(database_path)
    with duckdb.connect(str(database_path)) as connection:
        connection.register("_sanitation", sanitation)
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(
                """
                CREATE OR REPLACE TABLE stg_saneamento AS
                SELECT *, current_timestamp AS _ingested_at
                FROM _sanitation
                """
            )
            connection.execute(
                """
                CREATE OR REPLACE TABLE fact_saneamento AS
                SELECT
                    codigo_ibge_municipio, ano, componente, sistema,
                    codigo_prestador, nome_prestador, sigla_prestador,
                    abrangencia_prestador, familia_indicador,
                    codigo_indicador, codigo_indicador_padronizado,
                    classificacao_comparabilidade, nome_indicador, formula,
                    unidade, valor_origem, valor, status_valor,
                    status_resposta, fonte, nivel_origem,
                    current_timestamp AS _ingested_at
                FROM stg_saneamento
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_fact_saneamento_municipio_ano
                ON fact_saneamento(codigo_ibge_municipio, ano)
                """
            )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return database_path


def load_dengue(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    municipality_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
    dengue_files: tuple[Path, ...] = DENGUE_FILES,
) -> Path:
    """Valida e materializa casos SINAN/Dengue selecionados por residência."""
    municipalities = pd.read_csv(municipality_file, dtype=str)
    dengue = pd.concat(
        [pd.read_csv(path, dtype=str) for path in dengue_files],
        ignore_index=True,
    )
    _validate_dengue(municipalities, dengue)
    dengue["data_primeiros_sintomas"] = pd.to_datetime(
        dengue["DT_SIN_PRI"], format="mixed", errors="coerce"
    )
    dengue["data_notificacao"] = pd.to_datetime(
        dengue["DT_NOTIFIC"], format="mixed", errors="coerce"
    )
    dengue["atraso_notificacao_dias"] = (
        dengue["data_notificacao"] - dengue["data_primeiros_sintomas"]
    ).dt.days
    dengue["caso_descartado"] = dengue["CLASSI_FIN"].eq("5")
    dengue["caso_provavel"] = ~dengue["caso_descartado"]
    dengue["classificacao_final_rotulo"] = dengue["CLASSI_FIN"].map(
        {
            "5": "descartado",
            "10": "dengue",
            "11": "dengue_com_sinais_de_alarme",
            "12": "dengue_grave",
        }
    ).fillna("codigo_original_nao_rotulado")

    build_database(database_path)
    with duckdb.connect(str(database_path)) as connection:
        connection.register("_dengue", dengue)
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(
                """
                CREATE OR REPLACE TABLE stg_dengue AS
                SELECT *, current_timestamp AS _ingested_at
                FROM _dengue
                """
            )
            connection.execute(
                """
                CREATE OR REPLACE TABLE fact_dengue AS
                SELECT
                    codigo_ibge_municipio,
                    ANO_BASE::INTEGER AS ano_base,
                    CRITERIO_TERRITORIAL::VARCHAR AS criterio_territorial,
                    ID_MN_RESI::VARCHAR AS codigo_residencia_origem,
                    data_primeiros_sintomas,
                    data_notificacao,
                    atraso_notificacao_dias::INTEGER AS atraso_notificacao_dias,
                    SEM_PRI::VARCHAR AS semana_sintomas_origem,
                    SEM_NOT::VARCHAR AS semana_notificacao_origem,
                    CLASSI_FIN::VARCHAR AS classificacao_final_original,
                    classificacao_final_rotulo,
                    CRITERIO::VARCHAR AS criterio_confirmacao_original,
                    EVOLUCAO::VARCHAR AS evolucao_original,
                    DT_OBITO::VARCHAR AS data_obito_original,
                    DT_ENCERRA::VARCHAR AS data_encerramento_original,
                    SOROTIPO::VARCHAR AS sorotipo_original,
                    CS_SEXO::VARCHAR AS sexo_original,
                    NU_IDADE_N::VARCHAR AS idade_codificada_original,
                    caso_descartado,
                    caso_provavel,
                    current_timestamp AS _ingested_at
                FROM stg_dengue
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_fact_dengue_municipio_sintomas
                ON fact_dengue(codigo_ibge_municipio, data_primeiros_sintomas)
                """
            )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return database_path


def load_liraa(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    municipality_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
    liraa_file: Path = LIRAA_FILE,
) -> Path:
    """Valida e materializa os levantamentos municipais LIRAa/LIA."""
    municipalities = pd.read_csv(municipality_file, dtype=str)
    liraa = pd.read_csv(
        liraa_file,
        dtype={
            "codigo_ibge_municipio": str,
            "codigo_municipio_origem": str,
        },
    )
    _validate_liraa(municipalities, liraa)
    liraa["data_referencia"] = pd.to_datetime(
        {
            "year": liraa["ano"],
            "month": liraa["mes"],
            "day": 1,
        }
    )

    build_database(database_path)
    with duckdb.connect(str(database_path)) as connection:
        connection.register("_liraa", liraa)
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(
                """
                CREATE OR REPLACE TABLE stg_liraa AS
                SELECT *, current_timestamp AS _ingested_at
                FROM _liraa
                """
            )
            connection.execute(
                """
                CREATE OR REPLACE TABLE fact_liraa AS
                SELECT
                    codigo_ibge_municipio,
                    codigo_municipio_origem,
                    ano::INTEGER AS ano,
                    mes::INTEGER AS mes,
                    data_referencia,
                    periodo_execucao_origem,
                    status_levantamento,
                    iip_aedes_aegypti,
                    ib_aedes_aegypti,
                    estratos_iip_satisfatorio_n,
                    estratos_iip_satisfatorio_percentual,
                    estratos_iip_alerta_n,
                    estratos_iip_alerta_percentual,
                    estratos_iip_risco_n,
                    estratos_iip_risco_percentual,
                    criadouro_a1_n, criadouro_a1_percentual,
                    criadouro_a2_n, criadouro_a2_percentual,
                    criadouro_b_n, criadouro_b_percentual,
                    criadouro_c_n, criadouro_c_percentual,
                    criadouro_d1_n, criadouro_d1_percentual,
                    criadouro_d2_n, criadouro_d2_percentual,
                    criadouro_e_n, criadouro_e_percentual,
                    iip_aedes_albopictus,
                    ib_aedes_albopictus,
                    flag_outlier_ib_maior_100,
                    arquivo_origem,
                    fonte,
                    current_timestamp AS _ingested_at
                FROM stg_liraa
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_liraa_municipio_data
                ON fact_liraa(codigo_ibge_municipio, ano, mes)
                """
            )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return database_path


def _validate_liraa(
    municipalities: pd.DataFrame, liraa: pd.DataFrame
) -> None:
    required = {
        "codigo_ibge_municipio",
        "codigo_municipio_origem",
        "ano",
        "mes",
        "status_levantamento",
        "iip_aedes_aegypti",
        "ib_aedes_aegypti",
        "flag_outlier_ib_maior_100",
    }
    missing = required.difference(liraa.columns)
    if missing:
        raise ValueError(f"Campos obrigatórios ausentes no LIRAa: {sorted(missing)}")
    if liraa.duplicated(["codigo_ibge_municipio", "ano", "mes"]).any():
        raise ValueError("LIRAa contém chaves município–ano–mês duplicadas")
    unknown = set(liraa["codigo_ibge_municipio"]).difference(
        municipalities["codigo_ibge_municipio"]
    )
    if unknown:
        raise ValueError(f"LIRAa contém códigos municipais desconhecidos: {unknown}")
    if not set(liraa["ano"].astype(int)).issubset(range(2020, 2025)):
        raise ValueError("LIRAa contém ano fora de 2020–2024")
    if not set(liraa["status_levantamento"]).issubset(
        {"observado", "justificativa", "nao_informado"}
    ):
        raise ValueError("LIRAa contém status de levantamento desconhecido")


def build_dengue_indicators(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    output_file: Path = Path(
        "data/processed/dengue/indicadores_dengue_municipio_ano_2020_2024.csv"
    ),
) -> Path:
    """Calcula casos e incidência por município e ano dos primeiros sintomas."""
    with duckdb.connect(str(database_path)) as connection:
        required = {"dim_municipio", "fact_demografia", "fact_dengue"}
        available = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        missing = required.difference(available)
        if missing:
            raise ValueError(f"Tabelas necessárias ausentes: {sorted(missing)}")
        connection.execute(
            """
            CREATE OR REPLACE TABLE indicador_dengue_municipio_ano AS
            WITH casos AS (
                SELECT
                    codigo_ibge_municipio,
                    year(data_primeiros_sintomas)::INTEGER AS ano,
                    count(*) FILTER (WHERE caso_provavel) AS casos_provaveis,
                    count(*) FILTER (WHERE caso_descartado) AS casos_descartados
                FROM fact_dengue
                WHERE year(data_primeiros_sintomas) BETWEEN 2020 AND 2024
                GROUP BY 1, 2
            )
            SELECT
                d.codigo_ibge_municipio,
                m.nome_municipio,
                d.ano,
                coalesce(c.casos_provaveis, 0)::BIGINT AS casos_provaveis,
                coalesce(c.casos_descartados, 0)::BIGINT AS casos_descartados,
                d.populacao_residente,
                (
                    coalesce(c.casos_provaveis, 0)::DOUBLE
                    / d.populacao_residente * 100000
                ) AS incidencia_100_mil,
                'DT_SIN_PRI'::VARCHAR AS eixo_temporal,
                'ID_MN_RESI'::VARCHAR AS criterio_territorial,
                current_timestamp AS _calculated_at
            FROM fact_demografia d
            JOIN dim_municipio m USING (codigo_ibge_municipio)
            LEFT JOIN casos c USING (codigo_ibge_municipio, ano)
            WHERE d.ano BETWEEN 2020 AND 2024
            ORDER BY d.ano, d.codigo_ibge_municipio
            """
        )
        result = connection.execute(
            "SELECT * EXCLUDE (_calculated_at) FROM indicador_dengue_municipio_ano"
        ).df()
    if len(result) != 460:
        raise ValueError(f"Esperados 460 indicadores município-ano; recebidos {len(result)}")
    if result.duplicated(["codigo_ibge_municipio", "ano"]).any():
        raise ValueError("Indicadores de dengue contêm chaves duplicadas")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)
    return output_file


def build_dengue_time_series(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    output_directory: Path = Path("data/processed/dengue"),
) -> DengueTimeSeries:
    """Materializa séries mensais e semanais com zeros municipais explícitos."""
    with duckdb.connect(str(database_path)) as connection:
        required = {"dim_municipio", "fact_dengue"}
        available = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        missing = required.difference(available)
        if missing:
            raise ValueError(f"Tabelas necessárias ausentes: {sorted(missing)}")
        connection.execute(
            """
            CREATE OR REPLACE TABLE serie_dengue_municipio_mes AS
            WITH meses AS (
                SELECT unnest(generate_series(
                    DATE '2020-01-01', DATE '2024-12-01', INTERVAL 1 MONTH
                ))::DATE AS mes
            ),
            casos AS (
                SELECT
                    codigo_ibge_municipio,
                    date_trunc('month', data_primeiros_sintomas)::DATE AS mes,
                    count(*) FILTER (WHERE caso_provavel) AS casos_provaveis,
                    count(*) FILTER (WHERE caso_descartado) AS casos_descartados
                FROM fact_dengue
                WHERE data_primeiros_sintomas >= DATE '2020-01-01'
                  AND data_primeiros_sintomas < DATE '2025-01-01'
                GROUP BY 1, 2
            )
            SELECT
                m.codigo_ibge_municipio,
                m.nome_municipio,
                e.mes,
                coalesce(c.casos_provaveis, 0)::BIGINT AS casos_provaveis,
                coalesce(c.casos_descartados, 0)::BIGINT AS casos_descartados,
                'DT_SIN_PRI'::VARCHAR AS eixo_temporal,
                'ID_MN_RESI'::VARCHAR AS criterio_territorial
            FROM dim_municipio m
            CROSS JOIN meses e
            LEFT JOIN casos c USING (codigo_ibge_municipio, mes)
            ORDER BY mes, codigo_ibge_municipio
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE TABLE serie_dengue_municipio_semana AS
            WITH semanas_validas AS (
                SELECT DISTINCT semana_sintomas_origem AS semana_epidemiologica
                FROM fact_dengue
                WHERE try_cast(left(semana_sintomas_origem, 4) AS INTEGER)
                      BETWEEN 2020 AND 2024
                  AND try_cast(right(semana_sintomas_origem, 2) AS INTEGER)
                      BETWEEN 1 AND 53
            ),
            casos AS (
                SELECT
                    codigo_ibge_municipio,
                    semana_sintomas_origem AS semana_epidemiologica,
                    count(*) FILTER (WHERE caso_provavel) AS casos_provaveis,
                    count(*) FILTER (WHERE caso_descartado) AS casos_descartados
                FROM fact_dengue
                WHERE try_cast(left(semana_sintomas_origem, 4) AS INTEGER)
                      BETWEEN 2020 AND 2024
                  AND try_cast(right(semana_sintomas_origem, 2) AS INTEGER)
                      BETWEEN 1 AND 53
                GROUP BY 1, 2
            )
            SELECT
                m.codigo_ibge_municipio,
                m.nome_municipio,
                s.semana_epidemiologica,
                coalesce(c.casos_provaveis, 0)::BIGINT AS casos_provaveis,
                coalesce(c.casos_descartados, 0)::BIGINT AS casos_descartados,
                'SEM_PRI'::VARCHAR AS eixo_temporal,
                'ID_MN_RESI'::VARCHAR AS criterio_territorial
            FROM dim_municipio m
            CROSS JOIN semanas_validas s
            LEFT JOIN casos c USING (
                codigo_ibge_municipio, semana_epidemiologica
            )
            ORDER BY semana_epidemiologica, codigo_ibge_municipio
            """
        )
        monthly = connection.execute(
            "SELECT * FROM serie_dengue_municipio_mes"
        ).df()
        weekly = connection.execute(
            "SELECT * FROM serie_dengue_municipio_semana"
        ).df()
        coverage = connection.execute(
            """
            SELECT
                ano_base,
                count(*) AS registros,
                count(DISTINCT codigo_ibge_municipio) AS municipios,
                count(data_primeiros_sintomas) AS datas_sintomas_validas,
                count(data_notificacao) AS datas_notificacao_validas,
                count(*) FILTER (WHERE caso_provavel) AS casos_provaveis,
                count(*) FILTER (WHERE caso_descartado) AS casos_descartados,
                count(*) FILTER (
                    WHERE classificacao_final_rotulo =
                          'codigo_original_nao_rotulado'
                ) AS classificacoes_nao_rotuladas,
                count(*) FILTER (
                    WHERE data_primeiros_sintomas < DATE '2020-01-01'
                       OR data_primeiros_sintomas >= DATE '2025-01-01'
                ) AS sintomas_fora_periodo,
                median(atraso_notificacao_dias) AS atraso_mediano_dias
            FROM fact_dengue
            GROUP BY ano_base
            ORDER BY ano_base
            """
        ).df()
    if len(monthly) != 92 * 60:
        raise ValueError(f"Série mensal incompleta: {len(monthly)} registros")
    if len(weekly) % 92 or weekly["semana_epidemiologica"].nunique() < 260:
        raise ValueError("Série semanal não possui grade municipal completa")
    output_directory.mkdir(parents=True, exist_ok=True)
    monthly_file = output_directory / "serie_dengue_municipio_mes_2020_2024.csv"
    weekly_file = output_directory / "serie_dengue_municipio_semana_2020_2024.csv"
    coverage_file = output_directory / "cobertura_sinan_dengue_2020_2024.csv"
    monthly.to_csv(monthly_file, index=False)
    weekly.to_csv(weekly_file, index=False)
    coverage.to_csv(coverage_file, index=False)
    return DengueTimeSeries(monthly_file, weekly_file, coverage_file)


def _validate_dengue(
    municipalities: pd.DataFrame, dengue: pd.DataFrame
) -> None:
    required = {
        "codigo_ibge_municipio",
        "ANO_BASE",
        "CRITERIO_TERRITORIAL",
        "ID_MN_RESI",
        "DT_SIN_PRI",
        "DT_NOTIFIC",
        "CLASSI_FIN",
    }
    missing = required.difference(dengue.columns)
    if missing:
        raise ValueError(f"Campos obrigatórios ausentes no dengue: {sorted(missing)}")
    if set(dengue["CRITERIO_TERRITORIAL"]) != {"municipio_residencia"}:
        raise ValueError("Dengue deve usar exclusivamente município de residência")
    unknown = set(dengue["codigo_ibge_municipio"]).difference(
        municipalities["codigo_ibge_municipio"]
    )
    if unknown:
        raise ValueError(f"Dengue contém códigos municipais desconhecidos: {unknown}")
    if set(dengue["ANO_BASE"].astype(int)) != set(range(2020, 2025)):
        raise ValueError("Dengue deve cobrir exatamente 2020–2024")
    if not dengue["ID_MN_RESI"].str.startswith("33").all():
        raise ValueError("Dengue contém residência de fora do RJ")


def _normalize_sanitation_file(path: Path) -> pd.DataFrame:
    table = pd.read_csv(path, dtype={"codigo_ibge_municipio": str})
    if path.name.startswith("sinisa_"):
        table["sistema"] = "SINISA"
    else:
        table["sistema"] = "SNIS"
        if "residuos_solidos" in path.name:
            table["componente"] = "residuos_solidos"
        elif "aguas_pluviais" in path.name:
            table["componente"] = "aguas_pluviais"
        else:
            table["componente"] = table["codigo_indicador"].map(
                lambda code: (
                    "abastecimento_agua"
                    if code in {"IN049", "IN055"}
                    else "esgotamento_sanitario"
                )
            )
        table["valor_origem"] = table["valor"]
        table["status_valor"] = table["valor"].map(
            lambda value: "ausente" if pd.isna(value) else "observado"
        )
        table["status_resposta"] = ""
        table["familia_indicador"] = table.get("familia_indicador", "")
        table["formula"] = table.get("formula", "")
        table["nivel_origem"] = table.get("nivel_origem", "municipio")
        table["nome_prestador"] = table.get("nome_prestador", "")
        table["sigla_prestador"] = table.get("sigla_prestador", "")
        table["codigo_prestador"] = table.get("codigo_prestador", "")
        table["abrangencia_prestador"] = table.get("abrangencia", "")
    columns = [
        "codigo_ibge_municipio", "ano", "componente", "sistema",
        "codigo_prestador", "nome_prestador", "sigla_prestador",
        "abrangencia_prestador", "familia_indicador", "codigo_indicador",
        "nome_indicador", "formula", "unidade", "valor_origem", "valor",
        "status_valor", "status_resposta", "fonte", "nivel_origem",
    ]
    for column in columns:
        if column not in table:
            table[column] = ""
    return table[columns]


def _validate_sanitation(
    municipalities: pd.DataFrame, sanitation: pd.DataFrame
) -> None:
    if sanitation.empty:
        raise ValueError("Nenhum registro de saneamento foi recebido")
    unknown = set(sanitation["codigo_ibge_municipio"]).difference(
        municipalities["codigo_ibge_municipio"]
    )
    if unknown:
        raise ValueError(f"Saneamento contém códigos municipais desconhecidos: {unknown}")
    if set(sanitation["ano"]) != {2020, 2021, 2022, 2023}:
        raise ValueError("Saneamento deve cobrir os anos de 2020 a 2023")
    if set(sanitation["componente"]) != {
        "abastecimento_agua",
        "esgotamento_sanitario",
        "residuos_solidos",
        "aguas_pluviais",
    }:
        raise ValueError("Saneamento deve conter exatamente os quatro componentes")


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
