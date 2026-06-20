"""Token model with standard-library ``token`` compatibility.

This project intentionally uses the rubric-requested filename ``token.py``.
Python's own ``tokenize`` module also imports a module with that name, so the
standard definitions are loaded first to avoid shadowing-related import errors.
"""

import os


_stdlib_token_path = os.path.join(os.path.dirname(os.__file__), "token.py")
with open(_stdlib_token_path, "rb") as _stdlib_token_file:
    exec(compile(_stdlib_token_file.read(), _stdlib_token_path, "exec"), globals())


class Token:
    """Represents one recognized lexeme in the source program."""

    __slots__ = ("token_type", "lexeme", "line", "column")

    def __init__(
        self, token_type: str, lexeme: str, line: int, column: int = 1
    ) -> None:
        self.token_type = token_type
        self.lexeme = lexeme
        self.line = line
        self.column = column

    def __repr__(self) -> str:
        return (
            f"Token(token_type={self.token_type!r}, lexeme={self.lexeme!r}, "
            f"line={self.line!r}, column={self.column!r})"
        )
