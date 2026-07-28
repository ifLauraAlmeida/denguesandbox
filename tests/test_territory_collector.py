import json

import pytest

from dengue_rj.collectors.territory_collector import parse_ibge_municipalities


def test_ibge_payload_must_be_a_list():
    with pytest.raises(TypeError, match="lista"):
        parse_ibge_municipalities(json.dumps({"id": 33}).encode())


def test_ibge_payload_must_be_valid_json():
    with pytest.raises(ValueError, match="JSON válido"):
        parse_ibge_municipalities(b"<html>erro</html>")
