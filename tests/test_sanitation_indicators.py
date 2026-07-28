from pathlib import Path

import pandas as pd

from dengue_rj.processors.sanitation_indicators import _inventory_snis_long


def test_inventory_snis_long_versions_metadata_changes(tmp_path: Path):
    source = pd.DataFrame(
        [
            {
                "codigo_indicador": "IN001",
                "nome_indicador": "Cobertura",
                "unidade": "%",
                "familia_indicador": "Gerais",
                "formula": "A/B",
                "ano": "2020",
            },
            {
                "codigo_indicador": "IN001",
                "nome_indicador": "Cobertura",
                "unidade": "%",
                "familia_indicador": "Gerais",
                "formula": "A/B",
                "ano": "2021",
            },
            {
                "codigo_indicador": "IN001",
                "nome_indicador": "Cobertura revisada",
                "unidade": "percentual",
                "familia_indicador": "Gerais",
                "formula": "A/B",
                "ano": "2022",
            },
        ]
    )
    path = tmp_path / "snis.csv"
    source.to_csv(path, index=False)

    result = _inventory_snis_long(path, "aguas_pluviais")

    assert len(result) == 2
    assert set(result["ano_referencia_inicial"]) == {"2020", "2022"}
    assert set(result["ano_referencia_final"]) == {"2021", "2022"}
