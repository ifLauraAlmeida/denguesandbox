from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from dengue_rj.collectors.sinan_collector import _validate_zip
from dengue_rj.processors.sinan_dengue import SAFE_COLUMNS, process_sinan_residence


def test_process_sinan_filters_strictly_by_residence(tmp_path: Path):
    dimension_file = tmp_path / "municipalities.csv"
    pd.DataFrame(
        {"codigo_ibge_municipio": ["3300100", "3304557"]}
    ).to_csv(dimension_file, index=False)
    rows = []
    for residence, notification in (
        ("330010", "355030"),
        ("330455", "355030"),
        ("355030", "330455"),
    ):
        row = {column: "" for column in SAFE_COLUMNS}
        row.update(
            {
                "ID_MN_RESI": residence,
                "ID_MUNICIP": notification,
                "DT_NOTIFIC": "20200102",
                "DT_SIN_PRI": "20200101",
                "CLASSI_FIN": "10",
            }
        )
        rows.append(row)
    archive_file = tmp_path / "DENGBR20.csv.zip"
    with ZipFile(archive_file, "w", ZIP_DEFLATED) as archive:
        archive.writestr("DENGBR20.csv", pd.DataFrame(rows).to_csv(index=False))

    result = process_sinan_residence(
        archive_file,
        2020,
        dimension_file,
        tmp_path / "processed",
    )
    output = pd.read_csv(result.output_file, dtype=str)
    assert result.records == 2
    assert set(output["codigo_ibge_municipio"]) == {"3300100", "3304557"}
    assert set(output["CRITERIO_TERRITORIAL"]) == {"municipio_residencia"}
    assert "ID_MUNICIP" not in output


def test_validate_sinan_zip_rejects_non_zip(tmp_path: Path):
    invalid = tmp_path / "invalid.zip"
    invalid.write_text("<html>erro</html>", encoding="utf-8")
    with pytest.raises(ValueError, match="ZIP válido"):
        _validate_zip(invalid)
