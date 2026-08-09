"""
Executable unit tests for the vivizoo frontend.

The assignment asks for test *descriptions* — every production function
carries them in its docstring, see ``docs/test_plan.md``. This package is the
voluntary next step: the subset of those descriptions that can be checked
automatically, written against the stdlib ``unittest`` so it needs no
dependency beyond PyQt6 itself.

Run everything::

    python -m unittest discover -s frontend/tests -t .

The same files also run under ``pytest frontend/tests`` when pytest happens
to be installed; ``unittest.TestCase`` is understood by both.

Importing this package selects Qt's offscreen platform unless the
environment already chose one. It happens here, in the package ``__init__``,
because Python runs it before any test module — which is the only way to set
the variable *before* the first ``PyQt6`` import without putting an import
halfway down ``support.py``.

Module owner: Erik (frontend).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
