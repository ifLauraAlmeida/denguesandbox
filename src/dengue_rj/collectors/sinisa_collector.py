"""Coleta dos pacotes oficiais da primeira divulgação do SINISA."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from dengue_rj.collectors.base import CollectionRequest, Collector
from dengue_rj.collectors.http import validate_response
from dengue_rj.metadata.writer import append_collection_metadata
from dengue_rj.utils.hashing import sha256_bytes

RESULTS_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/sinisa/resultados-sinisa"
)
BASE_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/sinisa"
)
REFERENCE_YEAR = 2023

OFFICIAL_PACKAGES = {
    "gestao_municipal": (
        f"{RESULTS_URL}/SINISA_GESTAOMUNICIPAL_Informacoes_2023.xlsx"
    ),
    "abastecimento_agua": (
        f"{BASE_URL}/arquivos/SINISA_AGUA_Planilhas_2023_v2.1.1.zip"
    ),
    "esgotamento_sanitario": (
        f"{RESULTS_URL}/SINISA_ESGOTO_Planilhas_2023_v2.zip"
    ),
    "residuos_solidos": (
        f"{RESULTS_URL}/SINISA_RESIDUOS_Planilhas_2023.rar"
    ),
    "aguas_pluviais": (
        f"{RESULTS_URL}/SINISA_AGUASPLUVIAIS_PLANILHAS_2023_V224042025.rar"
    ),
}


@dataclass(frozen=True)
class SinisaCollection:
    catalog_file: Path
    package_files: tuple[Path, ...]
    collected_at: datetime


def validate_official_package(content: bytes, suffix: str) -> None:
    """Recusa páginas de erro e arquivos com assinatura incompatível."""
    signatures = {
        ".xlsx": (b"PK\x03\x04",),
        ".zip": (b"PK\x03\x04",),
        ".rar": (b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00"),
    }
    expected = signatures.get(suffix.lower())
    if expected is None:
        raise ValueError(f"Formato SINISA não permitido: {suffix}")
    if not any(content.startswith(signature) for signature in expected):
        raise ValueError(f"Conteúdo SINISA incompatível com o formato {suffix}")


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=8), reraise=True)
def _get_complete(client: httpx.Client, url: str) -> httpx.Response:
    """Repete downloads interrompidos pelo servidor antes da persistência."""
    response = client.get(url)
    validate_response(response)
    expected_length = response.headers.get("content-length")
    if (
        expected_length
        and not response.headers.get("content-encoding")
        and len(response.content) != int(expected_length)
    ):
        raise ValueError(
            f"Download incompleto: {len(response.content)} de {expected_length} bytes"
        )
    return response


def collect_sinisa(
    raw_directory: Path = Path("data/raw/saneamento/sinisa"),
) -> SinisaCollection:
    """Baixa catálogo e cinco módulos do SINISA 2024, referência 2023."""
    collected_at = datetime.now().astimezone()
    timestamp = collected_at.strftime("%Y%m%dT%H%M%S%z")
    raw_directory.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=120, follow_redirects=True) as client:
        catalog = _get_complete(client, RESULTS_URL)
        catalog_file = raw_directory / f"sinisa_resultados_{timestamp}.html"
        catalog_file.write_bytes(catalog.content)

        package_files = []
        for module, url in OFFICIAL_PACKAGES.items():
            response = _get_complete(client, url)
            suffix = Path(url).suffix.lower()
            validate_official_package(response.content, suffix)
            destination = raw_directory / f"sinisa_{module}_ref2023_{timestamp}{suffix}"
            if destination.exists():
                raise FileExistsError(f"Arquivo bruto já existe: {destination}")
            destination.write_bytes(response.content)
            package_files.append(destination)
            _record_collection(
                module, url, destination, response.content, response.status_code, collected_at
            )
    return SinisaCollection(catalog_file, tuple(package_files), collected_at)


def _record_collection(
    module: str,
    url: str,
    path: Path,
    content: bytes,
    status_code: int,
    collected_at: datetime,
) -> None:
    append_collection_metadata(
        {
            "id_coleta": f"sinisa_{module}_2023_{collected_at:%Y%m%dT%H%M%S%z}",
            "fonte": "SINISA/Ministério das Cidades",
            "sistema": "SINISA",
            "descricao_base": f"Informações e indicadores — {module}",
            "url_origem": RESULTS_URL,
            "endpoint": url,
            "metodo_http": "GET",
            "arquivo_bruto": str(path),
            "formato_arquivo": path.suffix.lstrip("."),
            "data_referencia_inicial": REFERENCE_YEAR,
            "data_referencia_final": REFERENCE_YEAR,
            "data_hora_coleta": collected_at.isoformat(),
            "parametros_requisicao": {},
            "filtros_selecionados": {},
            "opcoes_selecionadas": {"modulo": module},
            "codigo_http": status_code,
            "status_coleta": "sucesso",
            "quantidade_registros": "",
            "hash_sha256": sha256_bytes(content),
            "versao_coletor": "0.1.0",
            "observacoes": (
                "Produto SINISA 2024 com ano de referência 2023; pacote oficial "
                "preservado sem transformação."
            ),
        }
    )


class SinisaCollector(Collector):
    """Implementação do contrato comum de coletores."""

    def collect(self, request: CollectionRequest) -> list[Path]:
        result = collect_sinisa(request.output_directory)
        return [result.catalog_file, *result.package_files]
