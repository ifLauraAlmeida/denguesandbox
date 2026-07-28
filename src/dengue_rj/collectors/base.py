"""Contrato comum para coletores oficiais."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CollectionRequest:
    source: str
    url: str
    years: tuple[int, ...]
    output_directory: Path


class Collector(ABC):
    """Interface que obriga persistência bruta antes do processamento."""

    @abstractmethod
    def collect(self, request: CollectionRequest) -> list[Path]:
        """Coleta e retorna caminhos dos arquivos brutos imutáveis."""
