import pandas as pd

from dengue_rj.processors.sinisa_municipal import (
    _indicator_frame,
    _municipality_identity,
)


def test_indicator_frame_preserves_non_numeric_source_status():
    index = pd.Index([10, 11, 12])
    municipality = pd.DataFrame(
        {
            "codigo_ibge_municipio": ["3304557", "3301702", "3303302"],
            "codigo_municipio_origem": ["3304557", "3301702", "3303302"],
            "nome_municipio_origem": ["Rio de Janeiro", "Duque de Caxias", "Niterói"],
            "uf": ["RJ", "RJ", "RJ"],
        },
        index=index,
    )
    values = pd.Series([42.5, "Não Calc.- Div/0", None], index=index)

    result = _indicator_frame(
        municipality=municipality,
        values=values,
        component="aguas_pluviais",
        family="Gestão de riscos",
        code="IGR0001",
        name="Risco",
        unit="percentual",
        formula="A/B",
    )

    assert result["valor"].notna().sum() == 1
    assert result["status_valor"].tolist() == [
        "observado",
        "Não Calc.- Div/0",
        "ausente",
    ]


def test_municipality_identity_rejects_code_outside_dimension():
    data = pd.DataFrame([["9999999", "Município inexistente"]])
    dimension = pd.DataFrame({"codigo_ibge_municipio": ["3304557"]})

    try:
        _municipality_identity(data, 0, 1, dimension, "teste")
    except ValueError as error:
        assert "9999999" in str(error)
    else:
        raise AssertionError("Código fora da dimensão deveria ser rejeitado")
