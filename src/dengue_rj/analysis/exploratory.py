"""Análise descritiva municipal de dengue e saneamento."""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
from scipy.stats import pearsonr, spearmanr


@dataclass(frozen=True)
class ExploratoryOutputs:
    incidence_summary: Path
    incidence_extremes: Path
    sanitation_cross_section: Path
    sanitation_associations: Path
    provider_duplicates: Path
    report: Path


def build_exploratory_analysis(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    table_directory: Path = Path("outputs/tables"),
    report_directory: Path = Path("outputs/reports"),
) -> ExploratoryOutputs:
    """Produz estatísticas descritivas sem alegação causal."""
    with duckdb.connect(str(database_path), read_only=True) as connection:
        incidence = connection.execute(
            "SELECT * EXCLUDE (_calculated_at) FROM indicador_dengue_municipio_ano"
        ).df()
        sanitation = connection.execute(
            """
            SELECT
                codigo_ibge_municipio,
                codigo_indicador_padronizado,
                valor,
                status_valor
            FROM fact_saneamento
            WHERE sistema = 'SINISA'
              AND ano = 2023
              AND codigo_indicador_padronizado IN ('IAG0001', 'IES0001')
            """
        ).df()
        duplicates = connection.execute(
            """
            SELECT
                sistema, ano, codigo_indicador_padronizado,
                codigo_ibge_municipio,
                count(*) AS quantidade_prestadores,
                string_agg(DISTINCT nome_prestador, ' | ') AS prestadores
            FROM fact_saneamento
            WHERE codigo_indicador_padronizado IS NOT NULL
            GROUP BY 1, 2, 3, 4
            HAVING count(*) > 1
            ORDER BY ano, codigo_indicador_padronizado,
                     quantidade_prestadores DESC, codigo_ibge_municipio
            """
        ).df()

    summary = _incidence_summary(incidence)
    extremes = _incidence_extremes(incidence)
    cross_section = _sanitation_cross_section(incidence, sanitation)
    associations = _sanitation_associations(cross_section)

    table_directory.mkdir(parents=True, exist_ok=True)
    report_directory.mkdir(parents=True, exist_ok=True)
    incidence_summary = table_directory / "resumo_incidencia_municipal_2020_2024.csv"
    incidence_extremes = table_directory / "extremos_incidencia_municipal_2020_2024.csv"
    sanitation_cross_section = table_directory / "dengue_saneamento_2023.csv"
    sanitation_associations = table_directory / "associacoes_dengue_saneamento_2023.csv"
    provider_duplicates = table_directory / "duplicidades_prestador_saneamento.csv"
    report = report_directory / "analise_exploratoria.md"
    summary.to_csv(incidence_summary, index=False)
    extremes.to_csv(incidence_extremes, index=False)
    cross_section.to_csv(sanitation_cross_section, index=False)
    associations.to_csv(sanitation_associations, index=False)
    duplicates.to_csv(provider_duplicates, index=False)
    report.write_text(
        _render_report(summary, extremes, associations, duplicates),
        encoding="utf-8",
    )
    return ExploratoryOutputs(
        incidence_summary,
        incidence_extremes,
        sanitation_cross_section,
        sanitation_associations,
        provider_duplicates,
        report,
    )


def _incidence_summary(incidence: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, group in incidence.groupby("ano", sort=True):
        values = group["incidencia_100_mil"]
        rows.append(
            {
                "ano": year,
                "municipios": len(group),
                "casos_provaveis": group["casos_provaveis"].sum(),
                "populacao": group["populacao_residente"].sum(),
                "incidencia_agregada_100_mil": (
                    group["casos_provaveis"].sum()
                    / group["populacao_residente"].sum()
                    * 100_000
                ),
                "incidencia_municipal_media": values.mean(),
                "incidencia_municipal_mediana": values.median(),
                "incidencia_municipal_p25": values.quantile(0.25),
                "incidencia_municipal_p75": values.quantile(0.75),
                "incidencia_municipal_min": values.min(),
                "incidencia_municipal_max": values.max(),
                "municipios_sem_caso": group["casos_provaveis"].eq(0).sum(),
            }
        )
    return pd.DataFrame(rows)


def _incidence_extremes(incidence: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for year, group in incidence.groupby("ano", sort=True):
        ordered = group.sort_values(
            ["incidencia_100_mil", "codigo_ibge_municipio"],
            ascending=[False, True],
        )
        top = ordered.head(10).copy()
        top.insert(0, "extremo", "maior")
        top.insert(1, "posicao", range(1, len(top) + 1))
        bottom = ordered.sort_values(
            ["incidencia_100_mil", "codigo_ibge_municipio"]
        ).head(10).copy()
        bottom.insert(0, "extremo", "menor")
        bottom.insert(1, "posicao", range(1, len(bottom) + 1))
        frames.extend((top, bottom))
    return pd.concat(frames, ignore_index=True)


def _sanitation_cross_section(
    incidence: pd.DataFrame, sanitation: pd.DataFrame
) -> pd.DataFrame:
    values = sanitation.pivot(
        index="codigo_ibge_municipio",
        columns="codigo_indicador_padronizado",
        values="valor",
    ).reset_index()
    values = values.rename(
        columns={
            "IAG0001": "atendimento_agua_percentual",
            "IES0001": "atendimento_esgoto_percentual",
        }
    )
    annual = incidence[incidence["ano"].eq(2023)].copy()
    return annual.merge(values, on="codigo_ibge_municipio", how="left")


def _sanitation_associations(cross_section: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in ("atendimento_agua_percentual", "atendimento_esgoto_percentual"):
        valid = cross_section[["incidencia_100_mil", column]].dropna()
        pearson = pearsonr(valid[column], valid["incidencia_100_mil"])
        spearman = spearmanr(valid[column], valid["incidencia_100_mil"])
        rows.append(
            {
                "ano": 2023,
                "indicador_saneamento": column,
                "observacoes": len(valid),
                "pearson_r": pearson.statistic,
                "pearson_p": pearson.pvalue,
                "spearman_rho": spearman.statistic,
                "spearman_p": spearman.pvalue,
                "interpretacao": "associacao_exploratoria_nao_causal",
            }
        )
    return pd.DataFrame(rows)


def _render_report(
    summary: pd.DataFrame,
    extremes: pd.DataFrame,
    associations: pd.DataFrame,
    duplicates: pd.DataFrame,
) -> str:
    top_2024 = extremes[
        (extremes["ano"].eq(2024)) & (extremes["extremo"].eq("maior"))
    ][["posicao", "nome_municipio", "incidencia_100_mil"]]
    return (
        "# Análise exploratória municipal\n\n"
        "Resultados descritivos e associações exploratórias. Correlação não "
        "implica causalidade; não há ajuste para clima, densidade, mobilidade, "
        "sorotipo, vigilância ou outros confundidores.\n\n"
        "## Resumo anual\n\n"
        f"{_to_markdown(summary)}\n\n"
        "## Maiores incidências em 2024\n\n"
        f"{_to_markdown(top_2024)}\n\n"
        "## Saneamento e incidência em 2023\n\n"
        f"{_to_markdown(associations)}\n\n"
        "A análise de saneamento usa somente a seção transversal SINISA 2023, "
        "que possui uma linha municipal por indicador. A série SNIS não foi "
        "agregada porque existem municípios com múltiplos prestadores.\n\n"
        f"Foram identificadas {len(duplicates)} chaves município–ano–indicador "
        "com múltiplos prestadores no SNIS; elas estão listadas separadamente.\n"
    )


def _to_markdown(table: pd.DataFrame) -> str:
    def format_value(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)

    header = "| " + " | ".join(map(str, table.columns)) + " |"
    separator = "| " + " | ".join("---" for _ in table.columns) + " |"
    rows = [
        "| " + " | ".join(format_value(value) for value in row) + " |"
        for row in table.itertuples(index=False, name=None)
    ]
    return "\n".join((header, separator, *rows))
