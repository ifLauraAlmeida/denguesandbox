from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from dengue_rj.analysis.liraa_temporal import _calculate_liraa_associations
from dengue_rj.collectors.liraa_collector import _validate_liraa_zip
from dengue_rj.processors.liraa import process_liraa


def test_process_liraa_preserves_justification_and_reconciles_codes(tmp_path: Path):
    dimension_file = tmp_path / "municipalities.csv"
    pd.DataFrame(
        {"codigo_ibge_municipio": ["3300100", "3304557"]}
    ).to_csv(dimension_file, index=False)
    table = pd.DataFrame([[None] * 28 for _ in range(4)])
    table.iloc[0, 0] = "LIRAa/LIA"
    table.iloc[1, 0] = "IBGE"
    table.iloc[2, :6] = [
        "330010",
        "Angra dos Reis",
        "RJ",
        "01/01/2024 a 07/01/2024",
        1.2,
        1.4,
    ]
    table.iloc[3, :6] = [
        "330455",
        "Rio de Janeiro",
        "RJ",
        "Ofício com justificativa",
        None,
        None,
    ]
    workbook = BytesIO()
    table.to_excel(workbook, index=False, header=False)
    raw_directory = tmp_path / "raw"
    raw_directory.mkdir()
    archive_file = raw_directory / "LIRAa_2024.zip"
    with ZipFile(archive_file, "w", ZIP_DEFLATED) as archive:
        archive.writestr("LIRAa_2024_01 JAN.xlsx", workbook.getvalue())

    result = process_liraa(
        raw_directory,
        dimension_file,
        tmp_path / "processed",
    )
    output = pd.read_csv(result.output_file, dtype={"codigo_ibge_municipio": str})
    assert result.records == 2
    assert set(output["codigo_ibge_municipio"]) == {"3300100", "3304557"}
    assert set(output["status_levantamento"]) == {"observado", "justificativa"}
    assert output.loc[
        output["status_levantamento"].eq("justificativa"), "iip_aedes_aegypti"
    ].isna().all()


def test_validate_liraa_zip_rejects_non_zip(tmp_path: Path):
    invalid = tmp_path / "invalid.zip"
    invalid.write_text("<html>erro</html>", encoding="utf-8")
    with pytest.raises(ValueError, match="ZIP válido"):
        _validate_liraa_zip(invalid)


def test_liraa_associations_preserve_lags_and_outlier_rule():
    panel = pd.DataFrame(
        {
            "iip_aedes_aegypti": range(12),
            "ib_aedes_aegypti": [*range(11), 204.6],
            "flag_outlier_ib_maior_100": [False] * 11 + [True],
            **{
                f"incidencia_mes_{lag}_1_mil": range(12)
                for lag in range(4)
            },
        }
    )
    result = _calculate_liraa_associations(panel)
    assert len(result) == 12
    assert set(result["defasagem_meses"]) == {0, 1, 2, 3}
    conservative = result[
        (result["indicador_liraa"] == "ib_aedes_aegypti")
        & (result["regra_outlier"] == "exclui_ib_maior_100")
    ]
    assert set(conservative["observacoes"]) == {11}
