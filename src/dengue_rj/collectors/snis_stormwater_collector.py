"""Coleta das planilhas anuais oficiais SNIS de águas pluviais."""

import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import httpx
import pandas as pd

from dengue_rj.collectors.http import validate_response
from dengue_rj.collectors.snis_solid_waste_collector import validate_zip
from dengue_rj.metadata.writer import append_collection_metadata
from dengue_rj.utils.hashing import sha256_bytes

BASE_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/snis/produtos-do-snis/diagnosticos"
)
ANNUAL_URLS = {
    year: f"{BASE_URL}/Planilhas_AP{year}.zip" for year in (2020, 2021, 2022)
}


@dataclass(frozen=True)
class StormwaterCollection:
    raw_files: tuple[Path, ...]
    processed_file: Path
    records: int
    collected_at: datetime


def collect_stormwater(
    raw_directory: Path = Path("data/raw/saneamento/snis_aguas_pluviais"),
    processed_file: Path = Path(
        "data/processed/saneamento/"
        "snis_aguas_pluviais_indicadores_rj_2020_2022.csv"
    ),
    dimension_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
) -> StormwaterCollection:
    """Baixa os pacotes 2020–2022 e processa os indicadores municipais do RJ."""
    collected_at = datetime.now().astimezone()
    timestamp = collected_at.strftime("%Y%m%dT%H%M%S%z")
    raw_directory.mkdir(parents=True, exist_ok=True)
    files = []
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        for year, url in ANNUAL_URLS.items():
            response = client.get(url)
            validate_response(response)
            if not response.content.startswith(b"PK\x03\x04"):
                raise ValueError(f"Resposta de águas pluviais {year} não é ZIP")
            destination = raw_directory / f"snis_aguas_pluviais_{year}_{timestamp}.zip"
            destination.write_bytes(response.content)
            validate_zip(destination)
            files.append(destination)
            _record_collection(year, url, destination, response.content, collected_at)
    dimension = pd.read_csv(dimension_file, dtype=str)
    processed = pd.concat(
        [
            _parse_indicator_archive(path, year, dimension)
            for year, path in zip(ANNUAL_URLS, files)
        ],
        ignore_index=True,
    )
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(processed_file, index=False)
    return StormwaterCollection(
        tuple(files), processed_file, len(processed), collected_at
    )


def _parse_indicator_archive(
    path: Path, year: int, dimension: pd.DataFrame
) -> pd.DataFrame:
    with ZipFile(path) as archive:
        member = next(
            name
            for name in archive.namelist()
            if "indicador" in name.casefold()
        )
        source = pd.read_excel(BytesIO(archive.read(member)), sheet_name=0, header=None)

    code_row = next(
        row
        for row in range(min(15, len(source)))
        if source.iloc[row].astype(str).str.fullmatch(r"IN\d{3}").any()
    )
    data_start = next(
        row
        for row in range(code_row + 1, len(source))
        if pd.notna(pd.to_numeric(source.iloc[row, 0], errors="coerce"))
    )
    family_row = code_row - 4
    name_row = code_row - 3
    formula_row = code_row - 2
    unit_row = code_row - 1
    families = source.iloc[family_row].ffill()

    data = source.iloc[data_start:].copy()
    data = data[data.iloc[:, 2].astype(str).str.strip().eq("RJ")]
    source_codes = (
        data.iloc[:, 0].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    )
    code_map = {
        str(code)[:6]: str(code)
        for code in dimension["codigo_ibge_municipio"].astype(str)
    }
    official_codes = source_codes.map(
        lambda value: value if len(value) == 7 else code_map.get(value[:6])
    )
    if official_codes.isna().any():
        raise ValueError(
            f"Código municipal de águas pluviais sem correspondência em {year}"
        )
    if official_codes.nunique() != len(data):
        raise ValueError(
            f"Municípios duplicados na planilha de águas pluviais de {year}"
        )

    frames = []
    for column in range(source.shape[1]):
        indicator = str(source.iloc[code_row, column]).strip()
        if not re.fullmatch(r"IN\d{3}", indicator):
            continue
        frames.append(
            pd.DataFrame(
                {
                    "codigo_ibge_municipio": official_codes.to_numpy(),
                    "codigo_municipio_origem": source_codes.to_numpy(),
                    "nome_municipio_origem": data.iloc[:, 1].astype(str).str.strip(),
                    "ano": year,
                    "familia_indicador": str(families.iloc[column]).strip(),
                    "codigo_indicador": indicator,
                    "nome_indicador": str(source.iloc[name_row, column]).strip(),
                    "formula": str(source.iloc[formula_row, column]).strip(),
                    "unidade": str(source.iloc[unit_row, column]).strip(),
                    "valor": pd.to_numeric(data.iloc[:, column], errors="coerce"),
                    "fonte": "SNIS Águas Pluviais/Ministério das Cidades",
                }
            )
        )
    if not frames:
        raise ValueError(f"Nenhum indicador de águas pluviais encontrado em {year}")
    return pd.concat(frames, ignore_index=True)


def _record_collection(
    year: int, url: str, path: Path, content: bytes, collected_at: datetime
) -> None:
    append_collection_metadata(
        {
            "id_coleta": f"snis_aguas_pluviais_{year}_{collected_at:%Y%m%dT%H%M%S%z}",
            "fonte": "SNIS/Ministério das Cidades",
            "sistema": "Diagnósticos SNIS",
            "descricao_base": "Planilhas de informações e indicadores de águas pluviais",
            "url_origem": url,
            "endpoint": url,
            "metodo_http": "GET",
            "arquivo_bruto": str(path),
            "formato_arquivo": "zip",
            "data_referencia_inicial": year,
            "data_referencia_final": year,
            "data_hora_coleta": collected_at.isoformat(),
            "parametros_requisicao": {},
            "filtros_selecionados": {},
            "opcoes_selecionadas": {"componente": "aguas_pluviais"},
            "codigo_http": 200,
            "status_coleta": "sucesso",
            "quantidade_registros": "",
            "hash_sha256": sha256_bytes(content),
            "versao_coletor": "0.1.0",
            "observacoes": "Pacote anual nacional preservado integralmente e validado como ZIP.",
        }
    )
