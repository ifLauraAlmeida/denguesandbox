"""Primitivas HTTP defensivas usadas pelos coletores."""

from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from dengue_rj.utils.hashing import sha256_bytes


def validate_response(response: httpx.Response) -> None:
    if response.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"Resposta HTTP inválida: {response.status_code}",
            request=response.request if response.has_request else httpx.Request("GET", "https://invalid.local"),
            response=response,
        )
    content_type = response.headers.get("content-type", "").lower()
    prefix = response.content[:1000].lower()
    html_error = b"<html" in prefix and any(token in prefix for token in (b"erro", b"error", b"indispon"))
    if html_error:
        raise ValueError("Fonte retornou página HTML de erro, possivelmente com HTTP 200")
    if not response.content:
        raise ValueError(f"Resposta vazia; content-type={content_type!r}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def download(url: str, destination: Path) -> tuple[Path, str]:
    """Baixa sem sobrescrever e retorna caminho e SHA-256."""
    if destination.exists():
        raise FileExistsError(f"Arquivo bruto já existe: {destination}")
    response = httpx.get(url, timeout=60, follow_redirects=True)
    validate_response(response)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination, sha256_bytes(response.content)
