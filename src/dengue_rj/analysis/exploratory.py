"""Análise descritiva municipal de dengue e saneamento."""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class ExploratoryOutputs:
    incidence_summary: Path
    incidence_extremes: Path
    sanitation_cross_section: Path
    sanitation_associations: Path
    association_sensitivity: Path
    provider_duplicates: Path
    report: Path
    scatter_figures: tuple[Path, ...]


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
              AND ano = 2024
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
    sensitivity = _association_sensitivity(cross_section)

    table_directory.mkdir(parents=True, exist_ok=True)
    report_directory.mkdir(parents=True, exist_ok=True)
    incidence_summary = table_directory / "resumo_incidencia_municipal_2020_2024.csv"
    incidence_extremes = table_directory / "extremos_incidencia_municipal_2020_2024.csv"
    sanitation_cross_section = table_directory / "dengue_saneamento_2024.csv"
    sanitation_associations = table_directory / "associacoes_dengue_saneamento_2024.csv"
    association_sensitivity = (
        table_directory / "sensibilidade_associacoes_dengue_saneamento_2024.csv"
    )
    provider_duplicates = table_directory / "duplicidades_prestador_saneamento.csv"
    report = report_directory / "analise_exploratoria.md"
    summary.to_csv(incidence_summary, index=False)
    extremes.to_csv(incidence_extremes, index=False)
    cross_section.to_csv(sanitation_cross_section, index=False)
    associations.to_csv(sanitation_associations, index=False)
    sensitivity.to_csv(association_sensitivity, index=False)
    duplicates.to_csv(provider_duplicates, index=False)
    scatter_figures = _plot_sanitation_scatter(cross_section)
    report.write_text(
        _render_report(summary, extremes, associations, sensitivity, duplicates),
        encoding="utf-8",
    )
    return ExploratoryOutputs(
        incidence_summary,
        incidence_extremes,
        sanitation_cross_section,
        sanitation_associations,
        association_sensitivity,
        provider_duplicates,
        report,
        scatter_figures,
    )


def _incidence_summary(incidence: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, group in incidence.groupby("ano", sort=True):
        values = group["incidencia_1_mil"]
        rows.append(
            {
                "ano": year,
                "municipios": len(group),
                "casos_provaveis": group["casos_provaveis"].sum(),
                "populacao": group["populacao_residente"].sum(),
                "incidencia_agregada_1_mil": (
                    group["casos_provaveis"].sum()
                    / group["populacao_residente"].sum()
                    * 1_000
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
            ["incidencia_1_mil", "codigo_ibge_municipio"],
            ascending=[False, True],
        )
        top = ordered.head(10).copy()
        top.insert(0, "extremo", "maior")
        top.insert(1, "posicao", range(1, len(top) + 1))
        bottom = ordered.sort_values(
            ["incidencia_1_mil", "codigo_ibge_municipio"]
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
    annual = incidence[incidence["ano"].eq(2024)].copy()
    return annual.merge(values, on="codigo_ibge_municipio", how="left")


def _sanitation_associations(cross_section: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in ("atendimento_agua_percentual", "atendimento_esgoto_percentual"):
        valid = cross_section[["incidencia_1_mil", column]].dropna()
        pearson = pearsonr(valid[column], valid["incidencia_1_mil"])
        spearman = spearmanr(valid[column], valid["incidencia_1_mil"])
        rows.append(
            {
                "ano": 2024,
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


def _association_sensitivity(cross_section: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in ("atendimento_agua_percentual", "atendimento_esgoto_percentual"):
        valid = cross_section[
            [
                "codigo_ibge_municipio",
                "nome_municipio",
                "incidencia_1_mil",
                column,
            ]
        ].dropna()
        base_pearson = pearsonr(valid[column], valid["incidencia_1_mil"]).statistic
        base_spearman = spearmanr(valid[column], valid["incidencia_1_mil"]).statistic
        for index, municipality in valid.iterrows():
            reduced = valid.drop(index)
            pearson_value = pearsonr(
                reduced[column], reduced["incidencia_1_mil"]
            ).statistic
            spearman_value = spearmanr(
                reduced[column], reduced["incidencia_1_mil"]
            ).statistic
            rows.append(
                {
                    "ano": 2024,
                    "indicador_saneamento": column,
                    "codigo_ibge_municipio_removido": municipality[
                        "codigo_ibge_municipio"
                    ],
                    "nome_municipio_removido": municipality["nome_municipio"],
                    "pearson_base": base_pearson,
                    "pearson_sem_municipio": pearson_value,
                    "delta_pearson": pearson_value - base_pearson,
                    "spearman_base": base_spearman,
                    "spearman_sem_municipio": spearman_value,
                    "delta_spearman": spearman_value - base_spearman,
                }
            )
    result = pd.DataFrame(rows)
    result["influencia_maxima_absoluta"] = result[
        ["delta_pearson", "delta_spearman"]
    ].abs().max(axis=1)
    return result.sort_values(
        ["indicador_saneamento", "influencia_maxima_absoluta"],
        ascending=[True, False],
    ).reset_index(drop=True)


def _plot_sanitation_scatter(
    cross_section: pd.DataFrame,
    output_directory: Path = Path("outputs/figures"),
) -> tuple[Path, ...]:
    output_directory.mkdir(parents=True, exist_ok=True)
    figures = []
    labels = {
        "atendimento_agua_percentual": "Atendimento de água (%)",
        "atendimento_esgoto_percentual": "Atendimento de esgoto (%)",
    }
    for column, x_label in labels.items():
        valid = cross_section[
            ["nome_municipio", "incidencia_1_mil", column]
        ].dropna()
        coefficients = np.polyfit(valid[column], valid["incidencia_1_mil"], 1)
        fitted = np.polyval(coefficients, valid[column])
        residuals = valid["incidencia_1_mil"] - fitted
        influential = residuals.abs().nlargest(5).index
        figure, axis = plt.subplots(figsize=(9, 6))
        axis.scatter(
            valid[column],
            valid["incidencia_1_mil"],
            alpha=0.75,
            edgecolor="white",
            linewidth=0.5,
        )
        order = np.argsort(valid[column].to_numpy())
        axis.plot(
            valid[column].to_numpy()[order],
            fitted[order],
            color="#b22222",
            linewidth=1.5,
            label="Ajuste linear descritivo",
        )
        for index in influential:
            row = valid.loc[index]
            axis.annotate(
                row["nome_municipio"],
                (row[column], row["incidencia_1_mil"]),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=7,
            )
        axis.set(
            xlabel=x_label,
            ylabel="Incidência de dengue por 1.000 habitantes",
            title=f"Incidência de dengue × {x_label.lower()} — 2024",
        )
        axis.legend()
        axis.grid(alpha=0.2)
        figure.tight_layout()
        path = output_directory / f"dispersao_dengue_{column}_2024.png"
        figure.savefig(path, dpi=160)
        plt.close(figure)
        figures.append(path)
    return tuple(figures)


def _render_report(
    summary: pd.DataFrame,
    extremes: pd.DataFrame,
    associations: pd.DataFrame,
    sensitivity: pd.DataFrame,
    duplicates: pd.DataFrame,
) -> str:
    top_2024 = extremes[
        (extremes["ano"].eq(2024)) & (extremes["extremo"].eq("maior"))
    ][["posicao", "nome_municipio", "incidencia_1_mil"]]
    influential = sensitivity.groupby("indicador_saneamento", sort=False).head(5)[
        [
            "indicador_saneamento",
            "nome_municipio_removido",
            "delta_pearson",
            "delta_spearman",
        ]
    ]
    return (
        "# Análise exploratória municipal\n\n"
        "Resultados descritivos e associações exploratórias. Correlação não "
        "implica causalidade; não há ajuste para clima, densidade, mobilidade, "
        "sorotipo, vigilância ou outros confundidores.\n\n"
        "## Resumo anual\n\n"
        f"{_to_markdown(summary)}\n\n"
        "## Maiores incidências em 2024\n\n"
        f"{_to_markdown(top_2024)}\n\n"
        "## Saneamento e incidência em 2024\n\n"
        f"{_to_markdown(associations)}\n\n"
        "## Sensibilidade à retirada de um município\n\n"
        f"{_to_markdown(influential)}\n\n"
        "A análise de saneamento usa somente a seção transversal SINISA 2024, "
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
