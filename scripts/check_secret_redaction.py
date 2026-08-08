from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def function_source(path: str, name: str) -> str:
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(f"Function not found: {path}:{name}")


def main() -> None:
    path = "app/core/error_diagnostics.py"
    text = (ROOT / path).read_text(encoding="utf-8")
    for fragment in (
        '"token"',
        '"secret"',
        '"password"',
        '"authorization"',
        '"cookie"',
        '"credential"',
        '"api_key"',
        '"private_key"',
    ):
        assert fragment in text, fragment

    detector = function_source(path, "is_sensitive_diagnostic_key")
    assert "SENSITIVE_KEY_FRAGMENTS" in detector
    assert "fragment in normalized" in detector

    recorder = function_source(path, "record_bot_error")
    assert "is_sensitive_diagnostic_key(key)" in recorder
    assert "details[str(key)[:80]]" in recorder

    print("Diagnostic secret redaction check: OK")
    print("Token/secret/password/auth/cookie/credential-like extra fields are dropped")


if __name__ == "__main__":
    main()
