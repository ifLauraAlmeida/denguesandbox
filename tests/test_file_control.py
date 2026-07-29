import csv
from pathlib import Path

from dengue_rj.metadata.file_control import refresh_file_control
from dengue_rj.utils.hashing import sha256_file


def test_file_control_inventories_raw_and_processed_idempotently(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "data/raw/dengue"
    processed = tmp_path / "data/processed/dengue"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    source = raw / "source.zip"
    result = processed / "result.csv"
    source.write_bytes(b"original")
    result.write_text("code,value\n1,2\n", encoding="utf-8")
    output = refresh_file_control(tmp_path)
    first_content = output.read_text(encoding="utf-8")
    refresh_file_control(tmp_path)
    assert output.read_text(encoding="utf-8") == first_content
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert rows[0]["hash_sha256"] == sha256_file(source)
    assert rows[1]["quantidade_linhas"] == "1"
    assert rows[1]["quantidade_colunas"] == "2"
    assert rows[1]["arquivo_origem"] == "data/raw/dengue/"
