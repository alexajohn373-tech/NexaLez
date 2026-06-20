"""Generate reproducible lexical statistics for every bundled sample."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lexer import Lexer
from languages import detect_language


ROOT = Path(__file__).resolve().parent


def generate() -> dict:
    records = {}
    for path in sorted(ROOT.glob("*/*.*")):
        if "__pycache__" in path.parts or path.suffix.lower() not in {
            ".c", ".cpp", ".java", ".js", ".cs", ".py"
        }:
            continue
        language = detect_language(path)
        result = Lexer().analyze(
            path.read_text(encoding="utf-8"),
            language=language,
            file_path=path,
        )
        records[str(path.relative_to(ROOT)).replace("\\", "/")] = {
            "language": result.language,
            **result.statistics,
            "Symbols": len(result.symbols),
        }
    (ROOT / "statistics.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    return records


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
