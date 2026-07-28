"""Coleta municipal do SNIS Série Histórica para água e esgoto."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
import pandas as pd

from dengue_rj.collectors.http import validate_response
from dengue_rj.metadata.writer import append_collection_metadata
from dengue_rj.utils.hashing import sha256_bytes

BASE_URL = "https://app4.cidades.gov.br/serieHistorica/"
GRID_URL = "https://app4.cidades.gov.br/serieHistorica/agregado/getGridData"
YEARS = (2020, 2021, 2022)
PAGE_SIZE = 15

GLOSSARY_IDS = (
    "38525", "38550", "39134", "38723", "39392", "38248", "38205", "38583",
    "39071", "39138", "38535", "38451", "38236", "38176", "38177", "38936",
    "39011", "38467", "38210", "38194", "39197", "38214", "38235", "38209",
    "39171", "38750", "38818", "38744", "38318", "38195",
)

GRID_COLUMNS = (
    "codigo_municipio_snis", "nome_municipio_origem", "uf", "ano",
    "codigo_prestador", "nome_prestador", "sigla_prestador", "abrangencia",
    "tipo_servico", "natureza_juridica", "IN001", "IN009", "IN010", "IN011",
    "IN013", "IN014", "IN015", "IN016", "IN017", "IN020", "IN021", "IN022",
    "IN023", "IN024", "IN025", "IN028", "IN043", "IN044", "IN046", "IN047",
    "IN049", "IN050", "IN051", "IN052", "IN053", "IN055", "IN056", "IN057",
    "IN058", "IN059",
)

PRIORITY_INDICATORS = {
    "IN015": ("Índice de coleta de esgoto", "percentual"),
    "IN016": ("Índice de tratamento de esgoto", "percentual"),
    "IN046": ("Índice de esgoto tratado referido à água consumida", "percentual"),
    "IN049": ("Índice de perdas na distribuição", "percentual"),
    "IN055": ("Índice de atendimento total de água", "percentual"),
    "IN056": (
        "Índice de atendimento total de esgoto referido aos municípios atendidos com água",
        "percentual",
    ),
}


@dataclass(frozen=True)
class SnisHistoricalCollection:
    raw_files: tuple[Path, ...]
    processed_file: Path
    source_records: int
    processed_records: int
    collected_at: datetime


def build_grid_body(page: int) -> str:
    """Monta a dupla codificação usada pelo formulário legado."""
    filters: list[tuple[str, str]] = []
    filters.extend(("ShAgregados[ano_ref][]", str(year)) for year in reversed(YEARS))
    filters.extend(("ShAgregados[cod_abr][]", value) for value in ("1", "2", "3"))
    filters.extend(("ShAgregados[cod_srv][]", value) for value in ("1", "2", "3"))
    filters.extend(
        ("ShAgregados[cod_nat][]", value)
        for value in ("1", "2", "8", "6", "3", "7", "5", "4")
    )
    filters.extend(
        [
            ("ShAgregados[cod_reg_geo][]", "3"),
            ("ShAgregados[sgl_est][]", "RJ"),
            ("ShAgregados[cod_fam_info][]", "9"),
            ("ShAgregados[cod_fam_info][]", "10"),
        ]
    )
    filters.extend(("ShAgregados[fk_glossario][]", value) for value in GLOSSARY_IDS)
    return urlencode(
        {
            "data": urlencode(filters),
            "_search": "false",
            "nd": str(int(datetime.now(UTC).timestamp() * 1000)),
            "rows": str(PAGE_SIZE),
            "page": str(page),
            "sidx": "a.sgl_est,a.nom_mun,a.ano_ref",
            "sord": "desc",
        }
    )


def parse_grid_pages(
    pages: list[dict[str, object]], dimension: pd.DataFrame
) -> pd.DataFrame:
    """Converte páginas jqGrid em tabela longa sem agregar prestadores."""
    rows = []
    for page in pages:
        if page.get("status") != "ok":
            raise ValueError(f"SNIS retornou status inválido: {page.get('status')}")
        rows.extend(row["cell"] for row in page.get("rows", []))
    wide = pd.DataFrame(rows, columns=GRID_COLUMNS)
    if wide.empty:
        raise ValueError("SNIS Série Histórica retornou zero registros")
    wide["ano"] = pd.to_numeric(wide["ano"], errors="raise").astype(int)
    if set(wide["ano"]) != set(YEARS):
        raise ValueError(f"Anos SNIS divergentes: {sorted(wide['ano'].unique())}")

    code_map = {
        str(code)[:6]: str(code)
        for code in dimension["codigo_ibge_municipio"].astype(str)
    }
    wide["codigo_ibge_municipio"] = wide["codigo_municipio_snis"].map(code_map)
    if wide["codigo_ibge_municipio"].isna().any():
        unknown = sorted(wide.loc[wide["codigo_ibge_municipio"].isna(), "codigo_municipio_snis"].unique())
        raise ValueError(f"Códigos SNIS sem correspondência IBGE: {unknown}")

    identifiers = [
        "codigo_ibge_municipio", "codigo_municipio_snis", "nome_municipio_origem",
        "uf", "ano", "codigo_prestador", "nome_prestador", "sigla_prestador",
        "abrangencia", "tipo_servico", "natureza_juridica",
    ]
    long = wide.melt(
        id_vars=identifiers,
        value_vars=list(PRIORITY_INDICATORS),
        var_name="codigo_indicador",
        value_name="valor",
    )
    long["valor"] = pd.to_numeric(long["valor"], errors="coerce")
    long["nome_indicador"] = long["codigo_indicador"].map(
        {code: definition[0] for code, definition in PRIORITY_INDICATORS.items()}
    )
    long["unidade"] = long["codigo_indicador"].map(
        {code: definition[1] for code, definition in PRIORITY_INDICATORS.items()}
    )
    long["fonte"] = "SNIS Série Histórica/Ministério das Cidades"
    long["nivel_origem"] = "prestador-municipio-ano"
    return long.sort_values(
        ["codigo_ibge_municipio", "ano", "codigo_prestador", "codigo_indicador"]
    ).reset_index(drop=True)


def collect_snis_historical(
    raw_directory: Path = Path("data/raw/saneamento/snis_serie_historica"),
    processed_file: Path = Path(
        "data/processed/saneamento/snis_agua_esgoto_indicadores_2020_2022.csv"
    ),
    dimension_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
) -> SnisHistoricalCollection:
    """Coleta todas as páginas da consulta municipal capturada."""
    dimension = pd.read_csv(dimension_file, dtype=str)
    collected_at = datetime.now().astimezone()
    timestamp = collected_at.strftime("%Y%m%dT%H%M%S%z")
    raw_directory.mkdir(parents=True, exist_ok=True)
    raw_files = []
    parsed_pages = []

    with httpx.Client(timeout=120, follow_redirects=True) as client:
        home = client.get(BASE_URL)
        validate_response(home)
        home_file = raw_directory / f"snis_serie_historica_{timestamp}.html"
        home_file.write_bytes(home.content)
        raw_files.append(home_file)

        page = 1
        total_pages = 1
        while page <= total_pages:
            response = client.post(
                GRID_URL,
                content=build_grid_body(page),
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": BASE_URL,
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            validate_response(response)
            payload = response.json()
            if payload.get("status") != "ok":
                raise ValueError(f"Erro no endpoint SNIS: {payload.get('msg')}")
            total_pages = int(payload["total"])
            page_file = raw_directory / f"snis_ae_rj_2020_2022_p{page:02d}_{timestamp}.json"
            page_file.write_bytes(response.content)
            raw_files.append(page_file)
            parsed_pages.append(payload)
            page += 1

    processed = parse_grid_pages(parsed_pages, dimension)
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(processed_file, index=False)
    source_records = int(parsed_pages[0]["records"])
    _record_collection(raw_files[1:], source_records, collected_at)
    return SnisHistoricalCollection(
        tuple(raw_files), processed_file, source_records, len(processed), collected_at
    )


def _record_collection(
    page_files: list[Path], records: int, collected_at: datetime
) -> None:
    hashes = {path.name: sha256_bytes(path.read_bytes()) for path in page_files}
    append_collection_metadata(
        {
            "id_coleta": f"snis_ae_rj_2020_2022_{collected_at:%Y%m%dT%H%M%S%z}",
            "fonte": "SNIS/Ministério das Cidades",
            "sistema": "SNIS Série Histórica",
            "descricao_base": "Indicadores operacionais de água e esgoto por prestador e município",
            "url_origem": BASE_URL,
            "endpoint": GRID_URL,
            "metodo_http": "POST",
            "arquivo_bruto": str(page_files[0].parent),
            "formato_arquivo": "json",
            "data_referencia_inicial": min(YEARS),
            "data_referencia_final": max(YEARS),
            "data_hora_coleta": collected_at.isoformat(),
            "parametros_requisicao": {
                "anos": list(YEARS), "uf": "RJ", "familias": [9, 10],
                "paginas": len(page_files), "linhas_por_pagina": PAGE_SIZE,
            },
            "filtros_selecionados": {
                "abrangencias": [1, 2, 3], "servicos": [1, 2, 3],
                "naturezas_juridicas": [1, 2, 8, 6, 3, 7, 5, 4],
            },
            "opcoes_selecionadas": {
                "familias": ["Indicadores operacionais - água", "Indicadores operacionais - esgotos"]
            },
            "codigo_http": 200,
            "status_coleta": "sucesso",
            "quantidade_registros": records,
            "hash_sha256": hashes,
            "versao_coletor": "0.1.0",
            "observacoes": (
                "JSON paginado preservado; valores mantidos no nível prestador-município-ano."
            ),
        }
    )
