"""Coleta dos glossários necessários à harmonização de água e esgoto."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

from dengue_rj.collectors.http import validate_response
from dengue_rj.metadata.writer import append_collection_metadata
from dengue_rj.utils.hashing import sha256_bytes

GLOSSARY_URLS = {
    "snis_agua_esgoto_indicadores_2022": (
        "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
        "saneamento/snis/produtos-do-snis/diagnosticos/"
        "Glossario_Indicadores_AE2022.pdf"
    ),
    "sinisa_agua_indicadores_ref2023": (
        "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
        "saneamento/sinisa/resultados-sinisa/"
        "INDICADORES_SINISA_ABASTECIMENTO_DE_AGUA_2024_v2.pdf"
    ),
    "sinisa_esgoto_indicadores_ref2023": (
        "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
        "saneamento/sinisa/arquivos/"
        "INDICADORES_SINISA_ESGOTAMENTOSANITRIO_2024_V2.pdf"
    ),
}


@dataclass(frozen=True)
class SanitationGlossaryCollection:
    raw_files: tuple[Path, ...]
    collected_at: datetime


def collect_sanitation_glossaries(
    raw_directory: Path = Path("data/raw/saneamento/glossarios"),
) -> SanitationGlossaryCollection:
    """Baixa e valida os três glossários oficiais de comparação."""
    collected_at = datetime.now().astimezone()
    timestamp = collected_at.strftime("%Y%m%dT%H%M%S%z")
    raw_directory.mkdir(parents=True, exist_ok=True)
    files = []
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        for name, url in GLOSSARY_URLS.items():
            response = client.get(url)
            validate_response(response)
            if not response.content.startswith(b"%PDF-"):
                raise ValueError(f"Glossário {name} não é um PDF")
            destination = raw_directory / f"{name}_{timestamp}.pdf"
            if destination.exists():
                raise FileExistsError(f"Arquivo bruto já existe: {destination}")
            destination.write_bytes(response.content)
            files.append(destination)
            _record_collection(
                name,
                url,
                destination,
                response.content,
                response.status_code,
                collected_at,
            )
    return SanitationGlossaryCollection(tuple(files), collected_at)


def _record_collection(
    name: str,
    url: str,
    path: Path,
    content: bytes,
    status_code: int,
    collected_at: datetime,
) -> None:
    append_collection_metadata(
        {
            "id_coleta": f"{name}_{collected_at:%Y%m%dT%H%M%S%z}",
            "fonte": "SNIS/SINISA - Ministério das Cidades",
            "sistema": "SNIS/SINISA",
            "descricao_base": f"Glossário oficial: {name}",
            "url_origem": url,
            "endpoint": url,
            "metodo_http": "GET",
            "arquivo_bruto": str(path),
            "formato_arquivo": "pdf",
            "data_referencia_inicial": 2022 if name.startswith("snis_") else 2023,
            "data_referencia_final": 2022 if name.startswith("snis_") else 2023,
            "data_hora_coleta": collected_at.isoformat(),
            "parametros_requisicao": {},
            "filtros_selecionados": {},
            "opcoes_selecionadas": {"documento": name},
            "codigo_http": status_code,
            "status_coleta": "sucesso",
            "quantidade_registros": "",
            "hash_sha256": sha256_bytes(content),
            "versao_coletor": "0.1.0",
            "observacoes": "PDF oficial preservado integralmente antes da análise.",
        }
    )
