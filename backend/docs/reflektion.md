# Backend — AI use & Reflection

> **Note:** `deepseek flash` at plattform.deepseek.com and `gemini flash` at gemini.google.com were used

This backend was developed with the support of an AI assistant. The AI was deliberately used for the following purposes:

* **Writing code:** functions and classes were generated individually by the AI, instead of producing whole modules at once.
* **Ideation:** the AI served as a sparring partner for design questions (e.g. how the day/phase logic should be throttled, how visitor probability should reasonably depend on the weather, or how persistence should be cleanly hidden behind an adapter).
* **Targeted refactoring:** hard-to-read or "not good" code was deliberately refactored — based on concrete AI suggestions the structure was rebuilt without changing the existing behaviour.
* **Pylint cleanup:** the AI helped to fix Pylint warnings and adjust the configuration (`.pylintrc`) so that it supports the patterns the OOP design intends (encapsulation, slim strategy classes, the `db` import of the demo as a third party) without switching off the general quality rules.

**Own responsibility / quality assurance:** the AI was used exclusively as a tool. Every single generated function was **logically checked myself** (the `Tests:` blocks in the docstrings are a result of this manual verification), so the AI-generated building blocks were only adopted after human review.
