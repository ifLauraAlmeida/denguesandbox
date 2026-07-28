from pathlib import Path
from zipfile import ZipFile

import pytest

from dengue_rj.collectors.snis_solid_waste_collector import validate_zip


def test_validate_zip_accepts_integral_archive(tmp_path: Path):
    archive = tmp_path / "valid.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("table.csv", "a,b\n1,2\n")
    validate_zip(archive)


def test_validate_zip_rejects_invalid_archive(tmp_path: Path):
    archive = tmp_path / "invalid.zip"
    archive.write_bytes(b"<html>erro</html>")
    with pytest.raises(ValueError, match="inválido"):
        validate_zip(archive)
