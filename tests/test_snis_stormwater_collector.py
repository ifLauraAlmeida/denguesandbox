from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from dengue_rj.collectors.snis_stormwater_collector import (
    _parse_indicator_archive,
)


def test_parse_indicator_archive_filters_rj_and_normalizes_to_long_format(
    tmp_path: Path,
):
    source = pd.DataFrame(
        [
            ["título", None, None, None, None, None, None, None],
            [None] * 8,
            [None] * 8,
            [None] * 8,
            [None] * 8,
            [None] * 8,
            ["MUNICÍPIO", None, None, None, None, None, None, "GERAIS"],
            ["Código IBGE", "Nome", "UF", "Região", "Capital", "Crítico", "Faixa", "Cobertura"],
            [None, None, None, None, None, None, None, "(IE024 / IE017) * 100"],
            [None, None, None, None, None, None, None, "%"],
            [None, None, None, None, None, None, None, "IN021"],
            [330455, "Rio de Janeiro", "RJ", "Sudeste", "Sim", "Não", "5", 42.5],
            [355030, "São Paulo", "SP", "Sudeste", "Sim", "Não", "5", 50.0],
        ]
    )
    workbook = BytesIO()
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        source.to_excel(writer, index=False, header=False)
    archive = tmp_path / "stormwater.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("Tabela de Indicadores_AP2022.xlsx", workbook.getvalue())
    dimension = pd.DataFrame(
        {"codigo_ibge_municipio": ["3304557"], "nome_municipio": ["Rio de Janeiro"]}
    )

    result = _parse_indicator_archive(archive, 2022, dimension)

    assert len(result) == 1
    assert result.loc[0, "codigo_ibge_municipio"] == "3304557"
    assert result.loc[0, "codigo_indicador"] == "IN021"
    assert result.loc[0, "valor"] == 42.5
