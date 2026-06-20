# Lexical Analyzer Project - Viva Questions and Answers

## Core Concepts

### 1. What is a lexical analyzer?

A lexical analyzer is the first phase of a compiler. It reads source code as
characters, groups them into lexemes, and produces tokens for the parser.

### 2. What is the difference between a lexeme and a token?

A lexeme is the actual text, such as `count`. A token is its category, such as
`IDENTIFIER`.

### 3. What output does this project generate?

It generates a token stream, symbol table, lexical error list, and token
statistics.

### 4. Why is lexical analysis separated from parsing?

The separation simplifies compiler design. The lexer handles characters and
token boundaries while the parser handles grammatical structure.

### 5. Which token categories are recognized?

Keywords, identifiers, numbers, strings, characters, operators, and separators.
Comments are consumed but omitted from the token stream.

### 6. What is a token pattern?

It is the rule used to recognize a token class. For example, an identifier starts
with a letter or underscore and may continue with letters, digits, or underscores.

### 7. Why are comments ignored?

Comments do not affect program execution or grammar, but the lexer must consume
them so comment contents are not mistaken for source code.

### 8. What is lookahead?

Lookahead checks upcoming characters without consuming them. It distinguishes
`/`, `//`, and `/*`, as well as `=` from `==`.

### 9. Why are multi-character operators checked first?

Otherwise `==` could incorrectly become two `=` tokens. Lexers generally prefer
the longest valid match.

### 10. Why track line and column numbers?

They locate tokens and errors precisely and make diagnostics useful.

## Implementation

### 11. Which scanning approach is used?

The lexer performs deterministic character-by-character scanning with a current
position, line, column, and one-character lookahead.

### 12. Why not use only regular expressions?

Explicit scanning makes state, escaped strings, comments, line tracking, and
error recovery easier to explain and control.

### 13. How are keywords distinguished from identifiers?

The lexer scans the identifier pattern and then checks the lexeme against the
predefined keyword set.

### 14. How are integer and floating-point numbers distinguished?

Digits are scanned first. A decimal point is included only when another digit
follows it.

### 15. How is `2name` detected as invalid?

After scanning initial digits, the lexer sees an immediate letter, consumes the
whole malformed lexeme, and reports an invalid identifier.

### 16. How are unterminated strings detected?

After an opening quote, reaching a newline or end of input before a closing quote
produces an unterminated-string error.

### 17. How are escaped characters handled?

A backslash marks the following character as escaped, preventing an escaped quote
from closing the literal.

### 18. How are character literals validated?

The content must represent one normal character or one escaped character.

### 19. How are multi-line comments processed?

Characters are consumed until `*/`. Reaching end of input first reports an
unterminated-comment error.

### 20. What is lexical error recovery?

It means reporting an error and continuing from a sensible position so multiple
problems can be shown in one run.

### 21. How is the symbol table populated?

When a type keyword is followed by an identifier, the identifier is stored with
its inferred type, current scope, and declaration line.

### 22. How are scopes represented?

A stack is used. Class, function, and block scopes are pushed at `{` and popped
at `}`.

### 23. Is symbol-table construction normally a lexical task?

Basic collection can be demonstrated here, but complete declaration and type
validation normally belongs to syntax and semantic analysis.

### 24. Why is the project modular?

Tokens, errors, symbols, scanning, and presentation are separated, improving
testing, maintenance, and extension.

### 25. Where is OOP used?

`Lexer`, `SymbolTable`, `Token`, `LexicalError`, `AnalysisResult`, and
`LexicalAnalyzerGUI` model distinct responsibilities.

## GUI and Testing

### 26. Why use ttk?

ttk provides theme-aware widgets, consistent states, and a more professional
native appearance.

### 27. How does dark mode work?

A Boolean setting selects a light or dark palette, then reapplies widget styles,
editor colors, row colors, icons, and chart colors.

### 28. How are icons included without dependencies?

Small `PhotoImage` icons are drawn programmatically at runtime.

### 29. How are charts generated?

Tkinter Canvas primitives draw bars, arcs, labels, legends, and the donut chart
from the latest statistics.

### 30. Why use Treeview for tables?

It provides headings, rows, selection, scrolling, and ttk theme support.

### 31. How does token search work?

It filters displayed rows using case-insensitive matches against token type or
lexeme without changing the stored result.

### 32. How was the lexer tested?

With valid and malformed samples, all required token classes, comments, literals,
operators, and assertion-based smoke tests.

### 33. What is the time complexity?

Approximately O(n), because each source character is consumed a constant number
of times.

### 34. What are the limitations?

The language is fixed, advanced number formats are absent, and symbol typing uses
lightweight inference rather than a full parser and semantic analyzer.

### 35. How could it be extended?

Add configurable language rules, finite-automata visualization, parser and AST
integration, semantic checks, code generation, and automated unit tests.

### 36. How does CSV export work?

Python's standard `csv` module writes the current token or symbol collection with
a UTF-8 header row.

### 37. Why is `token.py` implemented carefully?

Python has a standard module with that name. The project loads standard token
definitions first, preserving the required filename without breaking imports.

### 38. Which architecture pattern does the project resemble?

Model-View-Controller: lexer and data classes form the model, Tkinter is the
view, and event methods coordinate actions.

### 39. Why is it suitable for demonstration?

It exposes compiler artifacts in separate tabs, includes valid and invalid
examples, visual diagnostics, exports, themes, and live charts.

### 40. What is a good demonstration sequence?

Explain tokens, analyze the valid example, inspect tokens and symbols, show the
dashboard, then analyze the invalid example to demonstrate recovery.
