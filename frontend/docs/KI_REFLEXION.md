# 🤖 AI Reflection — vivizoo Frontend

> **Module:** Frontend · **Module owner:** Erik
> **Grading criterion:** Reflexion & KI-Einsatz (5 points)
> **Status:** 2026-08-09

---

## 1. Which AI tools, and in which role

| Phase | Model | Interface | Task |
|---|---|---|---|
| Planning, implementation, docs | **DeepSeek v4 Pro** | Cline (VS Code) | Cross-read the planning sources, resolved 10 contradictions, generated all widget and sprite classes, `main.py`, the QSS theme, the first diagrams |
| Review and correction | **Claude Opus 5** | Claude Code (CLI) | Verified every displayed value against the real backend code, found and fixed eleven frontend defects plus one backend defect, refactored the sprites into a hierarchy, rewrote the documentation |

**Why two models?** A model that reviews its own code inherits its own
assumptions. The second one got a different job — not "keep writing" but
"verify every claim against the neighbouring module". That split produced
every finding in §3; none of them surfaced while re-reading the code myself.

---

## 2. Human in the loop

The AI plan resolved ten conflicts between the UI design and the backend
plan. Checked later against the **actual backend code** rather than its
planning document, three of those resolutions turned out wrong:

| Original decision | Reality in the code | Correction |
|---|---|---|
| "Backend only exposes `zoo_open`" | `_phase_of()` returns four real phases | Four-phase lighting |
| "Hard-code the life stage to 'adult'" | No stage exists, but `is_dead` does | Real life status |
| "Enclosure membership by point-in-rectangle" | All animals start at (300, 200) and roam | Occupancy via `free_slots` |

**Lesson:** a neighbouring module's plan is a statement of intent, not a
contract. Only the code is binding — or a test against it.

Every generated file was then read and checked against the neighbours:
imports and cycles, one responsibility per class, private state behind
properties, complete docstrings, no `backend`/`db` import outside the entry
point, every displayed metric traced to its source. Three of those checks no
longer depend on my eyes — `tests/test_layering.py` enforces one class per
file, the layer boundary and the module-owner note on every run. A checklist
ticked by hand does not get ticked again after the next refactoring.

One item stayed honest instead of green: colours mostly come from the `C_*`
constants, but 59 hex literals remain in the QSS templates.

---

## 3. Where the AI was wrong

Eleven defects; the instructive ones:

| Defect | Effect | How it surfaced |
|---|---|---|
| **Invented prices.** `MEAT: 50`, `lion: 8000` — the backend says 8 € and 900 € | Shop prices off by up to a factor of ten | Line-by-line comparison with `Inventory.FOOD_PRICES` |
| **Invented field names.** `msg["time"]`, `finances["reputation"]`, `animal["name"]` — none exist | Chat log without timestamps, two chips permanently 0, every animal named after its species | Four symptoms, one cause |
| **Discarded signal payload.** `pyqtSignal(str, dict)` wired straight to `_dispatch(action, **kwargs)` — PyQt passes only as many arguments as the slot takes *positionally* | Three of four action buttons silently did nothing | A test that clicks the button instead of calling the controller |
| **Swallowed errors.** `except Exception: return {"message": "Fehler bei Aktion"}` | A real backend bug in `buy_animal` stayed invisible | Only after the original message was passed through |
| **Triple copy-paste sprite.** Three near-identical 197-line files instead of one base class | 470 duplicated lines | Code review before submission |
| **Invented numbers in its own documentation.** "9 status chips", "314 test descriptions" | Falsifiable claims in five documents at once | Every number recomputed by script |

Full list with symptom, cause and fix: [`CHANGELOG.md`](CHANGELOG.md).

**Three patterns.** *Plausible invention* — the AI invents exactly where it
does not know an interface, and it invents something believable; 50 € and a
field called `time` look right, which is why they survive a review that only
checks readability. *Errors without error messages* — the expensive defects
were the quiet ones: a discarded payload, a stale panel, an ignored keyword.
Nothing raises, nothing logs; the code runs and does the wrong thing.
*The test walked around the defect* — the worst bug survived every test,
because those called the controller directly and skipped the broken signal
path. A test that does not take the user's route tests different software.

---

## 4. What I learned

Cross-checking with a second AI helped the most, and it saved a lot of time.
The reasons are in the sections above. At the start I thought that asking the
same AI to point out its own mistakes would improve the result a little. It
did not. Even the obvious mistakes only became visible when I checked the
code myself, or when a different AI looked at it.

### 4.1 About OOP

The inheritance hierarchy did not exist at first. Before: three files of 197
lines each, about 95 % identical. Now `lion_sprite.py`, `giraffe_sprite.py`
and `penguin_sprite.py` are 39 lines each, and five of those lines are class
attributes. Everything else sits once in `AnimalSpriteBase` (465 lines) and
`AsciiAnimalSprite` (252).

### 4.2 About PyQt6

A signal carried `(str, dict)`, but PyQt only passes as many arguments as the
slot takes positionally. So the dict was dropped. Three of four buttons did
nothing and the backend answered "No animal with id None." There was no
exception, no crash and no log entry.

### 4.3 About software architecture

Layer separation: `ENCLOSURE_DEFS` and `FOOD_PRICES` are mirrored in the
frontend, not imported — otherwise there is no separation. But that is also
where the bug came from: the AI wrote `MEAT: 50`, the backend says 8 €.
Mirroring means checking by hand.

### 4.4 What I would do differently

Test against the neighbour's real code, not against its plan. Three of ten
conflict resolutions were wrong because they were based on
`backend_core_plan.md` instead of `backend/core/engine.py`.

Write the numbers in the documentation as a script, not as a sentence. In the
end there were 19 wrong numbers in our own documents, and four of them made
the project look worse than it is — the README claimed 403 test descriptions,
the real number is 482.

Commit more often. Two days of work, 24 files not in git.

---

*Part of the submission; graded under "Reflexion & KI-Einsatz" (5 points).*
