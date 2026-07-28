"""Coleta da referência oficial de transição SNIS-SINISA-ACERTAR."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

from dengue_rj.collectors.http import validate_response
from dengue_rj.metadata.writer import append_collection_metadata
from dengue_rj.utils.hashing import sha256_bytes

CROSSWALK_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/sinisa/arquivos/"
    "Planilha_De_Para_SINISA_SNIS_ACERTAR___20250623.pdf"
)


@dataclass(frozen=True)
class SinisaCrosswalkCollection:
    raw_file: Path
    collected_at: datetime


def collect_sinisa_crosswalk(
    raw_directory: Path = Path("data/raw/saneamento/sinisa_referencias"),
) -> SinisaCrosswalkCollection:
    """Baixa e valida o PDF oficial da regra de transição."""
    collected_at = datetime.now().astimezone()
    timestamp = collected_at.strftime("%Y%m%dT%H%M%S%z")
    raw_directory.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        response = client.get(CROSSWALK_URL)
    validate_response(response)
    if not response.content.startswith(b"%PDF-"):
        raise ValueError("Resposta do de-para SINISA-SNIS não é um PDF")
    destination = raw_directory / f"de_para_sinisa_snis_acertar_{timestamp}.pdf"
    if destination.exists():
        raise FileExistsError(f"Arquivo bruto já existe: {destination}")
    destination.write_bytes(response.content)
    append_collection_metadata(
        {
            "id_coleta": f"sinisa_de_para_{collected_at:%Y%m%dT%H%M%S%z}",
            "fonte": "SINISA/Ministério das Cidades",
            "sistema": "SINISA",
            "descricao_base": "Regra de transição SNIS-SINISA-ACERTAR",
            "url_origem": CROSSWALK_URL,
            "endpoint": CROSSWALK_URL,
            "metodo_http": "GET",
            "arquivo_bruto": str(destination),
            "formato_arquivo": "pdf",
            "data_referencia_inicial": "",
            "data_referencia_final": "",
            "data_hora_coleta": collected_at.isoformat(),
            "parametros_requisicao": {},
            "filtros_selecionados": {},
            "opcoes_selecionadas": {"tipo": "de_para"},
            "codigo_http": response.status_code,
            "status_coleta": "sucesso",
            "quantidade_registros": "",
            "hash_sha256": sha256_bytes(response.content),
            "versao_coletor": "0.1.0",
            "observacoes": "PDF oficial preservado integralmente antes da extração.",
        }
    )
    return SinisaCrosswalkCollection(destination, collected_at)
