"""Inventário dos indicadores originais de saneamento do SNIS e SINISA."""

import re
import subprocess
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from dengue_rj.processors.sanitation_harmonization import PRIORITY_COMPARISONS

INDICATOR_PATTERN = re.compile(r"I[A-Z]{2}\d{4}|IN\d{3}")


def build_sanitation_indicator_inventory(
    processed_directory: Path = Path("data/processed/saneamento"),
    sinisa_directory: Path = Path("data/raw/saneamento/sinisa"),
    output_file: Path = Path(
        "data/processed/saneamento/dim_indicador_saneamento_original.csv"
    ),
) -> Path:
    """Consolida metadados originais sem presumir equivalência entre sistemas."""
    frames = [
        _inventory_snis_water_sewer(
            processed_directory / "snis_agua_esgoto_indicadores_2020_2022.csv"
        ),
        _inventory_snis_long(
            processed_directory
            / "snis_residuos_solidos_indicadores_rj_2020_2022.csv",
            "residuos_solidos",
        ),
        _inventory_snis_long(
            processed_directory
            / "snis_aguas_pluviais_indicadores_rj_2020_2022.csv",
            "aguas_pluviais",
        ),
        _inventory_sinisa_water_sewer(
            _latest(sinisa_directory, "*abastecimento_agua*ref2023*.zip"),
            "abastecimento_agua",
        ),
        _inventory_sinisa_water_sewer(
            _latest(sinisa_directory, "*esgotamento_sanitario*ref2023*.zip"),
            "esgotamento_sanitario",
        ),
        _inventory_sinisa_stormwater(
            _latest(sinisa_directory, "*aguas_pluviais*ref2023*.rar")
        ),
        _inventory_sinisa_solid_waste(
            _latest(sinisa_directory, "*residuos_solidos*ref2023*.rar")
        ),
    ]
    result = pd.concat(frames, ignore_index=True).fillna("")
    key = ["sistema", "componente", "codigo_indicador_original"]
    result = result.drop_duplicates().sort_values(
        key + ["ano_referencia_inicial"], kind="stable"
    )
    result["versao_metadado_origem"] = (
        result.groupby(key).cumcount().add(1).map(lambda value: f"v{value:02d}")
    )
    result = result.reset_index(drop=True)
    result.insert(
        0,
        "id_indicador_origem",
        result["sistema"]
        + ":"
        + result["componente"]
        + ":"
        + result["codigo_indicador_original"]
        + ":"
        + result["versao_metadado_origem"],
    )
    result["codigo_indicador_padronizado"] = ""
    water_sewer = result["componente"].isin(
        ["abastecimento_agua", "esgotamento_sanitario"]
    )
    result["status_harmonizacao"] = "de_para_indicadores_nao_localizado"
    result.loc[
        water_sewer, "status_harmonizacao"
    ] = "de_para_informacoes_disponivel_indicadores_pendentes"
    for comparison in PRIORITY_COMPARISONS:
        selected = (
            result["sistema"].eq("SNIS")
            & result["componente"].eq(comparison["componente"])
            & result["codigo_indicador_original"].eq(comparison["codigo_snis"])
        )
        result.loc[selected, "codigo_indicador_padronizado"] = comparison[
            "codigo_sinisa"
        ]
        result.loc[selected, "status_harmonizacao"] = comparison[
            "classificacao_comparabilidade"
        ]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)
    return output_file


def _inventory_snis_water_sewer(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path, dtype=str)
    metadata = (
        source[["codigo_indicador", "nome_indicador", "unidade"]]
        .drop_duplicates()
        .copy()
    )
    sewer_codes = {"IN015", "IN016", "IN046", "IN056"}
    metadata["componente"] = metadata["codigo_indicador"].map(
        lambda value: (
            "esgotamento_sanitario"
            if value in sewer_codes
            else "abastecimento_agua"
        )
    )
    return _standardize_inventory(metadata, "SNIS", 2020, 2022)


def _inventory_snis_long(path: Path, component: str) -> pd.DataFrame:
    source = pd.read_csv(path, dtype=str)
    columns = ["codigo_indicador", "nome_indicador", "unidade"]
    optional = [column for column in ("familia_indicador", "formula") if column in source]
    grouping = columns + optional
    metadata = (
        source[grouping + ["ano"]]
        .drop_duplicates()
        .groupby(grouping, dropna=False, as_index=False)
        .agg(
            ano_referencia_inicial=("ano", "min"),
            ano_referencia_final=("ano", "max"),
        )
    )
    metadata["componente"] = component
    return _standardize_inventory(metadata, "SNIS", 2020, 2022)


def _inventory_sinisa_water_sewer(path: Path, component: str) -> pd.DataFrame:
    frames = []
    with ZipFile(path) as archive:
        member = next(
            name
            for name in archive.namelist()
            if "Indicadores_Base Municipal" in name
        )
        workbook = pd.ExcelFile(BytesIO(archive.read(member)))
        for sheet in workbook.sheet_names:
            if "nota" in sheet.casefold():
                continue
            source = pd.read_excel(workbook, sheet_name=sheet, header=None, nrows=11)
            for column in range(source.shape[1]):
                code = _text(source.iat[9, column])
                if not INDICATOR_PATTERN.fullmatch(code):
                    continue
                frames.append(
                    {
                        "codigo_indicador": code,
                        "nome_indicador": _text(source.iat[7, column]),
                        "unidade": _text(source.iat[8, column]),
                        "familia_indicador": sheet,
                        "formula": "",
                        "componente": component,
                    }
                )
    return _standardize_inventory(pd.DataFrame(frames), "SINISA", 2023, 2023)


def _inventory_sinisa_stormwater(path: Path) -> pd.DataFrame:
    member, content = _read_rar_indicator(path)
    source = pd.read_excel(BytesIO(content), sheet_name=0, header=None, nrows=11)
    families = source.iloc[6].ffill()
    frames = []
    for column in range(source.shape[1]):
        code = _text(source.iat[10, column])
        if not INDICATOR_PATTERN.fullmatch(code):
            continue
        frames.append(
            {
                "codigo_indicador": code,
                "nome_indicador": _text(source.iat[7, column]),
                "unidade": _text(source.iat[9, column]),
                "familia_indicador": _text(families.iloc[column]),
                "formula": _text(source.iat[8, column]),
                "componente": "aguas_pluviais",
                "arquivo_origem": member,
            }
        )
    return _standardize_inventory(pd.DataFrame(frames), "SINISA", 2023, 2023)


def _inventory_sinisa_solid_waste(path: Path) -> pd.DataFrame:
    member, content = _read_rar_indicator(path)
    source = pd.read_excel(BytesIO(content), sheet_name=0, header=None, nrows=13)
    families = source.iloc[9].ffill()
    frames = []
    for column in range(source.shape[1]):
        code = _text(source.iat[10, column])
        if not INDICATOR_PATTERN.fullmatch(code):
            continue
        frames.append(
            {
                "codigo_indicador": code,
                "nome_indicador": _text(source.iat[11, column]),
                "unidade": _text(source.iat[12, column]),
                "familia_indicador": _text(families.iloc[column]),
                "formula": "",
                "componente": "residuos_solidos",
                "arquivo_origem": member,
            }
        )
    return _standardize_inventory(pd.DataFrame(frames), "SINISA", 2023, 2023)


def _standardize_inventory(
    source: pd.DataFrame, system: str, first_year: int, last_year: int
) -> pd.DataFrame:
    result = source.rename(
        columns={
            "codigo_indicador": "codigo_indicador_original",
            "nome_indicador": "nome_indicador_original",
            "unidade": "unidade_original",
            "familia_indicador": "familia_original",
            "formula": "formula_original",
        }
    )
    for column in ("familia_original", "formula_original"):
        if column not in result:
            result[column] = ""
    result["sistema"] = system
    if "ano_referencia_inicial" not in result:
        result["ano_referencia_inicial"] = first_year
    if "ano_referencia_final" not in result:
        result["ano_referencia_final"] = last_year
    return result[
        [
            "sistema",
            "componente",
            "codigo_indicador_original",
            "nome_indicador_original",
            "unidade_original",
            "familia_original",
            "formula_original",
            "ano_referencia_inicial",
            "ano_referencia_final",
        ]
    ].drop_duplicates()


def _read_rar_indicator(path: Path) -> tuple[str, bytes]:
    listing = subprocess.run(
        ["tar", "-tf", str(path)], capture_output=True, check=True
    ).stdout.decode("utf-8")
    member = next(
        name
        for name in listing.splitlines()
        if "Indicadores" in name and name.endswith(".xlsx")
    )
    content = subprocess.run(
        ["tar", "-xOf", str(path), member], capture_output=True, check=True
    ).stdout
    return member, content


def _latest(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not matches:
        raise FileNotFoundError(f"Nenhum pacote encontrado: {directory / pattern}")
    return matches[-1]


def _text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()
