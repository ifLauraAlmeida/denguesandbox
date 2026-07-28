"""Decisões metodológicas para indicadores prioritários de água e esgoto."""

from pathlib import Path

import pandas as pd

PRIORITY_COMPARISONS = [
    {
        "componente": "abastecimento_agua",
        "codigo_snis": "IN055",
        "codigo_sinisa": "IAG0001",
        "formula_snis": "(AG001 / GE12a) * 100",
        "formula_sinisa": "((GTA0001 + GTA0002) / DFE0001) * 100",
        "classificacao_comparabilidade": "comparavel_direto",
        "justificativa": (
            "AG001 corresponde a GTA0001 + GTA0002; ambos usam população total "
            "residente como denominador."
        ),
        "pagina_snis": 16,
        "pagina_sinisa": 1,
    },
    {
        "componente": "abastecimento_agua",
        "codigo_snis": "IN049",
        "codigo_sinisa": "IAG2013",
        "formula_snis": (
            "((AG006 + AG018 - AG010 - AG024) / "
            "(AG006 + AG018 - AG024)) * 100"
        ),
        "formula_sinisa": (
            "((GTA1001 + GTA1009 - GTA1207 - GTA1211 - GTA1203) / "
            "(GTA1001 + GTA1009)) * 100"
        ),
        "classificacao_comparabilidade": "nao_comparavel_formula_alterada",
        "justificativa": (
            "O volume autorizado não faturado é subtraído do denominador SNIS, "
            "mas não do denominador SINISA."
        ),
        "pagina_snis": 14,
        "pagina_sinisa": 11,
    },
    {
        "componente": "esgotamento_sanitario",
        "codigo_snis": "IN015",
        "codigo_sinisa": "IES2002",
        "formula_snis": "(ES005 / (AG010 - AG019)) * 100",
        "formula_sinisa": "(GTE1002 / GTA1211) * 100",
        "classificacao_comparabilidade": "similar_com_ruptura_definicao",
        "justificativa": (
            "A fórmula é reconciliável pelo de-para, mas o próprio documento "
            "registra mudança no conceito de volume de esgoto coletado."
        ),
        "pagina_snis": 17,
        "pagina_sinisa": 8,
    },
    {
        "componente": "esgotamento_sanitario",
        "codigo_snis": "IN016",
        "codigo_sinisa": "IES2004",
        "formula_snis": (
            "((ES006 + ES014 + ES015) / (ES005 + ES013)) * 100"
        ),
        "formula_sinisa": (
            "((GTE1014 + GTE1015 + GTE1013) / (GTE1002 + GTE1009)) * 100"
        ),
        "classificacao_comparabilidade": "similar_com_ruptura_definicao",
        "justificativa": (
            "Os termos possuem correspondência estrutural, mas o denominador "
            "inclui o volume coletado cuja definição mudou no SINISA."
        ),
        "pagina_snis": 17,
        "pagina_sinisa": 9,
    },
    {
        "componente": "esgotamento_sanitario",
        "codigo_snis": "IN046",
        "codigo_sinisa": "IES2003",
        "formula_snis": "((ES006 + ES015) / (AG010 - AG019)) * 100",
        "formula_sinisa": "((GTE1014 + GTE1013) / GTA1211) * 100",
        "classificacao_comparabilidade": "comparavel_apenas_base_municipal",
        "justificativa": (
            "A equivalência AG010 - AG019 = GTA1211 é declarada válida apenas "
            "para a base municipal; agregações por prestador exigem cautela."
        ),
        "pagina_snis": 18,
        "pagina_sinisa": 9,
    },
    {
        "componente": "esgotamento_sanitario",
        "codigo_snis": "IN056",
        "codigo_sinisa": "IES0001",
        "formula_snis": "(ES001 / GE12a) * 100",
        "formula_sinisa": "((GTE0001 + GTE0002) / DFE0001) * 100",
        "classificacao_comparabilidade": "comparavel_direto",
        "justificativa": (
            "ES001 corresponde a GTE0001 + GTE0002; ambos usam população total "
            "residente como denominador."
        ),
        "pagina_snis": 18,
        "pagina_sinisa": 1,
    },
]

SNIS_GLOSSARY_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/snis/produtos-do-snis/diagnosticos/"
    "Glossario_Indicadores_AE2022.pdf"
)
SINISA_WATER_GLOSSARY_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/sinisa/resultados-sinisa/"
    "INDICADORES_SINISA_ABASTECIMENTO_DE_AGUA_2024_v2.pdf"
)
SINISA_SEWER_GLOSSARY_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "saneamento/sinisa/arquivos/"
    "INDICADORES_SINISA_ESGOTAMENTOSANITRIO_2024_V2.pdf"
)


def build_priority_harmonization(
    output_file: Path = Path(
        "data/processed/saneamento/"
        "comparabilidade_indicadores_agua_esgoto_snis_sinisa.csv"
    ),
) -> Path:
    """Materializa as decisões verificadas nos glossários oficiais."""
    result = pd.DataFrame(PRIORITY_COMPARISONS)
    result["url_glossario_snis"] = SNIS_GLOSSARY_URL
    result["url_glossario_sinisa"] = result["componente"].map(
        {
            "abastecimento_agua": SINISA_WATER_GLOSSARY_URL,
            "esgotamento_sanitario": SINISA_SEWER_GLOSSARY_URL,
        }
    )
    if result["codigo_snis"].duplicated().any():
        raise ValueError("Código SNIS duplicado na harmonização prioritária")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)
    return output_file
