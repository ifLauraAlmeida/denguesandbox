"""Recorte analítico de dengue por município de residência no RJ."""

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

RESIDENCE_COLUMN = "ID_MN_RESI"
PROHIBITED_DIRECT_IDENTIFIERS = frozenset(
    {
        "NU_NOTIFIC",
        "NM_PACIENT",
        "NM_MAE_PAC",
        "NU_CNS",
        "LOGRADOURO",
        "NUMERO",
        "COMPLEMENT",
        "BAIRRO",
        "CEP",
        "TELEFONE",
    }
)
SAFE_COLUMNS = (
    "DT_NOTIFIC",
    "SEM_NOT",
    "DT_SIN_PRI",
    "SEM_PRI",
    RESIDENCE_COLUMN,
    "CS_SEXO",
    "NU_IDADE_N",
    "CLASSI_FIN",
    "CRITERIO",
    "EVOLUCAO",
    "DT_OBITO",
    "DT_ENCERRA",
    "SOROTIPO",
)


@dataclass(frozen=True)
class SinanProcessing:
    output_file: Path
    records: int
    municipalities: int


def process_sinan_residence(
    archive_file: Path,
    year: int,
    dimension_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
    output_directory: Path = Path("data/processed/dengue"),
) -> SinanProcessing:
    """Filtra exclusivamente residentes do RJ e remove campos não analíticos."""
    dimension = pd.read_csv(dimension_file, dtype=str)
    official_codes = set(dimension["codigo_ibge_municipio"])
    source_to_official = {
        code[:6]: code for code in dimension["codigo_ibge_municipio"]
    }
    if len(source_to_official) != len(official_codes):
        raise ValueError("Códigos IBGE de seis dígitos não são unívocos na dimensão")
    frames = []
    with ZipFile(archive_file) as archive:
        member = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
        with archive.open(member) as stream:
            for chunk in pd.read_csv(
                stream,
                sep=",",
                encoding="latin-1",
                dtype=str,
                chunksize=100_000,
                low_memory=False,
            ):
                _validate_contract(chunk)
                residence = chunk[RESIDENCE_COLUMN].str.strip()
                mask = residence.isin(source_to_official)
                selected = chunk[mask].copy()
                selected[RESIDENCE_COLUMN] = residence[mask]
                selected.insert(
                    0,
                    "codigo_ibge_municipio",
                    selected[RESIDENCE_COLUMN].map(source_to_official),
                )
                frames.append(selected[["codigo_ibge_municipio", *SAFE_COLUMNS]])
    result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=SAFE_COLUMNS)
    if not set(result["codigo_ibge_municipio"]).issubset(official_codes):
        raise ValueError("O recorte contém município fora da dimensão oficial do RJ")
    result.insert(0, "ANO_BASE", year)
    result.insert(1, "CRITERIO_TERRITORIAL", "municipio_residencia")
    output_directory.mkdir(parents=True, exist_ok=True)
    output = output_directory / f"sinan_dengue_rj_residencia_{year}.csv"
    result.to_csv(output, index=False)
    return SinanProcessing(
        output,
        len(result),
        result[RESIDENCE_COLUMN].nunique(),
    )


def _validate_contract(table: pd.DataFrame) -> None:
    missing = set(SAFE_COLUMNS).difference(table.columns)
    if missing:
        raise ValueError(f"Campos obrigatórios ausentes no SINAN: {sorted(missing)}")
    if RESIDENCE_COLUMN != "ID_MN_RESI":
        raise ValueError("A dimensão territorial do SINAN deve ser município de residência")
    if PROHIBITED_DIRECT_IDENTIFIERS.intersection(SAFE_COLUMNS):
        raise ValueError("O recorte seguro não pode conter identificadores diretos")
