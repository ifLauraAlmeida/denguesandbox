"""Padronização textual auxiliar; a chave final continua sendo o código IBGE."""

import re
import unicodedata

import pandas as pd

HEALTH_REGIONS = {
    "33001": ("Baía de Ilha Grande", ("Angra dos Reis", "Mangaratiba", "Paraty")),
    "33002": (
        "Baixada Litorânea",
        (
            "Araruama", "Armação dos Búzios", "Arraial do Cabo", "Cabo Frio",
            "Casimiro de Abreu", "Iguaba Grande", "Rio das Ostras",
            "São Pedro da Aldeia", "Saquarema",
        ),
    ),
    "33003": (
        "Centro Sul",
        (
            "Areal", "Comendador Levy Gasparian", "Engenheiro Paulo de Frontin",
            "Mendes", "Miguel Pereira", "Paracambi", "Paraíba do Sul",
            "Paty do Alferes", "Sapucaia", "Três Rios", "Vassouras",
        ),
    ),
    "33004": (
        "Médio Paraíba",
        (
            "Barra do Piraí", "Barra Mansa", "Itatiaia", "Pinheiral", "Piraí",
            "Porto Real", "Quatis", "Resende", "Rio Claro", "Rio das Flores",
            "Valença", "Volta Redonda",
        ),
    ),
    "33005": (
        "Metropolitana I",
        (
            "Belford Roxo", "Duque de Caxias", "Itaguaí", "Japeri", "Magé",
            "Mesquita", "Nilópolis", "Nova Iguaçu", "Queimados", "Rio de Janeiro",
            "São João de Meriti", "Seropédica",
        ),
    ),
    "33006": (
        "Metropolitana II",
        ("Itaboraí", "Maricá", "Niterói", "Rio Bonito", "São Gonçalo", "Silva Jardim", "Tanguá"),
    ),
    "33007": (
        "Noroeste",
        (
            "Aperibé", "Bom Jesus do Itabapoana", "Cambuci", "Cardoso Moreira",
            "Italva", "Itaocara", "Itaperuna", "Laje do Muriaé", "Miracema",
            "Natividade", "Porciúncula", "Santo Antônio de Pádua",
            "São José de Ubá", "Varre-Sai",
        ),
    ),
    "33008": (
        "Norte",
        (
            "Campos dos Goytacazes", "Carapebus", "Conceição de Macabu", "Macaé",
            "Quissamã", "São Fidélis", "São Francisco de Itabapoana", "São João da Barra",
        ),
    ),
    "33009": (
        "Serrana",
        (
            "Bom Jardim", "Cachoeiras de Macacu", "Cantagalo", "Carmo", "Cordeiro",
            "Duas Barras", "Guapimirim", "Macuco", "Nova Friburgo", "Petrópolis",
            "Santa Maria Madalena", "São José do Vale do Rio Preto",
            "São Sebastião do Alto", "Sumidouro", "Teresópolis", "Trajano de Moraes",
        ),
    ),
}


def normalize_municipality_name(value: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"Nome municipal vazio; recebido {value!r}")
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_name = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_name.strip()).upper()


def validate_ibge_municipality_code(value: str) -> str:
    code = str(value).strip()
    if len(code) != 7 or not code.isdigit() or not code.startswith("33"):
        raise ValueError(f"Código IBGE municipal do RJ deve ter 7 dígitos e iniciar por 33: {value!r}")
    return code


def health_region_lookup() -> dict[str, tuple[str, str]]:
    """Cria relação normalizada município → (código, região) da SES-RJ."""
    lookup: dict[str, tuple[str, str]] = {}
    for code, (region, municipalities) in HEALTH_REGIONS.items():
        for municipality in municipalities:
            normalized = normalize_municipality_name(municipality)
            if normalized in lookup:
                raise ValueError(f"Município duplicado na fonte regional: {municipality}")
            lookup[normalized] = (code, region)
    if len(lookup) != 92:
        raise ValueError(f"Esperados 92 municípios nas regiões; recebido {len(lookup)}")
    return lookup


def build_municipality_dimension(records: list[dict]) -> pd.DataFrame:
    """Valida resposta IBGE e a combina com regiões oficiais da SES-RJ."""
    lookup = health_region_lookup()
    rows = []
    for record in records:
        code = validate_ibge_municipality_code(str(record.get("id", "")))
        name = str(record.get("nome", "")).strip()
        normalized = normalize_municipality_name(name)
        if normalized not in lookup:
            raise ValueError(f"Município do IBGE ausente na regionalização SES-RJ: {name}")
        region_code, region = lookup[normalized]
        rows.append((code, name, normalized, "RJ", "33", region_code, region))
    frame = pd.DataFrame(
        rows,
        columns=[
            "codigo_ibge_municipio", "nome_municipio", "nome_municipio_normalizado",
            "uf", "codigo_uf", "codigo_regiao_saude", "regiao_saude",
        ],
    ).sort_values("codigo_ibge_municipio")
    if len(frame) != 92 or frame["codigo_ibge_municipio"].nunique() != 92:
        raise ValueError(f"IBGE deve retornar 92 municípios únicos do RJ; recebido {len(frame)}")
    return frame.reset_index(drop=True)
