"""Mapas coropléticos municipais sem dependência de GeoPandas."""

import json
from pathlib import Path

import matplotlib
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Polygon

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def build_spatial_maps(
    local_table: pd.DataFrame,
    geojson_file: Path = Path("data/processed/territorio/rj_municipios_2024.geojson"),
    output_directory: Path = Path("outputs/figures/espacial"),
) -> tuple[Path, ...]:
    """Gera mapas anuais de incidência e clusters Moran locais."""
    geojson = json.loads(geojson_file.read_text(encoding="utf-8"))
    geometries = {
        feature["properties"]["CD_MUN"]: feature["geometry"]
        for feature in geojson["features"]
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    incidence_max = local_table["incidencia_100_mil"].quantile(0.99)
    for year, frame in local_table.groupby("ano", sort=True):
        values = frame.set_index("codigo_ibge_municipio")
        incidence_file = output_directory / f"incidencia_dengue_{year}.png"
        cluster_file = output_directory / f"moran_local_clusters_{year}.png"
        _plot_incidence(geometries, values, int(year), incidence_max, incidence_file)
        _plot_clusters(geometries, values, int(year), cluster_file)
        outputs.extend((incidence_file, cluster_file))
    return tuple(outputs)


def _polygon_patches(geometry: dict[str, object]) -> list[Polygon]:
    coordinates = geometry["coordinates"]
    polygons = [coordinates] if geometry["type"] == "Polygon" else coordinates
    return [
        Polygon(exterior[0], closed=True)
        for exterior in polygons
        if exterior and exterior[0]
    ]


def _base_axes(title: str) -> tuple[plt.Figure, plt.Axes]:
    figure, axes = plt.subplots(figsize=(8, 8))
    axes.set_title(title, fontsize=13)
    axes.set_aspect("equal")
    axes.axis("off")
    return figure, axes


def _plot_incidence(
    geometries: dict[str, dict[str, object]],
    values: pd.DataFrame,
    year: int,
    incidence_max: float,
    output_file: Path,
) -> None:
    figure, axes = _base_axes(f"Incidência de dengue por 100 mil habitantes — {year}")
    patches, colors = [], []
    for code, geometry in geometries.items():
        parts = _polygon_patches(geometry)
        patches.extend(parts)
        colors.extend([min(values.loc[code, "incidencia_100_mil"], incidence_max)] * len(parts))
    collection = PatchCollection(
        patches,
        cmap="viridis",
        edgecolor="white",
        linewidth=0.25,
    )
    collection.set_array(colors)
    collection.set_clim(0, incidence_max)
    axes.add_collection(collection)
    axes.autoscale_view()
    colorbar = figure.colorbar(collection, ax=axes, shrink=0.7)
    colorbar.set_label("Casos prováveis por 100 mil")
    figure.text(0.5, 0.03, "Fonte: SINAN por município de residência; população RIPSA/SES-RJ", ha="center")
    figure.savefig(output_file, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _plot_clusters(
    geometries: dict[str, dict[str, object]],
    values: pd.DataFrame,
    year: int,
    output_file: Path,
) -> None:
    labels = ["não significativo", "alto-alto", "baixo-baixo", "alto-baixo", "baixo-alto"]
    colors = ["#dedede", "#b2182b", "#2166ac", "#ef8a62", "#67a9cf"]
    lookup = {label: index for index, label in enumerate(labels)}
    figure, axes = _base_axes(f"Clusters locais de Moran da incidência — {year}")
    patches, categories = [], []
    for code, geometry in geometries.items():
        parts = _polygon_patches(geometry)
        patches.extend(parts)
        categories.extend([lookup[values.loc[code, "cluster_005"]]] * len(parts))
    cmap = ListedColormap(colors)
    collection = PatchCollection(
        patches,
        cmap=cmap,
        norm=BoundaryNorm(range(len(labels) + 1), cmap.N),
        edgecolor="white",
        linewidth=0.25,
    )
    collection.set_array(categories)
    axes.add_collection(collection)
    axes.autoscale_view()
    handles = [
        Polygon([[0, 0]], facecolor=color, edgecolor="none", label=label)
        for label, color in zip(labels, colors)
    ]
    axes.legend(handles=handles, loc="lower right", frameon=False, fontsize=8)
    figure.text(
        0.5,
        0.03,
        "Pesos rainha; p bilateral < 0,05; resultado exploratório",
        ha="center",
    )
    figure.savefig(output_file, dpi=180, bbox_inches="tight")
    plt.close(figure)
