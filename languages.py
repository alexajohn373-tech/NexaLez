"""Language profiles and file-extension detection."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


JAVA_KEYWORDS = frozenset({
    "public", "private", "protected", "class", "static", "void",
    "int", "float", "double", "char", "boolean", "if", "else",
    "while", "for", "return", "new", "this",
})

C_CPP_KEYWORDS = frozenset({
    "int", "float", "double", "char", "void", "if", "else",
    "while", "for", "return", "switch", "case", "break",
    "continue", "struct",
})

JAVASCRIPT_KEYWORDS = frozenset({
    "let", "const", "var", "function", "return", "if",
    "else", "while", "for", "class",
})

PYTHON_KEYWORDS = frozenset({
    "def", "class", "if", "else", "elif", "for", "while",
    "return", "import", "from", "True", "False", "None",
})


@dataclass(frozen=True)
class LanguageProfile:
    """Lexical rules that vary between supported programming languages."""

    name: str
    extensions: tuple[str, ...]
    keywords: frozenset[str]
    data_types: frozenset[str]
    declaration_words: frozenset[str]
    operators: frozenset[str]
    separators: frozenset[str]
    line_comments: tuple[str, ...]
    block_comments: tuple[tuple[str, str], ...]
    string_quotes: tuple[str, ...] = ('"',)
    character_quotes: tuple[str, ...] = ("'",)
    triple_quotes: bool = False


COMMON_OPERATORS = frozenset({
    "===", "!==", ">>>", "<<=", ">>=", "**=", "//=", "=>", "++", "--",
    "==", "!=", "<=", ">=", "&&", "||", "+=", "-=", "*=", "/=", "%=",
    "&=", "|=", "^=", "<<", ">>", "??", "?.", "**", "//", ":=", "->",
    "+", "-", "*", "/", "%", "=", "<", ">", "!", "&", "|", "^", "~", "?",
})

C_SEPARATORS = frozenset({"(", ")", "{", "}", "[", "]", ";", ",", ".", ":"})
PYTHON_SEPARATORS = frozenset({"(", ")", "{", "}", "[", "]", ",", ".", ":", ";"})


LANGUAGES: dict[str, LanguageProfile] = {
    "C": LanguageProfile(
        "C", (".c", ".h"),
        C_CPP_KEYWORDS | frozenset({
            "auto", "break", "case", "char", "const", "continue", "default",
            "do", "double", "else", "enum", "extern", "float", "for", "goto",
            "if", "inline", "int", "long", "register", "restrict", "return",
            "short", "signed", "sizeof", "static", "struct", "switch",
            "typedef", "union", "unsigned", "void", "volatile", "while",
        }),
        frozenset({
            "char", "double", "float", "int", "long", "short", "signed",
            "unsigned", "void", "struct", "enum",
        }),
        frozenset(),
        COMMON_OPERATORS | frozenset({"#"}), C_SEPARATORS, ("//",), (("/*", "*/"),),
    ),
    "C++": LanguageProfile(
        "C++", (".cpp", ".cc", ".cxx", ".hpp", ".hh"),
        C_CPP_KEYWORDS | frozenset({
            "alignas", "alignof", "and", "asm", "auto", "bool", "break",
            "case", "catch", "char", "class", "const", "constexpr", "continue",
            "default", "delete", "do", "double", "else", "enum", "explicit",
            "export", "extern", "false", "float", "for", "friend", "if",
            "inline", "int", "long", "namespace", "new", "nullptr", "operator",
            "private", "protected", "public", "return", "short", "signed",
            "sizeof", "static", "struct", "switch", "template", "this", "throw",
            "true", "try", "typedef", "typename", "union", "unsigned", "using",
            "virtual", "void", "volatile", "while",
        }),
        frozenset({
            "auto", "bool", "char", "double", "float", "int", "long", "short",
            "signed", "string", "unsigned", "void",
        }),
        frozenset(),
        COMMON_OPERATORS | frozenset({"::", "#"}), C_SEPARATORS,
        ("//",), (("/*", "*/"),),
    ),
    "Java": LanguageProfile(
        "Java", (".java",),
        JAVA_KEYWORDS | frozenset({
            "abstract", "assert", "boolean", "break", "byte", "case", "catch",
            "char", "class", "const", "continue", "default", "do", "double",
            "else", "enum", "extends", "final", "finally", "float", "for",
            "goto", "if", "implements", "import", "instanceof", "int",
            "interface", "long", "native", "new", "package", "private",
            "protected", "public", "return", "short", "static", "strictfp",
            "super", "switch", "synchronized", "this", "throw", "throws",
            "transient", "true", "false", "null", "try", "void", "volatile",
            "while", "var", "record", "sealed", "permits",
        }),
        frozenset({
            "boolean", "byte", "char", "double", "float", "int", "long",
            "short", "String", "var", "void",
        }),
        frozenset(),
        COMMON_OPERATORS | frozenset({">>>="}), C_SEPARATORS,
        ("//",), (("/*", "*/"),),
    ),
    "JavaScript": LanguageProfile(
        "JavaScript", (".js", ".jsx", ".mjs", ".cjs"),
        JAVASCRIPT_KEYWORDS | frozenset({
            "async", "await", "break", "case", "catch", "class", "const",
            "continue", "debugger", "default", "delete", "do", "else", "export",
            "extends", "false", "finally", "for", "from", "function", "get",
            "if", "import", "in", "instanceof", "let", "new", "null", "of",
            "return", "set", "static", "super", "switch", "this", "throw",
            "true", "try", "typeof", "undefined", "var", "void", "while",
            "with", "yield",
        }),
        frozenset(),
        frozenset({"const", "let", "var"}),
        COMMON_OPERATORS, C_SEPARATORS,
        ("//",), (("/*", "*/"),), ('"', "'", "`"), (),
    ),
    "C#": LanguageProfile(
        "C#", (".cs",),
        frozenset({
            "abstract", "as", "async", "await", "base", "bool", "break",
            "byte", "case", "catch", "char", "checked", "class", "const",
            "continue", "decimal", "default", "delegate", "do", "double",
            "else", "enum", "event", "explicit", "extern", "false", "finally",
            "fixed", "float", "for", "foreach", "get", "goto", "if", "implicit",
            "in", "int", "interface", "internal", "is", "lock", "long",
            "namespace", "new", "null", "object", "operator", "out", "override",
            "params", "private", "protected", "public", "readonly", "record",
            "ref", "return", "sbyte", "sealed", "set", "short", "sizeof",
            "stackalloc", "static", "string", "struct", "switch", "this",
            "throw", "true", "try", "typeof", "uint", "ulong", "unchecked",
            "unsafe", "ushort", "using", "var", "virtual", "void", "volatile",
            "while",
        }),
        frozenset({
            "bool", "byte", "char", "decimal", "double", "float", "int", "long",
            "object", "sbyte", "short", "string", "uint", "ulong", "ushort",
            "var", "void",
        }),
        frozenset(),
        COMMON_OPERATORS | frozenset({"??=", "?.", "?[", "#"}), C_SEPARATORS,
        ("//",), (("/*", "*/"),),
    ),
    "Python": LanguageProfile(
        "Python", (".py", ".pyw"),
        PYTHON_KEYWORDS | frozenset({
            "False", "None", "True", "and", "as", "assert", "async", "await",
            "break", "case", "class", "continue", "def", "del", "elif", "else",
            "except", "finally", "for", "from", "global", "if", "import", "in",
            "is", "lambda", "match", "nonlocal", "not", "or", "pass", "raise",
            "return", "try", "while", "with", "yield",
        }),
        frozenset(),
        frozenset(),
        COMMON_OPERATORS | frozenset({"@=", "@"}), PYTHON_SEPARATORS,
        ("#",), (), ('"', "'"), (), True,
    ),
}

DISPLAY_LANGUAGES = ("Auto Detect", "C", "C++", "Java", "JavaScript", "C#", "Python")

EXTENSION_LANGUAGE = {
    extension: name
    for name, profile in LANGUAGES.items()
    for extension in profile.extensions
}


def detect_language(path: Optional[str | Path], source: str = "") -> str:
    """Detect a supported language from extension, then lightweight source hints."""
    if path:
        extension = Path(path).suffix.lower()
        if extension in EXTENSION_LANGUAGE:
            return EXTENSION_LANGUAGE[extension]

    stripped = source.lstrip()
    if stripped.startswith("#!") and "python" in stripped.splitlines()[0].lower():
        return "Python"
    if re_search(r"(^|\n)\s*(def|elif|import|from)\s+", source):
        return "Python"
    if re_search(r"\busing\s+System\b|\bnamespace\s+\w+", source):
        return "C#"
    if re_search(
        r"\b(public|private|protected)\s+(?:static\s+)?class\s+\w+"
        r"|\bpublic\s+class\s+\w+"
        r"|\bpublic\s+static\s+void\s+main"
        r"|\bpackage\s+\w+",
        source,
    ):
        return "Java"
    if re_search(r"\b(const|let|function)\s+\w+|=>", source):
        return "JavaScript"
    if re_search(r"#include\s*<|\bstd::|\bcout\s*<<", source):
        return "C++"
    return "C"


def re_search(pattern: str, text: str) -> bool:
    import re
    return re.search(pattern, text, re.MULTILINE) is not None


def get_profile(language: str) -> LanguageProfile:
    """Return a profile, defaulting Auto Detect to C until source detection."""
    return LANGUAGES.get(language, LANGUAGES["C"])
