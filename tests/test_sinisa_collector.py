import pytest

from dengue_rj.collectors.sinisa_collector import validate_official_package


@pytest.mark.parametrize(
    ("content", "suffix"),
    [
        (b"PK\x03\x04conteudo", ".xlsx"),
        (b"PK\x03\x04conteudo", ".zip"),
        (b"Rar!\x1a\x07\x00conteudo", ".rar"),
        (b"Rar!\x1a\x07\x01\x00conteudo", ".rar"),
    ],
)
def test_validate_official_package_accepts_expected_signatures(content, suffix):
    validate_official_package(content, suffix)


def test_validate_official_package_rejects_html_disguised_as_archive():
    with pytest.raises(ValueError, match="incompatível"):
        validate_official_package(b"<html>erro</html>", ".zip")
