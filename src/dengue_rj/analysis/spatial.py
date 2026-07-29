"""Autocorrelação espacial da incidência municipal de dengue."""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from dengue_rj.visualization.spatial_maps import build_spatial_maps


@dataclass(frozen=True)
class SpatialAnalysisOutputs:
    global_file: Path
    local_file: Path
    sensitivity_file: Path
    report_file: Path


def build_spatial_analysis(
    database_path: Path = Path("database/dengue_rj.duckdb"),
    neighbors_file: Path = Path("data/processed/territorio/vizinhanca_rainha_rj_2024.csv"),
    rook_neighbors_file: Path = Path("data/processed/territorio/vizinhanca_torre_rj_2024.csv"),
    knn_neighbors_file: Path = Path("data/processed/territorio/vizinhanca_knn4_rj_2024.csv"),
    table_directory: Path = Path("outputs/tables"),
    report_directory: Path = Path("outputs/reports"),
    permutations: int = 999,
    seed: int = 20240729,
) -> SpatialAnalysisOutputs:
    """Calcula Moran global e local anual com pesos rainha normalizados."""
    with duckdb.connect(str(database_path), read_only=True) as connection:
        incidence = connection.execute(
            """
            SELECT codigo_ibge_municipio, nome_municipio, ano, incidencia_1_mil
            FROM indicador_dengue_municipio_ano
            WHERE ano BETWEEN 2020 AND 2024
            """
        ).df()
    neighbors = pd.read_csv(
        neighbors_file,
        dtype={"codigo_ibge_municipio": str, "codigo_ibge_vizinho": str},
    )
    codes = sorted(neighbors["codigo_ibge_municipio"].unique())
    weights = _weight_matrix(neighbors, codes)
    rng = np.random.default_rng(seed)
    global_rows, local_parts = [], []
    for year, frame in incidence.groupby("ano", sort=True):
        ordered = frame.set_index("codigo_ibge_municipio").reindex(codes)
        if ordered["incidencia_1_mil"].isna().any():
            raise ValueError(f"Incidência incompleta para a análise espacial de {year}")
        values = ordered["incidencia_1_mil"].to_numpy(float)
        observed, simulations = moran_global(values, weights, permutations, rng)
        p_value = (np.count_nonzero(np.abs(simulations) >= abs(observed)) + 1) / (
            permutations + 1
        )
        global_rows.append(
            {
                "ano": int(year),
                "municipios": len(codes),
                "moran_i": observed,
                "esperanca_aleatoria": -1 / (len(codes) - 1),
                "p_permutacao_bilateral": p_value,
                "permutacoes": permutations,
                "regra_vizinhanca": "contiguidade_rainha",
                "semente": seed,
            }
        )
        local = moran_local(values, weights, permutations, rng)
        local.insert(0, "codigo_ibge_municipio", codes)
        local.insert(1, "nome_municipio", ordered["nome_municipio"].to_numpy())
        local.insert(2, "ano", int(year))
        local_parts.append(local)

    global_table = pd.DataFrame(global_rows)
    local_table = pd.concat(local_parts, ignore_index=True)
    sensitivity_table = _spatial_sensitivity(
        incidence,
        {
            "contiguidade_rainha": neighbors_file,
            "contiguidade_torre": rook_neighbors_file,
            "k_vizinhos_4": knn_neighbors_file,
        },
        permutations,
        seed,
    )
    table_directory.mkdir(parents=True, exist_ok=True)
    report_directory.mkdir(parents=True, exist_ok=True)
    global_file = table_directory / "moran_global_incidencia_2020_2024.csv"
    local_file = table_directory / "moran_local_incidencia_2020_2024.csv"
    sensitivity_file = table_directory / "sensibilidade_pesos_moran_2020_2024.csv"
    report_file = report_directory / "analise_espacial.md"
    global_table.to_csv(global_file, index=False)
    local_table.to_csv(local_file, index=False)
    sensitivity_table.to_csv(sensitivity_file, index=False)
    build_spatial_maps(local_table)
    report_file.write_text(
        _report(global_table, local_table, sensitivity_table),
        encoding="utf-8",
    )
    return SpatialAnalysisOutputs(global_file, local_file, sensitivity_file, report_file)


def _spatial_sensitivity(
    incidence: pd.DataFrame,
    configurations: dict[str, Path],
    permutations: int,
    seed: int,
) -> pd.DataFrame:
    rows = []
    for rule, file in configurations.items():
        neighbors = pd.read_csv(
            file,
            dtype={"codigo_ibge_municipio": str, "codigo_ibge_vizinho": str},
        )
        codes = sorted(neighbors["codigo_ibge_municipio"].unique())
        weights = _weight_matrix(neighbors, codes)
        for year, frame in incidence.groupby("ano", sort=True):
            ordered = frame.set_index("codigo_ibge_municipio").reindex(codes)
            values = ordered["incidencia_1_mil"].to_numpy(float)
            rng = np.random.default_rng(seed + int(year))
            observed, simulations = moran_global(values, weights, permutations, rng)
            p_value = (
                np.count_nonzero(np.abs(simulations) >= abs(observed)) + 1
            ) / (permutations + 1)
            rows.append(
                {
                    "ano": int(year),
                    "regra_vizinhanca": rule,
                    "moran_i": observed,
                    "p_permutacao_bilateral": p_value,
                    "permutacoes": permutations,
                    "semente": seed + int(year),
                }
            )
    return pd.DataFrame(rows)


def _weight_matrix(neighbors: pd.DataFrame, codes: list[str]) -> np.ndarray:
    positions = {code: index for index, code in enumerate(codes)}
    weights = np.zeros((len(codes), len(codes)))
    for row in neighbors.itertuples():
        weights[
            positions[row.codigo_ibge_municipio],
            positions[row.codigo_ibge_vizinho],
        ] = float(row.peso_normalizado_linha)
    if not np.allclose(weights.sum(axis=1), 1):
        raise ValueError("Matriz espacial não está normalizada por linha")
    return weights


def moran_global(
    values: np.ndarray,
    weights: np.ndarray,
    permutations: int,
    rng: np.random.Generator,
) -> tuple[float, np.ndarray]:
    centered = values - values.mean()
    denominator = centered @ centered
    if denominator == 0:
        raise ValueError("Moran I é indefinido para valores constantes")
    factor = len(values) / weights.sum()
    observed = factor * (centered @ weights @ centered) / denominator
    simulations = np.empty(permutations)
    for index in range(permutations):
        permuted = rng.permutation(centered)
        simulations[index] = factor * (permuted @ weights @ permuted) / denominator
    return float(observed), simulations


def moran_local(
    values: np.ndarray,
    weights: np.ndarray,
    permutations: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    centered = values - values.mean()
    variance = np.mean(centered**2)
    if variance == 0:
        raise ValueError("Moran local é indefinido para valores constantes")
    lag = weights @ centered
    observed = centered * lag / variance
    simulated = np.empty((permutations, len(values)))
    for index in range(permutations):
        permuted = rng.permutation(centered)
        simulated[index] = permuted * (weights @ permuted) / variance
    p_values = (np.sum(np.abs(simulated) >= np.abs(observed), axis=0) + 1) / (
        permutations + 1
    )
    quadrant = np.select(
        [
            (centered > 0) & (lag > 0),
            (centered < 0) & (lag < 0),
            (centered > 0) & (lag < 0),
            (centered < 0) & (lag > 0),
        ],
        ["alto-alto", "baixo-baixo", "alto-baixo", "baixo-alto"],
        default="indefinido",
    )
    cluster = np.where(p_values < 0.05, quadrant, "não significativo")
    return pd.DataFrame(
        {
            "incidencia_1_mil": values,
            "valor_centrado": centered,
            "lag_espacial_centrado": lag,
            "moran_local_i": observed,
            "p_permutacao_bilateral": p_values,
            "cluster_005": cluster,
            "permutacoes": permutations,
            "regra_vizinhanca": "contiguidade_rainha",
        }
    )


def _report(
    global_table: pd.DataFrame,
    local_table: pd.DataFrame,
    sensitivity_table: pd.DataFrame,
) -> str:
    lines = [
        "# Autocorrelação espacial da incidência de dengue",
        "",
        (
            "Análise exploratória municipal com malha IBGE 2024 e pesos de contiguidade "
            "rainha normalizados por linha. Os testes usam 999 permutações bilaterais "
            "e semente fixa; associação espacial não implica causalidade."
        ),
        "",
        "| Ano | Moran I | p bilateral | Clusters locais (p < 0,05) |",
        "|---:|---:|---:|---:|",
    ]
    for row in global_table.itertuples():
        significant = (
            (local_table["ano"] == row.ano)
            & (local_table["cluster_005"] != "não significativo")
        ).sum()
        lines.append(
            f"| {row.ano} | {row.moran_i:.4f} | "
            f"{row.p_permutacao_bilateral:.3f} | {significant} |"
        )
    lines.extend(
        [
            "",
            "## Sensibilidade à matriz de pesos",
            "",
            "| Ano | Rainha | Torre | 4 vizinhos mais próximos |",
            "|---:|---:|---:|---:|",
        ]
    )
    pivot = sensitivity_table.pivot(
        index="ano", columns="regra_vizinhanca", values="moran_i"
    )
    for year, row in pivot.iterrows():
        lines.append(
            f"| {year} | {row['contiguidade_rainha']:.4f} | "
            f"{row['contiguidade_torre']:.4f} | {row['k_vizinhos_4']:.4f} |"
        )
    lines.extend(
        [
            "",
            (
                "Os resultados dependem da definição da vizinhança e não controlam clima, "
                "mobilidade, sorotipo, vigilância nem subnotificação. Os clusters locais "
                "são diagnósticos exploratórios e requerem sensibilidade a outros pesos."
            ),
        ]
    )
    return "\n".join(lines) + "\n"
