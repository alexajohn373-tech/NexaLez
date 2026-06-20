"""Symbol table models and storage."""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Symbol:
    """An identifier recorded by the lexical analyzer."""

    name: str
    data_type: str
    scope: str
    line: int


class SymbolTable:
    """Stores unique symbols by identifier and scope."""

    def __init__(self) -> None:
        self._symbols: List[Symbol] = []
        self._keys: set[Tuple[str, str]] = set()

    def clear(self) -> None:
        self._symbols.clear()
        self._keys.clear()

    def add(
        self, name: str, data_type: str, scope: str, line: int
    ) -> Optional[Symbol]:
        key = (name, scope)
        if key in self._keys:
            return None

        symbol = Symbol(name, data_type or "Unknown", scope, line)
        self._symbols.append(symbol)
        self._keys.add(key)
        return symbol

    def all(self) -> List[Symbol]:
        return list(self._symbols)

