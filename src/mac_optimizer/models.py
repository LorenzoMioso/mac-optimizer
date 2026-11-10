"""
models.py - Modelli dati e definizioni per moduli di pulizia.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Literal

RiskLevel = Literal["safe", "recommended", "caution"]


@dataclass
class CleanResult:
    """Risultato dell'esecuzione di una scansione o pulizia per un modulo."""
    name: str
    freed_bytes: int = 0
    items_count: int = 0
    details: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def add_detail(self, text: str) -> None:
        self.details.append(text)


@dataclass
class ModuleDef:
    """Definizione dichiarativa di un modulo di pulizia."""
    id: str
    name: str
    category: str
    description: str
    default_selected: bool
    risk_level: RiskLevel
    scan_func: Callable[[], int]
    clean_func: Callable[[bool], CleanResult]
    selected: bool = True
    estimated_bytes: int = 0
    scan_done: bool = False
