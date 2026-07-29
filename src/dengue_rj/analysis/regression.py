"""Regressões exploratórias com erros agrupados e diagnósticos."""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import chi2, t


@dataclass(frozen=True)
class RegressionOutputs:
    models_file: Path
    report_file: Path


def build_exploratory_regressions(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    table_directory: Path = Path("outputs/tables"),
    report_directory: Path = Path("outputs/reports"),
) -> RegressionOutputs:
    """Ajusta modelos brutos, temporais e com efeitos fixos municipais."""
    with duckdb.connect(str(database_path), read_only=True) as connection:
        panel = connection.execute(
            "SELECT * FROM painel_liraa_dengue_municipio"
        ).df()
    results = _fit_liraa_models(panel)
    table_directory.mkdir(parents=True, exist_ok=True)
    report_directory.mkdir(parents=True, exist_ok=True)
    models_file = table_directory / "regressoes_exploratorias_liraa_dengue.csv"
    report_file = report_directory / "regressoes_exploratorias_liraa_dengue.md"
    results.to_csv(models_file, index=False)
    report_file.write_text(_render_report(results), encoding="utf-8")
    return RegressionOutputs(models_file, report_file)


def _fit_liraa_models(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for indicator in ("iip_aedes_aegypti", "ib_aedes_aegypti"):
        for lag in range(4):
            outcome = f"incidencia_mes_{lag}_1_mil"
            columns = [
                "codigo_ibge_municipio",
                "ano",
                "mes",
                "data_referencia",
                indicator,
                outcome,
                "flag_outlier_ib_maior_100",
            ]
            valid = panel[columns].dropna().copy()
            outlier_rule = "nao_aplicavel"
            if indicator == "ib_aedes_aegypti":
                valid = valid[~valid["flag_outlier_ib_maior_100"]]
                outlier_rule = "exclui_ib_maior_100"
            valid["indicador_padronizado"] = (
                valid[indicator] - valid[indicator].mean()
            ) / valid[indicator].std(ddof=0)
            for transformation in ("original", "log1p"):
                y = valid[outcome].to_numpy(dtype=float)
                if transformation == "log1p":
                    y = np.log1p(y)
                for adjustment in ("bruto", "tempo", "municipio_rodada"):
                    design = _design_matrix(valid, adjustment)
                    model = _ols_clustered(
                        y,
                        design.to_numpy(dtype=float),
                        valid["codigo_ibge_municipio"].to_numpy(),
                        coefficient_position=1,
                    )
                    rows.append(
                        {
                            "indicador_liraa": indicator,
                            "defasagem_meses": lag,
                            "transformacao_desfecho": transformation,
                            "ajuste": adjustment,
                            "regra_outlier": outlier_rule,
                            "observacoes": len(valid),
                            "municipios": valid[
                                "codigo_ibge_municipio"
                            ].nunique(),
                            **model,
                            "interpretacao": (
                                "coeficiente_associativo_por_1_dp_do_indicador"
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def _design_matrix(table: pd.DataFrame, adjustment: str) -> pd.DataFrame:
    design = pd.DataFrame(
        {
            "intercepto": 1.0,
            "indicador_padronizado": table["indicador_padronizado"],
        },
        index=table.index,
    )
    if adjustment == "bruto":
        return design
    if adjustment == "tempo":
        categories = table[["ano", "mes"]].astype(str)
    elif adjustment == "municipio_rodada":
        categories = pd.DataFrame(
            {
                "municipio": table["codigo_ibge_municipio"].astype(str),
                "rodada": table["data_referencia"].astype(str),
            },
            index=table.index,
        )
    else:
        raise ValueError(f"Ajuste desconhecido: {adjustment}")
    dummies = pd.get_dummies(categories, drop_first=True, dtype=float)
    return pd.concat([design, dummies], axis=1)


def _ols_clustered(
    y: np.ndarray,
    x: np.ndarray,
    clusters: np.ndarray,
    coefficient_position: int,
) -> dict[str, float]:
    n, k = x.shape
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    fitted = x @ beta
    residuals = y - fitted
    bread = np.linalg.pinv(x.T @ x)
    unique_clusters = np.unique(clusters)
    meat = np.zeros((k, k))
    for cluster in unique_clusters:
        cluster_score = x[clusters == cluster].T @ residuals[clusters == cluster]
        meat += np.outer(cluster_score, cluster_score)
    cluster_count = len(unique_clusters)
    correction = (cluster_count / (cluster_count - 1)) * ((n - 1) / (n - k))
    covariance = correction * bread @ meat @ bread
    standard_error = float(np.sqrt(max(covariance[coefficient_position, coefficient_position], 0)))
    coefficient = float(beta[coefficient_position])
    statistic = coefficient / standard_error if standard_error else np.nan
    p_value = (
        float(2 * t.sf(abs(statistic), df=cluster_count - 1))
        if np.isfinite(statistic)
        else np.nan
    )
    total_sum = float(((y - y.mean()) ** 2).sum())
    residual_sum = float((residuals**2).sum())
    r_squared = 1 - residual_sum / total_sum if total_sum else np.nan
    bp_statistic, bp_p = _breusch_pagan(residuals, x)
    return {
        "coeficiente_indicador": coefficient,
        "erro_padrao_cluster_municipio": standard_error,
        "estatistica_t": statistic,
        "p_valor_cluster": p_value,
        "r_quadrado": r_squared,
        "breusch_pagan_lm": bp_statistic,
        "breusch_pagan_p": bp_p,
    }


def _breusch_pagan(residuals: np.ndarray, x: np.ndarray) -> tuple[float, float]:
    squared = residuals**2
    auxiliary = np.linalg.lstsq(x, squared, rcond=None)[0]
    fitted = x @ auxiliary
    total_sum = float(((squared - squared.mean()) ** 2).sum())
    residual_sum = float(((squared - fitted) ** 2).sum())
    r_squared = max(0.0, 1 - residual_sum / total_sum) if total_sum else 0.0
    statistic = len(squared) * r_squared
    degrees_freedom = max(1, x.shape[1] - 1)
    return statistic, float(chi2.sf(statistic, degrees_freedom))


def _render_report(results: pd.DataFrame) -> str:
    selected = results[
        (results["ajuste"] == "municipio_rodada")
        & (results["transformacao_desfecho"] == "log1p")
    ][
        [
            "indicador_liraa",
            "defasagem_meses",
            "observacoes",
            "coeficiente_indicador",
            "erro_padrao_cluster_municipio",
            "p_valor_cluster",
            "r_quadrado",
            "breusch_pagan_p",
        ]
    ]
    return (
        "# Regressões exploratórias LIRAa–dengue\n\n"
        "O coeficiente representa a associação com uma variação de um "
        "desvio-padrão no índice LIRAa. Os modelos principais usam "
        "`log1p(incidência)`, efeitos fixos de município e rodada e "
        "erro-padrão agrupado por município. Não constituem estimativa causal. "
        "Clima, intervenções, sorotipo e outros confundidores permanecem "
        "ausentes.\n\n"
        "## Modelos principais\n\n"
        f"{_to_markdown(selected)}\n"
    )


def _to_markdown(table: pd.DataFrame) -> str:
    def text(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)

    header = "| " + " | ".join(map(str, table.columns)) + " |"
    separator = "| " + " | ".join("---" for _ in table.columns) + " |"
    rows = [
        "| " + " | ".join(text(value) for value in row) + " |"
        for row in table.itertuples(index=False, name=None)
    ]
    return "\n".join((header, separator, *rows))
