"""Extração tabular da regra oficial de transição SNIS-SINISA-ACERTAR."""

import re
from pathlib import Path

import pandas as pd

SINISA_CODE_PATTERN = re.compile(r"\b[A-Z]{3}\d{4}\b")
COLUMNS = [
    "grupo",
    "codigo_informacao_snis",
    "detalhamento_referencia_snis",
    "descricao_informacao_snis",
    "expressao_informacao_sinisa",
    "descricao_informacao_sinisa",
    "comentarios",
]


def build_sinisa_crosswalk(
    raw_directory: Path = Path("data/raw/saneamento/sinisa_referencias"),
    output_file: Path = Path(
        "data/processed/saneamento/de_para_informacoes_snis_sinisa_acertar.csv"
    ),
) -> Path:
    """Extrai as tabelas do PDF, preservando expressões e comentários oficiais."""
    import fitz

    source_file = _latest(raw_directory, "*.pdf")
    document = fitz.open(source_file)
    records = []
    for page_number, page in enumerate(document, start=1):
        tables = page.find_tables().tables
        if len(tables) != 1:
            raise ValueError(
                f"Esperada uma tabela na página {page_number}; encontradas {len(tables)}"
            )
        rows = tables[0].extract()
        if page_number == 1:
            rows = rows[1:]
        for row in rows:
            if len(row) != len(COLUMNS):
                raise ValueError(
                    f"Linha com {len(row)} colunas na página {page_number}"
                )
            normalized = [_normalize_text(value) for value in row]
            if not normalized[1]:
                continue
            record = dict(zip(COLUMNS, normalized))
            record["pagina_origem"] = page_number
            records.append(record)
    result = pd.DataFrame(records)
    result["codigos_sinisa"] = result["expressao_informacao_sinisa"].map(
        lambda value: "|".join(dict.fromkeys(SINISA_CODE_PATTERN.findall(value)))
    )
    result["tipo_correspondencia"] = result.apply(_classify_correspondence, axis=1)
    result["possui_observacao_metodologica"] = result["comentarios"].ne("")
    result["arquivo_origem"] = str(source_file)
    if result["codigo_informacao_snis"].duplicated().any():
        duplicates = result.loc[
            result["codigo_informacao_snis"].duplicated(keep=False),
            "codigo_informacao_snis",
        ].unique()
        raise ValueError(f"Códigos SNIS duplicados no de-para: {duplicates.tolist()}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)
    return output_file


def _classify_correspondence(row: pd.Series) -> str:
    expression = row["expressao_informacao_sinisa"]
    if expression.casefold() == "não identificado":
        return "sem_correspondencia_identificada"
    codes = SINISA_CODE_PATTERN.findall(expression)
    if len(codes) > 1 or "+" in expression or " - " in expression:
        return "composicao_ou_ajuste"
    if len(codes) == 1:
        return "correspondencia_direta"
    return "revisao_manual"


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _latest(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not matches:
        raise FileNotFoundError(f"Nenhum PDF encontrado em {directory}")
    return matches[-1]
