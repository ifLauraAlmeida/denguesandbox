import pandas as pd

from dengue_rj.processors.sinisa_crosswalk import (
    _classify_correspondence,
    _normalize_text,
)


def test_normalize_text_flattens_pdf_line_breaks():
    assert _normalize_text("Volume de água\nconsumido") == "Volume de água consumido"


def test_classify_correspondence_distinguishes_direct_composed_and_missing():
    assert (
        _classify_correspondence(
            pd.Series({"expressao_informacao_sinisa": "GTA0003"})
        )
        == "correspondencia_direta"
    )
    assert (
        _classify_correspondence(
            pd.Series({"expressao_informacao_sinisa": "GTA0001 + GTA0002"})
        )
        == "composicao_ou_ajuste"
    )
    assert (
        _classify_correspondence(
            pd.Series({"expressao_informacao_sinisa": "Não identificado"})
        )
        == "sem_correspondencia_identificada"
    )
