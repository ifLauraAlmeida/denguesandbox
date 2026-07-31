"""Processamento municipal dos quatro componentes SINISA, referências 2023–2024."""

import re
import subprocess
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

INDICATOR_PATTERN = re.compile(r"I[A-Z]{2}\d{4}")
REFERENCE_YEAR = 2023


@dataclass(frozen=True)
class SinisaMunicipalProcessing:
    component_files: tuple[Path, ...]
    coverage_file: Path
    records: int


def process_sinisa_municipal(
    raw_directory: Path = Path("data/raw/saneamento/sinisa"),
    output_directory: Path = Path("data/processed/saneamento"),
    dimension_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
) -> SinisaMunicipalProcessing:
    """Processa os indicadores de água, esgoto, resíduos e águas pluviais."""
    dimension = pd.read_csv(dimension_file, dtype=str)
    tables_2023 = {
        "abastecimento_agua": _parse_water_sewer_archive(
            _latest(raw_directory, "*abastecimento_agua*ref2023*.zip"),
            "abastecimento_agua",
            dimension,
        ),
        "esgotamento_sanitario": _parse_water_sewer_archive(
            _latest(raw_directory, "*esgotamento_sanitario*ref2023*.zip"),
            "esgotamento_sanitario",
            dimension,
        ),
        "residuos_solidos": _parse_solid_waste_archive(
            _latest(raw_directory, "*residuos_solidos*ref2023*.rar"),
            dimension,
        ),
        "aguas_pluviais": _parse_stormwater_archive(
            _latest(raw_directory, "*aguas_pluviais*ref2023*.rar"),
            dimension,
        ),
    }
    tables_2024 = {
        "abastecimento_agua": _parse_water_sewer_archive_2024(
            _latest(raw_directory, "*abastecimento_agua*ref2024*.zip"),
            "abastecimento_agua", dimension,
        ),
        "esgotamento_sanitario": _parse_water_sewer_archive_2024(
            _latest(raw_directory, "*esgotamento_sanitario*ref2024*.zip"),
            "esgotamento_sanitario", dimension,
        ),
        "residuos_solidos": _parse_solid_waste_archive_2024(
            _latest(raw_directory, "*residuos_solidos*ref2024*.zip"), dimension,
        ),
        "aguas_pluviais": _parse_stormwater_archive_2024(
            _latest(raw_directory, "*aguas_pluviais*ref2024*.zip"), dimension,
        ),
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    files = []
    for year, tables in ((2023, tables_2023), (2024, tables_2024)):
        for component, table in tables.items():
            path = output_directory / f"sinisa_{component}_indicadores_rj_{year}.csv"
            table.to_csv(path, index=False)
            files.append(path)
    coverage = pd.concat(
        [_build_coverage(tables_2023), _build_coverage(tables_2024)], ignore_index=True
    )
    coverage_file = output_directory / "cobertura_saneamento_snis_sinisa_2020_2024.csv"
    _append_snis_coverage(coverage_file, coverage)
    return SinisaMunicipalProcessing(
        tuple(files), coverage_file,
        sum(len(table) for tables in (tables_2023, tables_2024) for table in tables.values())
    )


def _parse_water_sewer_archive_2024(
    path: Path, component: str, dimension: pd.DataFrame
) -> pd.DataFrame:
    with ZipFile(path) as archive:
        member = next(name for name in archive.namelist() if "Indicadores_Base Municipal" in name)
        source = pd.read_excel(BytesIO(archive.read(member)), header=None)
    code_row = _row_containing(source, "cod_IBGE")
    codes = source.iloc[code_row].map(_text)
    data = source.iloc[code_row + 1 :].copy()
    code_column = _column_by_code(codes, "cod_IBGE")
    name_column = _column_by_code(codes, "Município")
    uf_column = _column_by_code(codes, "UF")
    data = data[data.iloc[:, uf_column].map(_text).eq("RJ")]
    municipality = _municipality_identity(data, code_column, name_column, dimension, component)
    frames = []
    for column, code in codes.items():
        if INDICATOR_PATTERN.fullmatch(code):
            frames.append(_indicator_frame(
                municipality=municipality, values=data.iloc[:, column], component=component,
                family=_text(source.iat[code_row - 3, column]), code=code,
                name=_text(source.iat[code_row - 2, column]), unit=_text(source.iat[code_row - 1, column]),
                formula="", provider_name=data.iloc[:, _column_by_code(codes, "CAD0005")].map(_text),
                provider_acronym=data.iloc[:, _column_by_code(codes, "CAD0006")].map(_text),
                provider_scope=data.iloc[:, _column_by_code(codes, "CAD0003")].map(_text), year=2024,
            ))
    return pd.concat(frames, ignore_index=True)


def _parse_solid_waste_archive_2024(path: Path, dimension: pd.DataFrame) -> pd.DataFrame:
    with ZipFile(path) as archive:
        member = next(name for name in archive.namelist() if "Indicadores" in name)
        source = pd.read_excel(BytesIO(archive.read(member)), header=None)
    return _parse_municipal_indicator_sheet(source, dimension, "residuos_solidos", 2024)


def _parse_stormwater_archive_2024(path: Path, dimension: pd.DataFrame) -> pd.DataFrame:
    with ZipFile(path) as archive:
        nested = next(name for name in archive.namelist() if "Indicadores" in name)
        with ZipFile(BytesIO(archive.read(nested))) as inner:
            member = next(name for name in inner.namelist() if name.endswith(".xlsx"))
            source = pd.read_excel(BytesIO(inner.read(member)), header=None)
    return _parse_municipal_indicator_sheet(source, dimension, "aguas_pluviais", 2024)


def _parse_municipal_indicator_sheet(
    source: pd.DataFrame, dimension: pd.DataFrame, component: str, year: int
) -> pd.DataFrame:
    # Escolhe a linha com maior quantidade de códigos de indicadores.
    candidates = [(row, source.iloc[row].map(_text).str.fullmatch(INDICATOR_PATTERN).sum()) for row in range(min(20, len(source)))]
    code_row = max(candidates, key=lambda item: item[1])[0]
    codes = source.iloc[code_row].map(_text)
    data = source.iloc[code_row + 1 :].copy()
    code_column, name_column, uf_column = (1, 2, 3) if component == "residuos_solidos" else (0, 1, 2)
    data = data[data.iloc[:, uf_column].map(_text).eq("RJ")]
    municipality = _municipality_identity(data, code_column, name_column, dimension, component)
    frames = []
    for column, code in codes.items():
        if INDICATOR_PATTERN.fullmatch(code):
            frames.append(_indicator_frame(
                municipality=municipality, values=data.iloc[:, column], component=component,
                family=_text(source.iat[max(0, code_row - 4), column]), code=code,
                name=_text(source.iat[code_row - 3, column]), formula=_text(source.iat[code_row - 2, column]),
                unit=_text(source.iat[code_row - 1, column]), year=year,
            ))
    result = pd.concat(frames, ignore_index=True)
    _validate_municipal_indicator_key(result, component)
    return result


def _parse_water_sewer_archive(
    path: Path, component: str, dimension: pd.DataFrame
) -> pd.DataFrame:
    with ZipFile(path) as archive:
        member = next(
            name
            for name in archive.namelist()
            if "Indicadores_Base Municipal" in name
        )
        workbook = pd.ExcelFile(BytesIO(archive.read(member)))
        frames = []
        for sheet in workbook.sheet_names:
            if "nota" in sheet.casefold():
                continue
            source = pd.read_excel(workbook, sheet_name=sheet, header=None)
            codes = source.iloc[9].map(_text)
            code_column = _column_by_code(codes, "cod_IBGE")
            name_column = _column_by_code(codes, "Município")
            uf_column = _column_by_code(codes, "UF")
            provider_name = _column_by_code(codes, "CAD0005")
            provider_acronym = _column_by_code(codes, "CAD0006")
            provider_scope = _optional_column_by_code(codes, "CAD0003")
            data = source.iloc[10:].copy()
            data = data[data.iloc[:, uf_column].map(_text).eq("RJ")]
            municipality = _municipality_identity(
                data, code_column, name_column, dimension, component
            )
            for column, code in codes.items():
                if not INDICATOR_PATTERN.fullmatch(code):
                    continue
                frames.append(
                    _indicator_frame(
                        municipality=municipality,
                        values=data.iloc[:, column],
                        component=component,
                        family=sheet,
                        code=code,
                        name=_text(source.iat[7, column]),
                        unit=_text(source.iat[8, column]),
                        formula="",
                        provider_name=data.iloc[:, provider_name].map(_text),
                        provider_acronym=data.iloc[:, provider_acronym].map(_text),
                        provider_scope=(
                            data.iloc[:, provider_scope].map(_text)
                            if provider_scope is not None
                            else pd.Series("", index=data.index)
                        ),
                    )
                )
    result = pd.concat(frames, ignore_index=True)
    key = [
        "codigo_ibge_municipio",
        "nome_prestador",
        "sigla_prestador",
        "familia_indicador",
        "codigo_indicador",
    ]
    if result.duplicated(key).any():
        raise ValueError(f"Duplicidade município-prestador-indicador em {component}")
    return result


def _parse_solid_waste_archive(
    path: Path, dimension: pd.DataFrame
) -> pd.DataFrame:
    _member, content = _read_rar_indicator(path)
    source = pd.read_excel(BytesIO(content), header=None)
    data = source.iloc[13:].copy()
    data = data[data.iloc[:, 3].map(_text).eq("RJ")]
    municipality = _municipality_identity(data, 1, 2, dimension, "residuos_solidos")
    families = source.iloc[9].ffill()
    frames = []
    for column in range(source.shape[1]):
        code = _text(source.iat[10, column])
        if not INDICATOR_PATTERN.fullmatch(code):
            continue
        frames.append(
            _indicator_frame(
                municipality=municipality,
                values=data.iloc[:, column],
                component="residuos_solidos",
                family=_text(families.iloc[column]),
                code=code,
                name=_text(source.iat[11, column]),
                unit=_text(source.iat[12, column]),
                formula="",
                response_status=data.iloc[:, 0].map(_text),
            )
        )
    result = pd.concat(frames, ignore_index=True)
    _validate_municipal_indicator_key(result, "resíduos sólidos")
    return result


def _parse_stormwater_archive(
    path: Path, dimension: pd.DataFrame
) -> pd.DataFrame:
    _member, content = _read_rar_indicator(path)
    source = pd.read_excel(BytesIO(content), header=None)
    data = source.iloc[11:].copy()
    data = data[data.iloc[:, 2].map(_text).eq("RJ")]
    municipality = _municipality_identity(data, 0, 1, dimension, "aguas_pluviais")
    families = source.iloc[6].ffill()
    frames = []
    for column in range(source.shape[1]):
        code = _text(source.iat[10, column])
        if not INDICATOR_PATTERN.fullmatch(code):
            continue
        frames.append(
            _indicator_frame(
                municipality=municipality,
                values=data.iloc[:, column],
                component="aguas_pluviais",
                family=_text(families.iloc[column]),
                code=code,
                name=_text(source.iat[7, column]),
                unit=_text(source.iat[9, column]),
                formula=_text(source.iat[8, column]),
                response_status=data.iloc[:, 12].map(_text),
            )
        )
    result = pd.concat(frames, ignore_index=True)
    _validate_municipal_indicator_key(result, "águas pluviais")
    return result


def _indicator_frame(
    *,
    municipality: pd.DataFrame,
    values: pd.Series,
    component: str,
    family: str,
    code: str,
    name: str,
    unit: str,
    formula: str,
    provider_name: pd.Series | None = None,
    provider_acronym: pd.Series | None = None,
    provider_scope: pd.Series | None = None,
    response_status: pd.Series | None = None,
    year: int = REFERENCE_YEAR,
) -> pd.DataFrame:
    value_origin = values.map(_text)
    numeric = pd.to_numeric(value_origin.str.replace(",", ".", regex=False), errors="coerce")
    status = pd.Series("observado", index=values.index)
    status[value_origin.eq("")] = "ausente"
    status[value_origin.ne("") & numeric.isna()] = value_origin[
        value_origin.ne("") & numeric.isna()
    ]
    return pd.DataFrame(
        {
            **{column: municipality[column].to_numpy() for column in municipality},
            "ano": year,
            "componente": component,
            "codigo_prestador": "",
            "nome_prestador": (
                provider_name.to_numpy() if provider_name is not None else ""
            ),
            "sigla_prestador": (
                provider_acronym.to_numpy() if provider_acronym is not None else ""
            ),
            "abrangencia_prestador": (
                provider_scope.to_numpy() if provider_scope is not None else ""
            ),
            "familia_indicador": family,
            "codigo_indicador": code,
            "nome_indicador": name,
            "formula": formula,
            "unidade": unit,
            "valor_origem": value_origin.to_numpy(),
            "valor": numeric.to_numpy(),
            "status_valor": status.to_numpy(),
            "status_resposta": (
                response_status.to_numpy() if response_status is not None else ""
            ),
            "fonte": "SINISA/Ministério das Cidades",
            "nivel_origem": (
                "municipio_prestador"
                if provider_name is not None
                else "municipio"
            ),
        }
    )


def _municipality_identity(
    data: pd.DataFrame,
    code_column: int,
    name_column: int,
    dimension: pd.DataFrame,
    component: str,
) -> pd.DataFrame:
    source_codes = (
        data.iloc[:, code_column].map(_text).str.replace(r"\.0$", "", regex=True)
    )
    official = set(dimension["codigo_ibge_municipio"].astype(str))
    if not set(source_codes).issubset(official):
        missing = sorted(set(source_codes) - official)
        raise ValueError(f"Códigos municipais sem correspondência em {component}: {missing}")
    return pd.DataFrame(
        {
            "codigo_ibge_municipio": source_codes.to_numpy(),
            "codigo_municipio_origem": source_codes.to_numpy(),
            "nome_municipio_origem": data.iloc[:, name_column].map(_text).to_numpy(),
            "uf": "RJ",
        },
        index=data.index,
    )


def _build_coverage(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    for component, table in tables.items():
        records.append(
            {
                "sistema": "SINISA",
                "ano": int(table["ano"].iloc[0]),
                "componente": component,
                "municipios_na_base": table["codigo_ibge_municipio"].nunique(),
                "municipios_com_valor": table.loc[
                    table["valor"].notna(), "codigo_ibge_municipio"
                ].nunique(),
                "indicadores": table["codigo_indicador"].nunique(),
                "registros": len(table),
                "valores_presentes": table["valor"].notna().sum(),
                "nivel_origem": table["nivel_origem"].iloc[0],
            }
        )
    return pd.DataFrame(records)


def _append_snis_coverage(path: Path, sinisa: pd.DataFrame) -> None:
    processed = path.parent
    rows = []
    sources = {
        "agua_esgoto": processed / "snis_agua_esgoto_indicadores_2020_2022.csv",
        "residuos_solidos": (
            processed / "snis_residuos_solidos_indicadores_rj_2020_2022.csv"
        ),
        "aguas_pluviais": (
            processed / "snis_aguas_pluviais_indicadores_rj_2020_2022.csv"
        ),
    }
    water_sewer = pd.read_csv(sources["agua_esgoto"], dtype=str)
    water_codes = {"IN049", "IN055"}
    for component, codes in (
        ("abastecimento_agua", water_codes),
        (
            "esgotamento_sanitario",
            set(water_sewer["codigo_indicador"]) - water_codes,
        ),
    ):
        subset = water_sewer[water_sewer["codigo_indicador"].isin(codes)]
        rows.extend(_coverage_rows("SNIS", component, subset, "municipio_prestador"))
    for component in ("residuos_solidos", "aguas_pluviais"):
        table = pd.read_csv(sources[component], dtype=str)
        rows.extend(_coverage_rows("SNIS", component, table, "municipio"))
    result = pd.concat([pd.DataFrame(rows), sinisa], ignore_index=True)
    result.sort_values(["componente", "ano", "sistema"]).to_csv(path, index=False)


def _coverage_rows(
    system: str, component: str, table: pd.DataFrame, level: str
) -> list[dict[str, object]]:
    table = table.copy()
    table["valor"] = pd.to_numeric(table["valor"], errors="coerce")
    return [
        {
            "sistema": system,
            "ano": int(year),
            "componente": component,
            "municipios_na_base": group["codigo_ibge_municipio"].nunique(),
            "municipios_com_valor": group.loc[
                group["valor"].notna(), "codigo_ibge_municipio"
            ].nunique(),
            "indicadores": group["codigo_indicador"].nunique(),
            "registros": len(group),
            "valores_presentes": group["valor"].notna().sum(),
            "nivel_origem": level,
        }
        for year, group in table.groupby("ano")
    ]


def _validate_municipal_indicator_key(result: pd.DataFrame, label: str) -> None:
    key = ["codigo_ibge_municipio", "codigo_indicador"]
    if result.duplicated(key).any():
        raise ValueError(f"Duplicidade município-indicador em {label}")


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


def _column_by_code(codes: pd.Series, target: str) -> int:
    matches = codes[codes.eq(target)]
    if len(matches) != 1:
        raise ValueError(f"Esperada uma coluna {target}; encontradas {len(matches)}")
    return int(matches.index[0])


def _row_containing(source: pd.DataFrame, target: str) -> int:
    for row in range(min(20, len(source))):
        if source.iloc[row].map(_text).eq(target).any():
            return row
    raise ValueError(f"Linha contendo {target} não encontrada")


def _optional_column_by_code(codes: pd.Series, target: str) -> int | None:
    matches = codes[codes.eq(target)]
    return int(matches.index[0]) if len(matches) == 1 else None


def _latest(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not matches:
        raise FileNotFoundError(f"Nenhum pacote encontrado: {directory / pattern}")
    return matches[-1]


def _text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()
