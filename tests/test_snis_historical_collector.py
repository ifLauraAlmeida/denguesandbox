import pandas as pd

from dengue_rj.collectors.snis_historical_collector import (
    GRID_COLUMNS,
    build_grid_body,
    parse_grid_pages,
)


def test_grid_body_contains_expected_filters():
    body = build_grid_body(2)
    assert "page=2" in body
    assert "rows=15" in body
    assert "2022" in body
    assert "RJ" in body


def test_parse_grid_pages_preserves_provider_granularity():
    cells = [None] * len(GRID_COLUMNS)
    values = {
        "codigo_municipio_snis": "330010",
        "nome_municipio_origem": "Angra dos Reis",
        "uf": "RJ",
        "ano": "2020",
        "codigo_prestador": "33001011",
        "nome_prestador": "SAAE",
        "sigla_prestador": "SAAE",
        "abrangencia": "Local",
        "tipo_servico": "Água e Esgoto",
        "natureza_juridica": "Autarquia",
        "IN015": "80.00",
        "IN016": "50.00",
    }
    for column, value in values.items():
        cells[GRID_COLUMNS.index(column)] = value
    rows = []
    for year in (2020, 2021, 2022):
        year_cells = cells.copy()
        year_cells[GRID_COLUMNS.index("ano")] = str(year)
        rows.append({"cell": year_cells})
    pages = [{"status": "ok", "rows": rows}]
    dimension = pd.DataFrame({"codigo_ibge_municipio": ["3300100"]})
    result = parse_grid_pages(pages, dimension)
    assert len(result) == 18
    assert result["codigo_prestador"].nunique() == 1
    assert result.loc[result["codigo_indicador"] == "IN015", "valor"].iloc[0] == 80
