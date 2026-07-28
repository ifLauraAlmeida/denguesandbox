"""Coleta das planilhas anuais oficiais SNIS de resíduos sólidos."""

import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import httpx
import pandas as pd

from dengue_rj.collectors.http import validate_response
from dengue_rj.metadata.writer import append_collection_metadata
from dengue_rj.utils.hashing import sha256_bytes

BASE_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/snis/produtos-do-snis/diagnosticos"
)
ANNUAL_URLS = {
    2020: f"{BASE_URL}/Planilhas_RS2020.zip",
    2021: f"{BASE_URL}/Planilhas_RS2021.zip",
    2022: f"{BASE_URL}/Planilha_RS_2022_atualizado_29112024.zip",
}


@dataclass(frozen=True)
class SolidWasteCollection:
    raw_files: tuple[Path, ...]
    processed_file: Path
    records: int
    collected_at: datetime


def validate_zip(path: Path) -> None:
    try:
        with ZipFile(path) as archive:
            bad_file = archive.testzip()
            if bad_file is not None:
                raise ValueError(f"Arquivo corrompido dentro do ZIP: {bad_file}")
    except BadZipFile as error:
        raise ValueError(f"Pacote SNIS inválido: {path}") from error


def collect_solid_waste(
    raw_directory: Path = Path("data/raw/saneamento/snis_residuos_solidos"),
    processed_file: Path = Path(
        "data/processed/saneamento/snis_residuos_solidos_indicadores_rj_2020_2022.csv"
    ),
    dimension_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
) -> SolidWasteCollection:
    """Baixa e valida os pacotes nacionais de referência 2020–2022."""
    collected_at = datetime.now().astimezone()
    timestamp = collected_at.strftime("%Y%m%dT%H%M%S%z")
    raw_directory.mkdir(parents=True, exist_ok=True)
    files = []
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        for year, url in ANNUAL_URLS.items():
            response = client.get(url)
            validate_response(response)
            if not response.content.startswith(b"PK\x03\x04"):
                raise ValueError(f"Resposta de {year} não possui assinatura ZIP")
            destination = raw_directory / f"snis_residuos_solidos_{year}_{timestamp}.zip"
            destination.write_bytes(response.content)
            validate_zip(destination)
            files.append(destination)
            _record_collection(year, url, destination, response.content, collected_at)
    dimension = pd.read_csv(dimension_file, dtype=str)
    processed = pd.concat(
        [_parse_indicator_archive(path, year, dimension) for year, path in zip(ANNUAL_URLS, files)],
        ignore_index=True,
    )
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(processed_file, index=False)
    return SolidWasteCollection(tuple(files), processed_file, len(processed), collected_at)


def _parse_indicator_archive(
    path: Path, year: int, dimension: pd.DataFrame
) -> pd.DataFrame:
    with ZipFile(path) as archive:
        member = next(
            name for name in archive.namelist() if "Planilha_Indicadores_RS_" in name
        )
        source = pd.read_excel(BytesIO(archive.read(member)), header=None)

    code_row = next(
        row
        for row in range(min(15, len(source)))
        if source.iloc[row].astype(str).str.fullmatch(r"IN\d{3}").any()
    )
    data_start = next(
        row for row in range(code_row + 1, len(source))
        if pd.notna(pd.to_numeric(source.iloc[row, 0], errors="coerce"))
    )
    header_row = code_row - 3
    unit_row = code_row - 2
    headers = source.iloc[header_row].astype(str).str.strip()
    uf_column = next(index for index, value in headers.items() if value == "UF")
    name_column = next(index for index, value in headers.items() if value == "Município")
    ibge_candidates = [
        index for index, value in headers.items() if value == "Código do IBGE"
    ]
    code_column = ibge_candidates[0] if ibge_candidates else 0

    data = source.iloc[data_start:].copy()
    data = data[data.iloc[:, uf_column].astype(str).str.strip().eq("RJ")]
    code_map = {
        str(code)[:6]: str(code)
        for code in dimension["codigo_ibge_municipio"].astype(str)
    }
    source_codes = (
        data.iloc[:, code_column].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    )
    official_codes = source_codes.map(
        lambda value: value if len(value) == 7 else code_map.get(value[:6])
    )
    if official_codes.isna().any():
        raise ValueError(f"Código municipal de resíduos sem correspondência em {year}")

    frames = []
    for column in range(source.shape[1]):
        indicator = str(source.iloc[code_row, column]).strip()
        if not re.fullmatch(r"IN\d{3}", indicator):
            continue
        frame = pd.DataFrame(
            {
                "codigo_ibge_municipio": official_codes.to_numpy(),
                "codigo_municipio_origem": source_codes.to_numpy(),
                "nome_municipio_origem": data.iloc[:, name_column].astype(str).str.strip(),
                "ano": year,
                "codigo_indicador": indicator,
                "nome_indicador": str(source.iloc[header_row, column]).strip(),
                "unidade": str(source.iloc[unit_row, column]).strip(),
                "valor": pd.to_numeric(data.iloc[:, column], errors="coerce"),
                "fonte": "SNIS Resíduos Sólidos/Ministério das Cidades",
            }
        )
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    if result["codigo_ibge_municipio"].nunique() != len(data):
        raise ValueError(f"Municípios duplicados na planilha de resíduos de {year}")
    return result


def _record_collection(
    year: int, url: str, path: Path, content: bytes, collected_at: datetime
) -> None:
    append_collection_metadata(
        {
            "id_coleta": f"snis_residuos_{year}_{collected_at:%Y%m%dT%H%M%S%z}",
            "fonte": "SNIS/Ministério das Cidades",
            "sistema": "Diagnósticos SNIS",
            "descricao_base": "Planilhas de informações e indicadores de resíduos sólidos",
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
            "opcoes_selecionadas": {"componente": "residuos_solidos"},
            "codigo_http": 200,
            "status_coleta": "sucesso",
            "quantidade_registros": "",
            "hash_sha256": sha256_bytes(content),
            "versao_coletor": "0.1.0",
            "observacoes": "Pacote anual nacional preservado integralmente e validado como ZIP.",
        }
    )
