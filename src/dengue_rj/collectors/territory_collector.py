"""Coleta oficial da dimensão municipal na API de Localidades do IBGE."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd

from dengue_rj.collectors.http import validate_response
from dengue_rj.metadata.writer import append_collection_metadata
from dengue_rj.processors.territory import build_municipality_dimension
from dengue_rj.utils.hashing import sha256_bytes

IBGE_MUNICIPALITIES_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/estados/33/municipios"
)


@dataclass(frozen=True)
class TerritoryCollection:
    raw_file: Path
    processed_file: Path
    sha256: str
    records: int
    collected_at: datetime


def parse_ibge_municipalities(content: bytes) -> pd.DataFrame:
    """Converte a resposta oficial do IBGE em dimensão municipal validada."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("Resposta IBGE não contém JSON válido") from error
    if not isinstance(payload, list):
        raise TypeError(f"Resposta IBGE deve ser uma lista; recebido {type(payload).__name__}")
    return build_municipality_dimension(payload)


def collect_territory(
    raw_directory: Path = Path("data/raw/demografia"),
    processed_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
    url: str = IBGE_MUNICIPALITIES_URL,
) -> TerritoryCollection:
    """Baixa, preserva e processa a dimensão oficial sem sobrescrever bruto."""
    collected_at = datetime.now().astimezone()
    response = httpx.get(url, timeout=60, follow_redirects=True)
    validate_response(response)
    dimension = parse_ibge_municipalities(response.content)
    timestamp = collected_at.strftime("%Y%m%dT%H%M%S%z")
    raw_file = raw_directory / f"ibge_municipios_rj_{timestamp}.json"
    if raw_file.exists():
        raise FileExistsError(f"Arquivo bruto já existe: {raw_file}")
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_bytes(response.content)
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    dimension.to_csv(processed_file, index=False)
    result = TerritoryCollection(
        raw_file, processed_file, sha256_bytes(response.content), len(dimension), collected_at
    )
    append_collection_metadata(
        {
            "id_coleta": f"ibge_municipios_rj_{timestamp}",
            "fonte": "IBGE",
            "sistema": "API de Localidades",
            "descricao_base": "Municípios do Estado do Rio de Janeiro",
            "url_origem": url,
            "endpoint": url,
            "metodo_http": "GET",
            "arquivo_bruto": str(raw_file),
            "formato_arquivo": "json",
            "data_hora_coleta": collected_at.isoformat(),
            "parametros_requisicao": {},
            "filtros_selecionados": {"codigo_uf": "33"},
            "opcoes_selecionadas": {},
            "codigo_http": response.status_code,
            "status_coleta": "sucesso",
            "quantidade_registros": len(dimension),
            "hash_sha256": result.sha256,
            "versao_coletor": "0.1.0",
            "observacoes": "Identificadores oficiais da API de Localidades do IBGE.",
        }
    )
    return result
