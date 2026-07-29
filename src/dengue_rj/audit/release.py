"""Auditoria local, somente leitura, da árvore versionada e dependências."""

import csv
import json
import re
import subprocess
import tomllib
from dataclasses import asdict, dataclass
from importlib.metadata import metadata
from pathlib import Path

from dengue_rj.utils.hashing import sha256_file

SECRET_PATTERNS = (
    re.compile(
        r"(?i)(?:api[_-]?key|secret|password|passwd|access[_-]?token)"
        r"\s*[:=]\s*['\"][^'\"]{8,}['\"]"
    ),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


@dataclass(frozen=True)
class ReleaseAudit:
    tracked_files: int
    largest_tracked_file_bytes: int
    files_over_limit: tuple[str, ...]
    possible_secrets: tuple[str, ...]
    metadata_rows: int
    verified_hashes: int
    missing_metadata_files: tuple[str, ...]
    hash_mismatches: tuple[str, ...]
    dependency_licenses: dict[str, str]
    dependencies_without_license: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not (
            self.files_over_limit
            or self.possible_secrets
            or self.missing_metadata_files
            or self.hash_mismatches
        ) and self.metadata_rows > 0 and self.verified_hashes == self.metadata_rows


def audit_release(
    root: Path = Path("."),
    large_file_limit: int = 5 * 1024 * 1024,
) -> ReleaseAudit:
    """Audita somente arquivos rastreados, hashes registrados e licenças diretas."""
    tracked = _tracked_files(root)
    sizes = {path: (root / path).stat().st_size for path in tracked}
    oversized = tuple(sorted(path for path, size in sizes.items() if size > large_file_limit))
    secrets = tuple(_possible_secrets(root, tracked))
    metadata_rows, verified, missing, mismatches = _metadata_hashes(root)
    licenses = _dependency_licenses(root / "pyproject.toml")
    unknown = tuple(sorted(name for name, license_name in licenses.items() if not license_name))
    return ReleaseAudit(
        tracked_files=len(tracked),
        largest_tracked_file_bytes=max(sizes.values(), default=0),
        files_over_limit=oversized,
        possible_secrets=secrets,
        metadata_rows=metadata_rows,
        verified_hashes=verified,
        missing_metadata_files=tuple(missing),
        hash_mismatches=tuple(mismatches),
        dependency_licenses=licenses,
        dependencies_without_license=unknown,
    )


def write_audit_report(audit: ReleaseAudit, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(audit) | {"passed": audit.passed}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [
        value.decode("utf-8")
        for value in result.stdout.split(b"\0")
        if value and (root / value.decode("utf-8")).is_file()
    ]


def _possible_secrets(root: Path, tracked: list[str]) -> list[str]:
    findings = []
    for relative in tracked:
        path = root / relative
        if path.suffix.lower() in {".png", ".gif", ".zip", ".xlsx", ".xls", ".pdf"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                findings.append(f"{relative}:{line_number}")
    return sorted(findings)


def _metadata_hashes(root: Path) -> tuple[int, int, list[str], list[str]]:
    control = root / "data/metadata/controle_arquivos.csv"
    if not control.exists():
        return 0, 0, [], []
    with control.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    verified = 0
    missing, mismatches = [], []
    for row in rows:
        relative = row.get("arquivo", "").strip()
        expected = row.get("hash_sha256", "").strip().lower()
        if not relative or not expected:
            continue
        path = root / relative
        if not path.exists():
            missing.append(relative)
        elif sha256_file(path) != expected:
            mismatches.append(relative)
        else:
            verified += 1
    return len(rows), verified, sorted(missing), sorted(mismatches)


def _dependency_licenses(pyproject_file: Path) -> dict[str, str]:
    project = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))["project"]
    names = [re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0] for requirement in project["dependencies"]]
    result = {}
    for name in names:
        package_metadata = metadata(name)
        license_name = package_metadata.get("License-Expression")
        classifiers = package_metadata.get_all("Classifier", [])
        classifier_license = " | ".join(
            item.removeprefix("License :: ").strip()
            for item in classifiers
            if item.startswith("License ::")
        )
        if not license_name:
            license_name = classifier_license
        if not license_name:
            raw_license = package_metadata.get("License", "")
            license_name = next(
                (line.strip() for line in raw_license.splitlines() if line.strip()),
                "",
            )[:160]
        result[name] = license_name or ""
    return dict(sorted(result.items()))
