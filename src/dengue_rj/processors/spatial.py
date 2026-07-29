"""Processamento da malha municipal e vizinhança por contiguidade."""

import json
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import shapefile
from shapely.geometry import mapping, shape


@dataclass(frozen=True)
class SpatialProcessing:
    geojson_file: Path
    neighbors_file: Path
    municipalities: int
    directed_edges: int


def process_spatial_mesh(
    archive_file: Path = Path("data/raw/territorio/RJ_Municipios_2024.zip"),
    dimension_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
    output_directory: Path = Path("data/processed/territorio"),
) -> SpatialProcessing:
    """Valida a malha e cria pesos rainha normalizados por linha."""
    dimension = pd.read_csv(dimension_file, dtype=str)
    official_codes = set(dimension["codigo_ibge_municipio"])
    records, geometries = _read_shapefile(archive_file)
    codes = [record["CD_MUN"] for record in records]
    if len(codes) != 92 or set(codes) != official_codes:
        raise ValueError("Malha municipal não reconcilia exatamente os 92 códigos oficiais")
    if any(not geometry.is_valid for geometry in geometries):
        raise ValueError("Malha municipal contém geometria inválida")

    neighbor_sets = {code: set() for code in codes}
    contact_types = {}
    for left in range(len(codes)):
        for right in range(left + 1, len(codes)):
            boundary_contact = geometries[left].boundary.intersection(
                geometries[right].boundary
            )
            if boundary_contact.is_empty:
                continue
            code_left, code_right = codes[left], codes[right]
            neighbor_sets[code_left].add(code_right)
            neighbor_sets[code_right].add(code_left)
            contact_types[frozenset((code_left, code_right))] = (
                "rook" if boundary_contact.length > 1e-10 else "queen_point"
            )
    if any(not neighbors for neighbors in neighbor_sets.values()):
        isolated = [code for code, neighbors in neighbor_sets.items() if not neighbors]
        raise ValueError(f"Municípios isolados na contiguidade rainha: {isolated}")

    rows = []
    for code, neighbors in neighbor_sets.items():
        for neighbor in sorted(neighbors):
            rows.append(
                {
                    "codigo_ibge_municipio": code,
                    "codigo_ibge_vizinho": neighbor,
                    "tipo_contato": contact_types[frozenset((code, neighbor))],
                    "peso_binario": 1,
                    "peso_normalizado_linha": 1 / len(neighbors),
                    "numero_vizinhos": len(neighbors),
                    "regra_vizinhanca": "contiguidade_rainha",
                    "ano_malha": 2024,
                }
            )
    neighbors = pd.DataFrame(rows)
    _validate_neighbors(neighbors, official_codes)

    features = []
    for record, geometry in zip(records, geometries):
        features.append(
            {
                "type": "Feature",
                "properties": record,
                "geometry": mapping(geometry),
            }
        )
    geojson = {
        "type": "FeatureCollection",
        "name": "RJ_Municipios_2024",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    geojson_file = output_directory / "rj_municipios_2024.geojson"
    neighbors_file = output_directory / "vizinhanca_rainha_rj_2024.csv"
    geojson_file.write_text(
        json.dumps(geojson, ensure_ascii=False),
        encoding="utf-8",
    )
    neighbors.to_csv(neighbors_file, index=False)
    return SpatialProcessing(
        geojson_file,
        neighbors_file,
        len(features),
        len(neighbors),
    )


def _read_shapefile(
    archive_file: Path,
) -> tuple[list[dict[str, object]], list[object]]:
    with ZipFile(archive_file) as archive:
        shp_name = next(name for name in archive.namelist() if name.endswith(".shp"))
        stem = shp_name[:-4]
        cpg_name = stem + ".cpg"
        encoding = (
            f"cp{archive.read(cpg_name).decode('ascii').strip()}"
            if cpg_name in archive.namelist()
            else "utf-8"
        )
        reader = shapefile.Reader(
            shp=archive.open(stem + ".shp"),
            shx=archive.open(stem + ".shx"),
            dbf=archive.open(stem + ".dbf"),
            encoding=encoding,
        )
        records = [record.as_dict() for record in reader.records()]
        geometries = [shape(item.__geo_interface__) for item in reader.shapes()]
    return records, geometries


def _validate_neighbors(neighbors: pd.DataFrame, official_codes: set[str]) -> None:
    if set(neighbors["codigo_ibge_municipio"]) != official_codes:
        raise ValueError("Vizinhança não cobre todos os municípios")
    reverse = set(
        zip(neighbors["codigo_ibge_vizinho"], neighbors["codigo_ibge_municipio"])
    )
    forward = set(
        zip(neighbors["codigo_ibge_municipio"], neighbors["codigo_ibge_vizinho"])
    )
    if forward != reverse:
        raise ValueError("Vizinhança de contiguidade não é simétrica")
    sums = neighbors.groupby("codigo_ibge_municipio")[
        "peso_normalizado_linha"
    ].sum()
    if not sums.between(1 - 1e-10, 1 + 1e-10).all():
        raise ValueError("Pesos espaciais não somam um por município")
