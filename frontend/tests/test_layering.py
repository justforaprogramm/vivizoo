"""
Architecture tests — the rules that no reviewer should have to re-check.

Three of the grading criteria are structural: one class per file, a module
owner in every file, and a visible separation between frontend, backend and
database. A rule that is only written down drifts; a rule that is asserted
does not.

Module owner: Erik (frontend).
"""

from __future__ import annotations

import ast
import pathlib
import unittest

_FRONTEND = pathlib.Path(__file__).resolve().parents[1]
_PRODUCTION = sorted(
    path
    for path in _FRONTEND.rglob("*.py")
    if "tests" not in path.parts and "__pycache__" not in path.parts
)


def _tree(path: pathlib.Path) -> ast.Module:
    """Parse one production module.

    Args:
        path: The file to parse.

    Returns:
        ast.Module: The parsed syntax tree.
    """
    return ast.parse(path.read_text(encoding="utf-8"))


class TestLayering(unittest.TestCase):
    """Only the entry point may know that a backend exists."""

    def test_backend_and_db_imports_only_in_main(self) -> None:
        """No UI module and not even the controller imports backend or db."""
        offenders = []
        for path in _PRODUCTION:
            if path.name == "main.py":
                continue
            for node in ast.walk(_tree(path)):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    if name.split(".")[0] in {"backend", "db"}:
                        offenders.append(f"{path.name}: {name}")
        self.assertEqual(offenders, [], f"layer violation: {offenders}")

    def test_ui_does_not_import_the_main_window(self) -> None:
        """Widgets must not reach back into the window that owns them."""
        offenders = [
            path.name
            for path in _PRODUCTION
            if path.parent.name == "ui"
            and "frontend.core.main_window" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])


class TestFileStructure(unittest.TestCase):
    """One class per file, and every file names its owner."""

    def test_at_most_one_class_per_module(self) -> None:
        """"Eine Aufgabe, eine Datei" — enforced, not just claimed."""
        for path in _PRODUCTION:
            classes = [
                node.name
                for node in _tree(path).body
                if isinstance(node, ast.ClassDef)
            ]
            self.assertLessEqual(
                len(classes), 1, f"{path.name} declares {classes}"
            )

    def test_every_module_names_its_owner(self) -> None:
        """The submission rules make a missing owner a deduction."""
        for path in _PRODUCTION:
            docstring = ast.get_docstring(_tree(path)) or ""
            self.assertIn("Module owner", docstring, f"{path.name}")

    def test_every_module_has_a_docstring(self) -> None:
        """Including the package __init__ files."""
        for path in _PRODUCTION:
            self.assertIsNotNone(
                ast.get_docstring(_tree(path)), f"{path.name} has no docstring"
            )


class TestDocstrings(unittest.TestCase):
    """Every function and class carries test descriptions."""

    def test_every_function_describes_its_tests(self) -> None:
        """The grading asks for at least two descriptions per function."""
        thin = []
        for path in _PRODUCTION:
            for node in ast.walk(_tree(path)):
                if not isinstance(node, ast.FunctionDef):
                    continue
                doc = ast.get_docstring(node) or ""
                if doc.count("- test") < 2:
                    thin.append(f"{path.name}:{node.name}")
        self.assertEqual(thin, [], f"fewer than two descriptions: {thin}")

    def test_every_class_describes_its_tests(self) -> None:
        """Class docstrings carry a Tests: block of their own."""
        thin = []
        for path in _PRODUCTION:
            for node in ast.walk(_tree(path)):
                if not isinstance(node, ast.ClassDef):
                    continue
                if "Tests:" not in (ast.get_docstring(node) or ""):
                    thin.append(f"{path.name}:{node.name}")
        self.assertEqual(thin, [])


if __name__ == "__main__":
    unittest.main()
