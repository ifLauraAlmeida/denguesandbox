"""Coleta da população residente RIPSA no TabNet da SES-RJ."""

import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from dengue_rj.collectors.base import CollectionRequest, Collector
from dengue_rj.collectors.http import validate_response
from dengue_rj.metadata.writer import append_collection_metadata
from dengue_rj.utils.hashing import sha256_bytes

FORM_URL = (
    "https://sistemas.saude.rj.gov.br/tabnetbd/"
    "dhx.exe?populacao/pop_populacao_ripsa2024.def"
)
QUERY_URL = "https://sistemas.saude.rj.gov.br/tabnetbd/webtabx.exe"
FORM_DEFINITION = "populacao/pop_populacao_ripsa2024.def"


@dataclass(frozen=True)
class DemographyCollection:
    raw_files: tuple[Path, ...]
    source_csv_file: Path
    processed_file: Path
    records: int
    collected_at: datetime


def _option_value(soup: BeautifulSoup, field: str, label: str) -> str:
    select = soup.find("select", attrs={"name": field})
    if select is None:
        raise ValueError(f"Campo TabNet ausente: {field}")
    for option in select.find_all("option"):
        if option.get_text(" ", strip=True) == label:
            return str(option["value"])
    raise ValueError(f"Opção TabNet ausente: {field}={label}")


def build_population_payload(
    form_content: bytes, years: tuple[int, ...]
) -> dict[str, str | list[str]]:
    """Monta o POST com opções descobertas no formulário oficial."""
    soup = BeautifulSoup(form_content, "lxml")
    return {
        "Linha": _option_value(soup, "Linha", "Município com código"),
        "Coluna": _option_value(soup, "Coluna", "Ano"),
        "Incremento": _option_value(soup, "Incremento", "População estimada"),
        "PAno": [_option_value(soup, "PAno", str(year)) for year in years],
        "SMunicípio": "TODAS_AS_CATEGORIAS__",
        "SRegião": "TODAS_AS_CATEGORIAS__",
        "SSexo": "TODAS_AS_CATEGORIAS__",
        "SFaixa": "TODAS_AS_CATEGORIAS__",
        "nomedef": FORM_DEFINITION,
        "grafico": "",
    }


def extract_csv_url(result_content: bytes) -> str:
    """Obtém o download CSV produzido pela própria resposta TabNet."""
    soup = BeautifulSoup(result_content, "lxml")
    links = [
        urljoin(QUERY_URL, str(link["href"]))
        for link in soup.find_all("a", href=True)
        if str(link["href"]).lower().endswith(".csv")
    ]
    if len(links) != 1:
        raise ValueError(f"Esperado um link CSV no resultado TabNet; recebido {len(links)}")
    return links[0]


def parse_population_csv(
    content: bytes, years: tuple[int, ...], dimension: pd.DataFrame
) -> pd.DataFrame:
    """Converte o CSV oficial largo em série longa com códigos IBGE."""
    source, source_encoding = _read_source_csv(content)
    if len(source.columns) < 2:
        raise ValueError(f"CSV RIPSA inválido; colunas recebidas: {list(source.columns)}")
    missing_years = set(map(str, years)).difference(source.columns)
    if missing_years:
        raise ValueError(f"Anos ausentes no CSV RIPSA: {sorted(missing_years)}")

    territorial = source.iloc[:, 0].str.strip()
    source_code = territorial.str.extract(r"^(\d{6})\s+", expand=False)
    names = territorial.str.replace(r"^\d{6}\s+", "", regex=True).str.strip()
    code_map = {
        str(code)[:6]: str(code) for code in dimension["codigo_ibge_municipio"].astype(str)
    }
    base = pd.DataFrame(
        {
            "codigo_ibge_municipio": source_code.map(code_map),
            "nome_municipio_origem": names,
        }
    ).dropna(subset=["codigo_ibge_municipio"])
    if len(base) != 92 or base["codigo_ibge_municipio"].nunique() != 92:
        raise ValueError(f"Esperados 92 municípios; recebidos {len(base)}")

    frames = []
    for year in years:
        frame = base.copy()
        frame["ano"] = year
        frame["populacao_residente"] = pd.to_numeric(
            source.loc[base.index, str(year)], errors="coerce"
        ).to_numpy()
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    frame["fonte"] = "RIPSA/SES-RJ"
    frame["codificacao_origem"] = source_encoding
    if frame["populacao_residente"].isna().any() or (
        frame["populacao_residente"] <= 0
    ).any():
        raise ValueError("População ausente ou não positiva")
    expected = 92 * len(years)
    if len(frame) != expected:
        raise ValueError(f"Esperados {expected} registros; recebidos {len(frame)}")
    return frame.sort_values(["ano", "codigo_ibge_municipio"]).reset_index(drop=True)


def _read_source_csv(content: bytes) -> tuple[pd.DataFrame, str]:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            frame = pd.read_csv(io.BytesIO(content), sep=";", dtype=str, encoding=encoding)
            return frame, encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV RIPSA não pôde ser decodificado como UTF-8 ou Latin-1")


def collect_population(
    years: tuple[int, ...] = (2020, 2021, 2022, 2023, 2024),
    raw_directory: Path = Path("data/raw/demografia"),
    source_csv_file: Path = Path(
        "data/processed/demografia/populacao_ripsa_tabnet_2020_2024.csv"
    ),
    processed_file: Path = Path("data/processed/demografia/populacao_ripsa_2020_2024.csv"),
    dimension_file: Path = Path("data/processed/demografia/dim_municipio.csv"),
) -> DemographyCollection:
    """Preserva o HTML bruto, o CSV oficial e gera a série municipal longa."""
    if not dimension_file.exists():
        raise FileNotFoundError(f"Dimensão municipal necessária: {dimension_file}")
    dimension = pd.read_csv(dimension_file, dtype=str)
    collected_at = datetime.now().astimezone()
    timestamp = collected_at.strftime("%Y%m%dT%H%M%S%z")
    raw_directory.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        form = client.get(FORM_URL)
        validate_response(form)
        form_file = raw_directory / f"ripsa_form_populacao_{timestamp}.html"
        form_file.write_bytes(form.content)

        payload = build_population_payload(form.content, years)
        result = client.post(
            QUERY_URL,
            content=urlencode(payload, doseq=True),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        validate_response(result)
        result_file = raw_directory / f"ripsa_populacao_2020_2024_{timestamp}.html"
        result_file.write_bytes(result.content)

        csv_response = client.get(extract_csv_url(result.content))
        validate_response(csv_response)

    source_csv_file.parent.mkdir(parents=True, exist_ok=True)
    source_csv_file.write_bytes(csv_response.content)
    processed = parse_population_csv(csv_response.content, years, dimension)
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(processed_file, index=False)
    _record_collection(years, result_file, result.content, collected_at)
    return DemographyCollection(
        (form_file, result_file),
        source_csv_file,
        processed_file,
        len(processed),
        collected_at,
    )


def _record_collection(
    years: tuple[int, ...], path: Path, content: bytes, collected_at: datetime
) -> None:
    append_collection_metadata(
        {
            "id_coleta": (
                f"ripsa_populacao_{min(years)}_{max(years)}_"
                f"{collected_at:%Y%m%dT%H%M%S%z}"
            ),
            "fonte": "RIPSA/SES-RJ",
            "sistema": "TabNet SES-RJ",
            "descricao_base": "População residente estimada por município",
            "url_origem": FORM_URL,
            "endpoint": QUERY_URL,
            "metodo_http": "POST",
            "arquivo_bruto": str(path),
            "formato_arquivo": "html",
            "data_referencia_inicial": min(years),
            "data_referencia_final": max(years),
            "data_hora_coleta": collected_at.isoformat(),
            "parametros_requisicao": {"anos": list(years)},
            "filtros_selecionados": {"municipio": "todas_as_categorias"},
            "opcoes_selecionadas": {
                "linha": "Município com código",
                "coluna": "Ano",
                "medida": "População estimada",
            },
            "codigo_http": 200,
            "status_coleta": "sucesso",
            "quantidade_registros": 92 * len(years),
            "hash_sha256": sha256_bytes(content),
            "versao_coletor": "0.3.0",
            "observacoes": (
                "HTML puro da resposta POST; o CSV oficial foi obtido pelo link "
                "'Salva como CSV' contido nesta resposta."
            ),
        }
    )


class RipsaCollector(Collector):
    """Compatibilidade com o contrato comum de coletores."""

    def collect(self, request: CollectionRequest) -> list[Path]:
        result = collect_population(request.years, request.output_directory)
        return list(result.raw_files)
