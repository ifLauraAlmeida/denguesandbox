from pathlib import Path

from dengue_rj.audit.release import ReleaseAudit, _metadata_hashes, _possible_secrets
from dengue_rj.utils.hashing import sha256_file


def test_secret_scan_finds_assignment_without_exposing_value(tmp_path: Path) -> None:
    source = tmp_path / "settings.py"
    source.write_text("api_" + "key = 'abcdefghijk'\n", encoding="utf-8")
    findings = _possible_secrets(tmp_path, ["settings.py"])
    assert findings == ["settings.py:1"]
    assert "abcdefghijk" not in findings[0]


def test_metadata_hash_audit_distinguishes_match_missing_and_mismatch(
    tmp_path: Path,
) -> None:
    data = tmp_path / "valid.csv"
    data.write_text("value\n1\n", encoding="utf-8")
    control = tmp_path / "data/metadata"
    control.mkdir(parents=True)
    (control / "controle_arquivos.csv").write_text(
        "arquivo,hash_sha256\n"
        f"valid.csv,{sha256_file(data)}\n"
        "missing.csv,abc\n"
        "valid.csv,def\n",
        encoding="utf-8",
    )
    rows, verified, missing, mismatches = _metadata_hashes(tmp_path)
    assert (rows, verified) == (3, 1)
    assert missing == ["missing.csv"]
    assert mismatches == ["valid.csv"]


def test_release_requires_at_least_one_verified_metadata_hash() -> None:
    base = {
        "tracked_files": 10,
        "largest_tracked_file_bytes": 100,
        "files_over_limit": (),
        "possible_secrets": (),
        "missing_metadata_files": (),
        "hash_mismatches": (),
        "dependency_licenses": {"example": "MIT"},
        "dependencies_without_license": (),
    }
    assert not ReleaseAudit(metadata_rows=0, verified_hashes=0, **base).passed
    assert ReleaseAudit(metadata_rows=1, verified_hashes=1, **base).passed
