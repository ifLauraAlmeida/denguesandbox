import pytest

from dengue_rj.collectors.ripsa_collector import (
    build_population_payload,
    extract_csv_url,
)

FORM = b"""
<form>
<select name="Linha"><option value="line">Munic\xc3\xadpio com c\xc3\xb3digo</option></select>
<select name="Coluna"><option value="column">Ano</option></select>
<select name="Incremento"><option value="measure">Popula\xc3\xa7\xc3\xa3o estimada</option></select>
<select name="PAno">
<option value="2023|2023|3">2023</option>
<option value="2024|2024|4">2024</option>
</select>
</form>
"""


def test_payload_uses_values_discovered_in_form():
    payload = build_population_payload(FORM, (2023, 2024))
    assert payload["Linha"] == "line"
    assert payload["Coluna"] == "column"
    assert payload["Incremento"] == "measure"
    assert payload["PAno"] == ["2023|2023|3", "2024|2024|4"]


def test_result_requires_exactly_one_csv_link():
    content = b'<a href="csv/result.csv">CSV</a>'
    assert extract_csv_url(content).endswith("/csv/result.csv")
    with pytest.raises(ValueError, match="um link CSV"):
        extract_csv_url(b"<html>sem exportacao</html>")
