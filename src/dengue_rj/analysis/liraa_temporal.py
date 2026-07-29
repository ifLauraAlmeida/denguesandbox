"""Painel exploratório entre LIRAa/LIA e dengue municipal."""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
from scipy.stats import pearsonr, spearmanr


@dataclass(frozen=True)
class LiraaTemporalOutputs:
    panel_file: Path
    associations_file: Path
    coverage_file: Path
    report_file: Path


def build_liraa_temporal_analysis(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    table_directory: Path = Path("outputs/tables"),
    report_directory: Path = Path("outputs/reports"),
) -> LiraaTemporalOutputs:
    """Cruza levantamentos com incidência mensal contemporânea e futura."""
    with duckdb.connect(str(database_path)) as connection:
        required = {
            "fact_liraa",
            "fact_demografia",
            "dim_municipio",
            "serie_dengue_municipio_mes",
        }
        available = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        missing = required.difference(available)
        if missing:
            raise ValueError(f"Tabelas necessárias ausentes: {sorted(missing)}")
        connection.execute(
            """
            CREATE OR REPLACE TABLE painel_liraa_dengue_municipio AS
            SELECT
                l.codigo_ibge_municipio,
                m.nome_municipio,
                l.ano,
                l.mes,
                l.data_referencia,
                l.status_levantamento,
                l.iip_aedes_aegypti,
                l.ib_aedes_aegypti,
                l.flag_outlier_ib_maior_100,
                d.populacao_residente,
                s0.casos_provaveis AS casos_mes_0,
                s1.casos_provaveis AS casos_mes_1,
                s2.casos_provaveis AS casos_mes_2,
                s3.casos_provaveis AS casos_mes_3,
                s0.casos_provaveis::DOUBLE
                    / d.populacao_residente * 1000 AS incidencia_mes_0_1_mil,
                s1.casos_provaveis::DOUBLE
                    / d.populacao_residente * 1000 AS incidencia_mes_1_1_mil,
                s2.casos_provaveis::DOUBLE
                    / d.populacao_residente * 1000 AS incidencia_mes_2_1_mil,
                s3.casos_provaveis::DOUBLE
                    / d.populacao_residente * 1000 AS incidencia_mes_3_1_mil,
                'ID_MN_RESI'::VARCHAR AS criterio_territorial_dengue,
                'DT_SIN_PRI'::VARCHAR AS eixo_temporal_dengue
            FROM fact_liraa l
            JOIN dim_municipio m USING (codigo_ibge_municipio)
            JOIN fact_demografia d
              ON d.codigo_ibge_municipio = l.codigo_ibge_municipio
             AND d.ano = l.ano
            LEFT JOIN serie_dengue_municipio_mes s0
              ON s0.codigo_ibge_municipio = l.codigo_ibge_municipio
             AND s0.mes = l.data_referencia
            LEFT JOIN serie_dengue_municipio_mes s1
              ON s1.codigo_ibge_municipio = l.codigo_ibge_municipio
             AND s1.mes = l.data_referencia + INTERVAL 1 MONTH
            LEFT JOIN serie_dengue_municipio_mes s2
              ON s2.codigo_ibge_municipio = l.codigo_ibge_municipio
             AND s2.mes = l.data_referencia + INTERVAL 2 MONTH
            LEFT JOIN serie_dengue_municipio_mes s3
              ON s3.codigo_ibge_municipio = l.codigo_ibge_municipio
             AND s3.mes = l.data_referencia + INTERVAL 3 MONTH
            ORDER BY l.data_referencia, l.codigo_ibge_municipio
            """
        )
        panel = connection.execute(
            "SELECT * FROM painel_liraa_dengue_municipio"
        ).df()
    if len(panel) != 1380:
        raise ValueError(f"Esperadas 1.380 linhas no painel LIRAa; recebidas {len(panel)}")
    associations = _calculate_liraa_associations(panel)
    coverage = (
        panel.groupby(["ano", "mes"], as_index=False)
        .agg(
            municipios=("codigo_ibge_municipio", "nunique"),
            municipios_com_iip=("iip_aedes_aegypti", "count"),
            municipios_com_ib=("ib_aedes_aegypti", "count"),
            outliers_ib_sinalizados=("flag_outlier_ib_maior_100", "sum"),
        )
        .sort_values(["ano", "mes"])
    )
    table_directory.mkdir(parents=True, exist_ok=True)
    report_directory.mkdir(parents=True, exist_ok=True)
    panel_file = table_directory / "painel_liraa_dengue_municipio_2020_2024.csv"
    associations_file = table_directory / "associacoes_liraa_dengue_2020_2024.csv"
    coverage_file = table_directory / "cobertura_painel_liraa_dengue_2020_2024.csv"
    report_file = report_directory / "analise_liraa_dengue.md"
    panel.to_csv(panel_file, index=False)
    associations.to_csv(associations_file, index=False)
    coverage.to_csv(coverage_file, index=False)
    report_file.write_text(
        _render_liraa_report(associations, coverage),
        encoding="utf-8",
    )
    return LiraaTemporalOutputs(
        panel_file,
        associations_file,
        coverage_file,
        report_file,
    )


def _calculate_liraa_associations(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for indicator in ("iip_aedes_aegypti", "ib_aedes_aegypti"):
        for lag in range(4):
            outcome = f"incidencia_mes_{lag}_1_mil"
            rules = (
                ("inclui_sinalizados", "exclui_ib_maior_100")
                if indicator == "ib_aedes_aegypti"
                else ("nao_aplicavel",)
            )
            for outlier_rule in rules:
                valid = panel[[indicator, outcome, "flag_outlier_ib_maior_100"]].dropna()
                if outlier_rule == "exclui_ib_maior_100":
                    valid = valid[~valid["flag_outlier_ib_maior_100"]]
                pearson = pearsonr(valid[indicator], valid[outcome])
                spearman = spearmanr(valid[indicator], valid[outcome])
                rows.append(
                    {
                        "indicador_liraa": indicator,
                        "defasagem_meses": lag,
                        "regra_outlier": outlier_rule,
                        "observacoes": len(valid),
                        "pearson_r": pearson.statistic,
                        "pearson_p": pearson.pvalue,
                        "spearman_rho": spearman.statistic,
                        "spearman_p": spearman.pvalue,
                        "interpretacao": "associacao_temporal_exploratoria_nao_causal",
                    }
                )
    return pd.DataFrame(rows)


def _render_liraa_report(
    associations: pd.DataFrame, coverage: pd.DataFrame
) -> str:
    primary = associations[
        associations["regra_outlier"].isin(
            ["nao_aplicavel", "exclui_ib_maior_100"]
        )
    ]
    return (
        "# Análise exploratória LIRAa/LIA e dengue\n\n"
        "Painel municipal dos 15 levantamentos de 2020–2024. A incidência usa "
        "casos por residência e primeiros sintomas no mês do levantamento e "
        "nos três meses seguintes. As associações são descritivas, não causais "
        "e não controlam sazonalidade, clima, intervenções ou outros "
        "confundidores.\n\n"
        "## Associações com regra conservadora de outlier\n\n"
        f"{_to_markdown(primary)}\n\n"
        "## Cobertura\n\n"
        f"{_to_markdown(coverage)}\n"
    )


def _to_markdown(table: pd.DataFrame) -> str:
    def value_text(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)

    header = "| " + " | ".join(map(str, table.columns)) + " |"
    separator = "| " + " | ".join("---" for _ in table.columns) + " |"
    rows = [
        "| " + " | ".join(value_text(value) for value in row) + " |"
        for row in table.itertuples(index=False, name=None)
    ]
    return "\n".join((header, separator, *rows))
