"""Lexical error model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LexicalError:
    """Describes a problem discovered while scanning source code."""

    error_type: str
    line: int
    description: str
    column: int = 1

