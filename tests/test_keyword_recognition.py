"""Regression tests for language-specific keyword classification."""

import unittest

from lexer import Lexer


class KeywordRecognitionTests(unittest.TestCase):
    def assert_tokens(self, source, language, expected):
        result = Lexer().analyze(source, language)
        actual = [(token.lexeme, token.token_type) for token in result.tokens]
        self.assertEqual(actual, expected)

    def test_minimal_java_class_auto_detects_and_recognizes_keywords(self):
        self.assert_tokens(
            "public class Student {}",
            "Auto Detect",
            [
                ("public", "KEYWORD"),
                ("class", "KEYWORD"),
                ("Student", "IDENTIFIER"),
                ("{", "SEPARATOR"),
                ("}", "SEPARATOR"),
            ],
        )

    def test_c_declaration_keyword(self):
        self.assert_tokens(
            "int age = 20;",
            "C",
            [
                ("int", "KEYWORD"),
                ("age", "IDENTIFIER"),
                ("=", "OPERATOR"),
                ("20", "NUMBER"),
                (";", "SEPARATOR"),
            ],
        )

    def test_python_function_keyword(self):
        self.assert_tokens(
            "def hello():",
            "Python",
            [
                ("def", "KEYWORD"),
                ("hello", "IDENTIFIER"),
                ("(", "SEPARATOR"),
                (")", "SEPARATOR"),
                (":", "SEPARATOR"),
            ],
        )

    def test_javascript_declaration_keyword(self):
        self.assert_tokens(
            'let name = "Ali";',
            "JavaScript",
            [
                ("let", "KEYWORD"),
                ("name", "IDENTIFIER"),
                ("=", "OPERATOR"),
                ('"Ali"', "STRING"),
                (";", "SEPARATOR"),
            ],
        )

    def test_keyword_matching_is_exact_and_case_sensitive(self):
        result = Lexer().analyze("Public classroom Class", "Java")
        self.assertEqual(
            [(token.lexeme, token.token_type) for token in result.tokens],
            [
                ("Public", "IDENTIFIER"),
                ("classroom", "IDENTIFIER"),
                ("Class", "IDENTIFIER"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
