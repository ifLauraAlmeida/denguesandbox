import pandas as pd

from dengue_rj.processors.sanitation_harmonization import (
    PRIORITY_COMPARISONS,
    build_priority_harmonization,
)


def test_priority_comparisons_cover_six_unique_indicators():
    table = pd.DataFrame(PRIORITY_COMPARISONS)
    assert len(table) == 6
    assert table["codigo_snis"].is_unique
    assert set(table["codigo_snis"]) == {
        "IN015",
        "IN016",
        "IN046",
        "IN049",
        "IN055",
        "IN056",
    }


def test_build_priority_harmonization_writes_auditable_table(tmp_path):
    output = build_priority_harmonization(tmp_path / "harmonizacao.csv")
    table = pd.read_csv(output)
    assert len(table) == 6
    assert table["url_glossario_snis"].str.startswith("https://").all()
    assert table["url_glossario_sinisa"].str.startswith("https://").all()
