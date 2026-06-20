"""Multi-language character-by-character lexical analyzer."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from errors import LexicalError
from languages import LANGUAGES, LanguageProfile, detect_language, get_profile
from symbol_table import SymbolTable
from token import Token


@dataclass
class AnalysisResult:
    """Complete output of one lexical analysis run."""

    tokens: List[Token]
    symbols: list
    errors: List[LexicalError]
    statistics: Dict[str, int]
    language: str


class Lexer:
    """Scans source code using one of the supported language profiles."""

    KEYWORDS = frozenset().union(*(profile.keywords for profile in LANGUAGES.values()))

    def __init__(self, language: str = "Auto Detect") -> None:
        self.language = language
        self.profile = get_profile(language)
        self.source = ""
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.errors: List[LexicalError] = []
        self.symbol_table = SymbolTable()
        self.scope_stack = ["Global"]
        self.pending_scope: Optional[str] = None
        self.last_data_type: Optional[str] = None
        self.expecting_declaration = False
        self.last_declared_type: Optional[str] = None
        self.expecting_scope_name = False
        self.declaration_word: Optional[str] = None
        self.at_line_start = True
        self.python_scope_indents = [0]

    def analyze(
        self,
        source: str,
        language: Optional[str] = None,
        file_path: Optional[str | Path] = None,
    ) -> AnalysisResult:
        """Analyze source using an explicit or automatically detected language."""
        requested = language or self.language
        if requested == "Auto Detect":
            requested = detect_language(file_path, source)
        self.language = requested if requested in LANGUAGES else "C"
        self.profile = get_profile(self.language)
        self._reset(source)

        while not self._at_end():
            character = self._current()
            if (
                self.language == "Python"
                and self.at_line_start
                and not character.isspace()
            ):
                self._apply_python_indent(0)
                self.at_line_start = False
            if character.isspace():
                self._consume_whitespace()
            elif self._matches_line_comment():
                self._scan_single_line_comment()
            elif self._matching_block_comment():
                self._scan_multi_line_comment()
            elif character.isalpha() or character in {"_", "$"}:
                self._scan_identifier()
            elif character.isdigit():
                self._scan_number()
            elif self._starts_string():
                self._scan_string()
            else:
                self._scan_operator_separator_or_error()

        statistics = {
            "Total Tokens": len(self.tokens),
            "Keywords": self._count("KEYWORD"),
            "Identifiers": self._count("IDENTIFIER"),
            "Numbers": self._count("NUMBER"),
            "Operators": self._count("OPERATOR"),
            "Errors": len(self.errors),
        }
        return AnalysisResult(
            list(self.tokens),
            self.symbol_table.all(),
            list(self.errors),
            statistics,
            self.language,
        )

    def _reset(self, source: str) -> None:
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []
        self.symbol_table.clear()
        self.scope_stack = ["Global"]
        self.pending_scope = None
        self.last_data_type = None
        self.expecting_declaration = False
        self.last_declared_type = None
        self.expecting_scope_name = False
        self.declaration_word = None
        self.at_line_start = True
        self.python_scope_indents = [0]

    def _scan_identifier(self) -> None:
        start = self.position
        line, column = self.line, self.column
        while not self._at_end() and (
            self._current().isalnum() or self._current() in {"_", "$"}
        ):
            self._advance()
        lexeme = self.source[start:self.position]

        if lexeme in self.profile.keywords:
            self._add_token("KEYWORD", lexeme, line, column)
            if lexeme == "class":
                self.expecting_scope_name = True
            if lexeme in {"def", "function"}:
                self.expecting_scope_name = True
            if lexeme in self.profile.data_types:
                self.last_data_type = lexeme
                self.last_declared_type = lexeme
                self.expecting_declaration = True
            if lexeme in self.profile.declaration_words:
                self.declaration_word = lexeme
                self.last_data_type = "inferred"
                self.last_declared_type = "inferred"
                self.expecting_declaration = True
            return

        if lexeme in self.profile.data_types:
            self._add_token("KEYWORD", lexeme, line, column)
            self.last_data_type = lexeme
            self.last_declared_type = lexeme
            self.expecting_declaration = True
            return

        self._add_token("IDENTIFIER", lexeme, line, column)
        if self.expecting_scope_name:
            self.pending_scope = lexeme
            self.expecting_scope_name = False
            if self.language == "Python" and self._next_non_whitespace() == "(":
                self.symbol_table.add(lexeme, "function", self.scope_stack[-1], line)
        elif self.expecting_declaration:
            self.symbol_table.add(
                lexeme,
                self.last_data_type or "Unknown",
                self.scope_stack[-1],
                line,
            )
            self.expecting_declaration = False
            if self._next_non_whitespace() == "(":
                self.pending_scope = lexeme
        elif (
            self.language == "Python"
            and self._next_non_whitespace() == "="
        ):
            self.symbol_table.add(lexeme, "inferred", self.scope_stack[-1], line)

    def _scan_number(self) -> None:
        start = self.position
        line, column = self.line, self.column
        if self.source[self.position:self.position + 2].lower() in {"0x", "0b", "0o"}:
            self._advance()
            self._advance()
            while not self._at_end() and (
                self._current().isalnum() or self._current() == "_"
            ):
                self._advance()
        else:
            while not self._at_end() and (
                self._current().isdigit() or self._current() == "_"
            ):
                self._advance()
            if self._current() == "." and self._peek().isdigit():
                self._advance()
                while not self._at_end() and (
                    self._current().isdigit() or self._current() == "_"
                ):
                    self._advance()
            if self._current().lower() == "e":
                checkpoint = self.position
                checkpoint_column = self.column
                self._advance()
                if self._current() in {"+", "-"}:
                    self._advance()
                if self._current().isdigit():
                    while not self._at_end() and self._current().isdigit():
                        self._advance()
                else:
                    self.position = checkpoint
                    self.column = checkpoint_column

        if not self._at_end() and (
            self._current().isalpha() or self._current() in {"_", "$"}
        ):
            while not self._at_end() and (
                self._current().isalnum() or self._current() in {"_", "$"}
            ):
                self._advance()
            lexeme = self.source[start:self.position]
            self._add_error(
                "Invalid Identifier",
                line,
                f"Identifier '{lexeme}' cannot begin with a digit.",
                column,
            )
            return
        self._add_token("NUMBER", self.source[start:self.position], line, column)

    def _scan_string(self) -> None:
        start = self.position
        line, column = self.line, self.column
        quote = self._current()
        triple = (
            self.profile.triple_quotes
            and self.source[self.position:self.position + 3] == quote * 3
        )
        delimiter = quote * 3 if triple else quote
        for _ in delimiter:
            self._advance()
        escaped = False

        while not self._at_end():
            if self.source[self.position:self.position + len(delimiter)] == delimiter and not escaped:
                for _ in delimiter:
                    self._advance()
                lexeme = self.source[start:self.position]
                token_type = self._literal_token_type(quote, lexeme, triple)
                self._add_token(token_type, lexeme, line, column)
                return
            if not triple and self._current() == "\n":
                break
            if self._current() == "\\" and not escaped:
                escaped = True
            else:
                escaped = False
            self._advance()

        error_type = "Invalid Character" if quote in self.profile.character_quotes else "Unterminated String"
        description = (
            "Character literal is missing a closing quote."
            if error_type == "Invalid Character"
            else "String literal is missing a closing quote."
        )
        self._add_error(error_type, line, description, column)

    def _literal_token_type(self, quote: str, lexeme: str, triple: bool) -> str:
        if quote not in self.profile.character_quotes or triple:
            return "STRING"
        content = lexeme[1:-1]
        valid_character = len(content) == 1 or (
            len(content) == 2 and content.startswith("\\")
        )
        if valid_character:
            return "CHARACTER"
        if self.language in {"JavaScript", "Python"}:
            return "STRING"
        self._add_error(
            "Invalid Character",
            self.line,
            f"Character literal {lexeme!r} must contain one character.",
            self.column,
        )
        return "INVALID"

    def _scan_single_line_comment(self) -> None:
        delimiter = next(
            marker for marker in self.profile.line_comments
            if self.source.startswith(marker, self.position)
        )
        for _ in delimiter:
            self._advance()
        while not self._at_end() and self._current() != "\n":
            self._advance()

    def _scan_multi_line_comment(self) -> None:
        opening, closing = self._matching_block_comment() or ("/*", "*/")
        line, column = self.line, self.column
        for _ in opening:
            self._advance()
        while not self._at_end():
            if self.source.startswith(closing, self.position):
                for _ in closing:
                    self._advance()
                return
            self._advance()
        self._add_error(
            "Unterminated Comment",
            line,
            f"Multi-line comment is missing the closing {closing}.",
            column,
        )

    def _scan_operator_separator_or_error(self) -> None:
        line, column = self.line, self.column
        operator = next(
            (
                candidate for candidate in sorted(
                    self.profile.operators, key=len, reverse=True
                )
                if self.source.startswith(candidate, self.position)
            ),
            None,
        )
        if operator:
            self._add_token("OPERATOR", operator, line, column)
            for _ in operator:
                self._advance()
            return

        character = self._current()
        if character in self.profile.separators:
            self._add_token("SEPARATOR", character, line, column)
            if character == "{":
                scope = self.pending_scope or f"Block (Line {line})"
                self.scope_stack.append(scope)
                self.pending_scope = None
            elif character == "}" and len(self.scope_stack) > 1:
                self.scope_stack.pop()
            elif character == ";":
                self.last_declared_type = None
                self.expecting_declaration = False
            self._advance()
            return

        error_type = "Unknown Token" if character in {"!", "&", "|"} else "Invalid Character"
        self._add_error(
            error_type,
            line,
            f"Character '{character}' is not valid for {self.language}.",
            column,
        )
        self._advance()

    def _starts_string(self) -> bool:
        return self._current() in set(self.profile.string_quotes) | set(self.profile.character_quotes)

    def _matches_line_comment(self) -> bool:
        return any(
            self.source.startswith(marker, self.position)
            for marker in self.profile.line_comments
        )

    def _matching_block_comment(self) -> Optional[tuple[str, str]]:
        return next(
            (
                pair for pair in self.profile.block_comments
                if self.source.startswith(pair[0], self.position)
            ),
            None,
        )

    def _consume_whitespace(self) -> None:
        while not self._at_end() and self._current().isspace():
            if self._current() == "\n":
                self._advance()
                continue
            if self.language == "Python" and self.at_line_start:
                indent = 0
                while not self._at_end() and self._current() in {" ", "\t"}:
                    indent += 4 if self._current() == "\t" else 1
                    self._advance()
                if self._current() == "\n":
                    continue
                self._apply_python_indent(indent)
                self.at_line_start = False
                continue
            self._advance()

    def _apply_python_indent(self, indent: int) -> None:
        while (
            len(self.python_scope_indents) > 1
            and indent < self.python_scope_indents[-1]
        ):
            self.python_scope_indents.pop()
            self.scope_stack.pop()
        if self.pending_scope and indent > self.python_scope_indents[-1]:
            self.scope_stack.append(self.pending_scope)
            self.python_scope_indents.append(indent)
            self.pending_scope = None

    def _add_token(self, token_type: str, lexeme: str, line: int, column: int) -> None:
        if token_type != "INVALID":
            self.tokens.append(Token(token_type, lexeme, line, column))

    def _add_error(self, error_type: str, line: int, description: str, column: int) -> None:
        self.errors.append(LexicalError(error_type, line, description, column))

    def _advance(self) -> str:
        character = self._current()
        self.position += 1
        if character == "\n":
            self.line += 1
            self.column = 1
            self.at_line_start = True
        else:
            self.column += 1
            if not character.isspace():
                self.at_line_start = False
        return character

    def _current(self) -> str:
        return "\0" if self._at_end() else self.source[self.position]

    def _peek(self, distance: int = 1) -> str:
        index = self.position + distance
        return "\0" if index >= len(self.source) else self.source[index]

    def _at_end(self) -> bool:
        return self.position >= len(self.source)

    def _next_non_whitespace(self) -> str:
        index = self.position
        while index < len(self.source) and self.source[index].isspace():
            index += 1
        return "\0" if index >= len(self.source) else self.source[index]

    def _previous_significant_lexeme(self) -> Optional[str]:
        return self.tokens[-2].lexeme if len(self.tokens) >= 2 else None

    def _count(self, token_type: str) -> int:
        return sum(token.token_type == token_type for token in self.tokens)
