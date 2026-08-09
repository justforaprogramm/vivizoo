# AI Use and Human-in-the-Loop Review — Database Module

**Focus area: Database. Module owner: Jannes.**

Every file in `db/` carries an *Authorship* note pointing here. This document
is what it points at: the factual record of how AI was used, what the human
review actually consisted of, and which defects that review caught.

> **Everything below is checkable against the repository.** No claim here rests
> on assurance alone — each one names the command, the measurement or the file
> that backs it, and section 7 lists them together so they can be re-run.

---

## 1. The rule this follows

The project brief states:

> *KI darf verwendet werden, muss immer mittels "human in the loop" Prinzipien
> verifiziert und mit der Planung abgeglichen werden.*

and, on assessment:

> *Entscheidend ist nicht der Umfang des KI-Einsatzes, sondern die Fähigkeit,
> den generierten Code zu verstehen, kritisch zu hinterfragen, anzupassen und
> den eigenen Lernprozess zu reflektieren.*

So the question is not *whether* AI was used — it was, extensively — but
whether anything was accepted without being understood. The record below is
kept so that question can be answered with evidence rather than assurance.

---

## 2. What was AI-assisted and what was not

| Step | Who | Notes |
|---|---|---|
| Schema design (which tables, which columns) | **Human** | Fixed first in [`db_requirements.md`](../../planning/db_planning/db_requirements.md); the code was written against it, not the other way round |
| Choice of SQLite + SQLAlchemy behind an abstract interface | **Human** | Reasoning in [`architecture.md`](architecture.md), §2 and §3 |
| Decision to drop the first design (hand-written mappers, no ORM) | **Human** | Dropped after the guidance that no large custom effort was expected; the ORM version turned out to demonstrate *more* object orientation, because polymorphic loading and cascades are domain modelling rather than plumbing |
| First draft of models, persistence layer, docstrings | AI-assisted | Then reviewed line by line — see §3 |
| Diagrams (class, ER, schema, sequence) | AI-assisted | Each one re-checked against the code it claims to describe |
| Defect hunting and the fixes for it | **Both** | Found by running the code, not by reading it — see §4 |
| The personal reflection ([`reflexion.md`](reflexion.md)) | **Human** | Written by hand, no AI. The one file in the module with none in it |

---

## 3. What "human in the loop" meant concretely

Not "read it and it looked fine". Four checks, all of them repeatable by
anyone with the repository:

**1. Reconciled against the planning document.** Every table, column and
method signature in `db/` was compared field by field with
`planning/db_planning/db_requirements.md`. The planning document is the
authority; where the two disagreed, one of them was wrong and got corrected.
The most recent instance: the implementation had grown an `overwrite`
parameter on `save_day()` that the planning document did not mention. The
planning document was updated to match.

**2. Ran it, rather than reading it.** `python -m db.demo` exercises every
operation the module offers end to end. Several of the defects in §4 produce
code that reads perfectly well and fails the moment it runs.

**3. Measured instead of assuming.** The performance numbers in
[`architecture.md`](architecture.md) are timings, not estimates. One of them
overturned an assumption — see §4, the `get_stats()` entry.

**4. Made the claims machine-checkable.** Where a document asserts something
about the code, there is a command that verifies it:

```bash
grep -rnE "^[[:space:]]*(from|import) db\.persistence" \
     --include="*.py" . --exclude-dir=.venv --exclude-dir=db
```

must print nothing (the layering rule), and an AST audit over all 18 modules
confirms that all 67 functions carry `Args:`, `Returns:` and at least two
described test cases. A promise that cannot be checked is not evidence.

---

## 4. Defects the review caught

These are the reason the review was worth doing. Each one passed a reading;
none of them survived being run or measured.

| # | Defect | How it surfaced | Why it mattered |
|---|---|---|---|
| 1 | `get_stats(30)` eagerly loaded every message of every day | Timing: **15.6 ms → 0.51 ms** after suppressing the load | 30× slower for data the charts never touch. No functional test would have failed |
| 2 | `Lion(animal_id="a_01").hp` was `None`, so `is_critical()` crashed | Constructing an object without saving it | SQLAlchemy applies `default=` on *insert*, not on construction. Fixed with an `init` event listener |
| 3 | The docs promised `save_day()` was "safe to retry"; messages piled up instead | Running the same script twice | A **documentation** defect, not a code one — and those mislead silently. Fixed by making both behaviours explicit (`replace_events`) |
| 4 | `animal.enclosure` raised `DetachedInstanceError` after `load_game()` | Walking a loaded graph upwards | SQLAlchemy stops eager-loading when relationships form a cycle. Fixed by resolving parent links while the session is open — at no extra query cost |
| 5 | `save_game()` on a graph from `load_game()` raised `StaleDataError` | Doing load → play → save, i.e. the normal cycle | A loaded graph keeps its database identity, so `add()` emitted `UPDATE`s against just-deleted rows. Fixed with `merge()` |
| 6 | A duplicate `animal_id` silently **deleted** an animal | Restarting an id counter after a load | The worst of them: no exception, just one lion fewer. Fixed twice — `next_animal_id()` and a guard in `save_game()` |
| 7 | Every `ZooDatabase()` attached two more DDL listeners, without bound | Counting listeners across four constructions: 2, 4, 6, 8 | A test suite building one database per test accumulates them. `register_views()` is now idempotent |
| 8 | `append_events()` with a missing `day_id` raised `FlushError: NULL identity key` | Passing an event the docstring already forbade | The contract was documented but not enforced, and the resulting message named neither the event nor the field. Now a `ValueError` that says which |
| 9 | The enum columns had **no `CHECK` constraint at all**, though five documents claimed they did | Dumping the generated DDL and reading it | In SQLAlchemy 2.0 `create_constraint` defaults to `False`, so `Enum(native_enum=False)` produces a bare `VARCHAR`. The "second line of defence" the architecture argues for did not exist: the file accepted `type='PANIC'`. Fixed by passing `create_constraint=True` on all three enum columns |
| 10 | The `grep` command the docs offer as *proof* of the layering rule reported five false violations | Running the command instead of trusting it | It filtered on a `./` path prefix that this platform's `grep` does not emit. A verification command that cries wolf is worse than none — it trains you to ignore it. Replaced with an `--exclude-dir` form, then tested against a deliberately planted violation to confirm it still catches a real one |

Defects 1–6 were found while building the module; 7–10 during the final review
pass, by probing edge cases the demo does not reach and by running the
documentation's own claims rather than reading them.

**The pattern across all ten:** every one is code — or a document — that reads
correctly. Most were only exposed by *using* the module rather than inspecting
it, and the three most damaging (1, 6 and 9) produced no error message at all:
one was merely slow, one quietly destroyed data, and one silently removed a
safeguard everyone believed was in place. That is the concrete reason generated
work gets run and measured here rather than reviewed by eye.

Defects 9 and 10 are the two worth dwelling on, because they are the same
mistake in different clothing: **a claim in a document that nobody had
executed.** Both had been written down confidently, reviewed, and repeated
across several files. Neither survived thirty seconds of actually running it.

---

## 5. Known behaviour that was accepted rather than fixed

Honesty is worth more than a clean list. These are understood and deliberate:

- **A real day with all figures at zero is indistinguishable from a
  placeholder.** `append_events()` creates a zero-filled `daily_stats` row when
  messages arrive before a day is closed, and `save_day()` treats an all-zero
  row as free to fill in. A genuine day on which literally nothing happened
  therefore has no overwrite protection. Fixing it properly needs a marker
  column, which would change the schema — and the schema is agreed in the
  planning document. Documented in [`architecture.md`](architecture.md), §7.
- **One save slot.** `enclosure_id` is the primary key of `enclosures`, so two
  slots cannot both hold an `"e_01"`. The fix (composite key) is written down
  rather than silently omitted.
- **Five `# pylint: disable` comments in `zoo_database.py` and one in
  `db/__init__.py`.** All are false positives from SQLAlchemy's runtime-built
  attributes and from the re-export pattern; each carries its reason in place,
  and each is scoped to a single line or file rather than switched off
  globally.

---

## 6. How the marking works

Every file in `db/` carries the same note, adapted to its format — with two
deliberate exceptions: this document, which *is* the note's target, and
[`reflexion.md`](reflexion.md), which carries the opposite note because it was
written by hand without AI.

- **Python modules** — an `Authorship:` section at the end of the module
  docstring, next to the existing module-owner line.
- **Markdown documents** — a blockquote directly under the title.
- **`requirements.txt`** — a comment header.

The note is identical everywhere on purpose: it is a statement about the
process, and the process was the same for all 18 modules and 10 documents.

---

## 7. Verifying this document

| Claim | Command |
|---|---|
| Every Python module carries the note | `grep -L "Authorship" db/**/*.py` prints nothing |
| The module runs end to end | `python -m db.demo` |
| Lint is clean | `pylint db/` → 10.00/10 |
| Docstring coverage | AST audit: 18 modules, 17 classes, 67 functions, 134 described test cases, 0 gaps |
| Layering holds | the `grep` in §3 prints nothing |

---

## 8. Where to go next

| Document | Contents |
|---|---|
| [`reflexion.md`](reflexion.md) | The personal reflection — written by hand, without AI |
| [`architecture.md`](architecture.md) | Why the module looks the way it does |
| [`criteria_audit.md`](criteria_audit.md) | Every assessment criterion mapped to evidence |
| [`usage.md`](usage.md) | How to call the module |
