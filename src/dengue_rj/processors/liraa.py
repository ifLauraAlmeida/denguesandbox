"""Processamento municipal das planilhas LIRAa/LIA da SES-RJ."""

import re
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

WORKBOOK_PATTERN = re.compile(r"LIRAa_(\d{4})_(\d{2})")
VALUE_COLUMNS = {
    4: "iip_aedes_aegypti",
    5: "ib_aedes_aegypti",
    6: "estratos_iip_satisfatorio_n",
    7: "estratos_iip_satisfatorio_percentual",
    8: "estratos_iip_alerta_n",
    9: "estratos_iip_alerta_percentual",
    10: "estratos_iip_risco_n",
    11: "estratos_iip_risco_percentual",
    12: "criadouro_a1_n",
    13: "criadouro_a1_percentual",
    14: "criadouro_a2_n",
    15: "criadouro_a2_percentual",
    16: "criadouro_b_n",
    17: "criadouro_b_percentual",
    18: "criadouro_c_n",
    19: "criadouro_c_percentual",
    20: "criadouro_d1_n",
    21: "criadouro_d1_percentual",
    22: "criadouro_d2_n",
    23: "criadouro_d2_percentual",
    24: "criadouro_e_n",
    25: "criadouro_e_percentual",
    26: "iip_aedes_albopictus",
    27: "ib_aedes_albopictus",
}


@dataclass(frozen=True)
class LiraaProcessing:
    output_file: Path
    coverage_file: Path
    records: int
    surveys: int


def process_liraa(
    raw_directory: Path = Path("data/raw/liraa"),
    dimension_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
    output_directory: Path = Path("data/processed/liraa"),
) -> LiraaProcessing:
    """Consolida os levantamentos LIRAa/LIA de 2020–2024."""
    dimension = pd.read_csv(dimension_file, dtype=str)
    source_to_official = {
        code[:6]: code for code in dimension["codigo_ibge_municipio"]
    }
    frames = []
    for archive_path in sorted(raw_directory.glob("LIRAa_20??.zip")):
        with ZipFile(archive_path) as archive:
            for member in archive.namelist():
                if not member.lower().endswith((".xlsx", ".xls")):
                    continue
                match = WORKBOOK_PATTERN.search(Path(member).stem)
                if not match:
                    raise ValueError(f"Ano/mês ausente no nome LIRAa: {member}")
                year, month = map(int, match.groups())
                with archive.open(member) as stream:
                    source = pd.read_excel(stream, header=None)
                source = source.reindex(columns=range(28))
                frames.append(
                    _parse_workbook(
                        source,
                        year,
                        month,
                        member,
                        source_to_official,
                    )
                )
    result = pd.concat(frames, ignore_index=True)
    _validate_liraa(result, dimension)
    coverage = (
        result.groupby(["ano", "mes"], as_index=False)
        .agg(
            municipios_na_planilha=("codigo_ibge_municipio", "nunique"),
            municipios_com_iip=("iip_aedes_aegypti", "count"),
            municipios_justificados=(
                "status_levantamento",
                lambda values: values.eq("justificativa").sum(),
            ),
            municipios_sem_resultado=(
                "status_levantamento",
                lambda values: values.ne("observado").sum(),
            ),
        )
        .sort_values(["ano", "mes"])
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    output_file = output_directory / "liraa_municipio_levantamento_2020_2024.csv"
    coverage_file = output_directory / "cobertura_liraa_2020_2024.csv"
    result.to_csv(output_file, index=False)
    coverage.to_csv(coverage_file, index=False)
    return LiraaProcessing(
        output_file,
        coverage_file,
        len(result),
        result[["ano", "mes"]].drop_duplicates().shape[0],
    )


def _parse_workbook(
    source: pd.DataFrame,
    year: int,
    month: int,
    member: str,
    source_to_official: dict[str, str],
) -> pd.DataFrame:
    header_rows = source.index[
        source.iloc[:, 0].astype(str).str.strip().eq("IBGE")
    ].tolist()
    if len(header_rows) != 1:
        raise ValueError(f"Cabeçalho IBGE não identificado em {member}")
    data = source.iloc[header_rows[0] + 1 :].copy()
    source_code = data.iloc[:, 0].astype(str).str.extract(r"(\d{6})", expand=False)
    data = data[source_code.isin(source_to_official)].copy()
    source_code = source_code[source_code.isin(source_to_official)]
    result = pd.DataFrame(
        {
            "codigo_ibge_municipio": source_code.map(source_to_official),
            "codigo_municipio_origem": source_code,
            "nome_municipio_origem": data.iloc[:, 1].astype(str).str.strip(),
            "uf": data.iloc[:, 2].astype(str).str.strip(),
            "ano": year,
            "mes": month,
            "periodo_execucao_origem": data.iloc[:, 3].fillna("").astype(str).str.strip(),
        }
    )
    for position, name in VALUE_COLUMNS.items():
        result[name] = pd.to_numeric(data.iloc[:, position], errors="coerce")
    period = result["periodo_execucao_origem"].str.casefold()
    result["status_levantamento"] = "nao_informado"
    result.loc[result["iip_aedes_aegypti"].notna(), "status_levantamento"] = "observado"
    result.loc[
        result["iip_aedes_aegypti"].isna()
        & period.str.contains("justific|of.cio|oficio", regex=True),
        "status_levantamento",
    ] = "justificativa"
    result["flag_outlier_ib_maior_100"] = result["ib_aedes_aegypti"].gt(100)
    result["arquivo_origem"] = member
    result["fonte"] = "LIRAa/LIA — SES-RJ"
    return result


def _validate_liraa(result: pd.DataFrame, dimension: pd.DataFrame) -> None:
    if result.empty:
        raise ValueError("Nenhum registro LIRAa foi processado")
    if result.duplicated(["codigo_ibge_municipio", "ano", "mes"]).any():
        raise ValueError("Chaves município–ano–mês duplicadas no LIRAa")
    unknown = set(result["codigo_ibge_municipio"]).difference(
        dimension["codigo_ibge_municipio"]
    )
    if unknown:
        raise ValueError(f"LIRAa contém códigos municipais desconhecidos: {unknown}")
    if set(result["uf"]) != {"RJ"}:
        raise ValueError("LIRAa deve conter somente UF RJ")
    invalid_iip = result["iip_aedes_aegypti"].dropna().lt(0)
    if invalid_iip.any():
        raise ValueError("LIRAa contém IIP negativo")
