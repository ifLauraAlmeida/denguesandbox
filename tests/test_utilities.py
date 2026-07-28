from pathlib import Path

import httpx
import pytest

from dengue_rj.collectors.http import validate_response
from dengue_rj.processors.territory import (
    HEALTH_REGIONS,
    health_region_lookup,
    normalize_municipality_name,
    validate_ibge_municipality_code,
)
from dengue_rj.utils.hashing import sha256_bytes, sha256_file


def test_hash_bytes_and_file_match(tmp_path: Path):
    path = tmp_path / "sample"
    path.write_bytes(b"dengue")
    assert sha256_file(path) == sha256_bytes(b"dengue")


def test_territory_normalization_and_code():
    assert normalize_municipality_name("  São   Gonçalo ") == "SAO GONCALO"
    assert validate_ibge_municipality_code("3304557") == "3304557"
    with pytest.raises(ValueError):
        validate_ibge_municipality_code("123")


def test_health_regions_cover_92_unique_municipalities():
    assert len(HEALTH_REGIONS) == 9
    assert len(health_region_lookup()) == 92


def test_html_error_with_status_200_is_rejected():
    response = httpx.Response(200, content=b"<html>Erro: indisponivel</html>")
    with pytest.raises(ValueError):
        validate_response(response)
