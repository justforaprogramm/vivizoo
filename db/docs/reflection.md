# Reflection — Database Module

**Focus area: Database**

> **This file is a scaffold.** The factual sections are filled in. Every part
> marked `[YOUR TEXT]` has to be written by you — the criterion rewards
> demonstrated understanding, and that cannot be delegated. Delete this note
> before submitting.

---

## 1. What I built and why it looks like this

**Task:** persist the zoo simulation — end-of-day summaries and the message
log for the charts, plus complete savegames.

**Chosen approach:** SQLite via SQLAlchemy, behind an abstract interface
that callers talk to.

`[YOUR TEXT — two or three sentences in your own words: what did you set out
to achieve, and what does the module do today?]`

---

## 2. Decisions I made, and what I traded away

### 2.1 SQLite instead of a database server

The application is a single-user desktop program, and the submission has to
run on a plain Python 3.14 kernel. Any server-based database would require
the examiner to install and start it first. Data volume settles it too:
roughly 5,000 rows after a hundred simulated days, where SQLite becomes
interesting somewhere around a few million.

Because SQLAlchemy sits in between, the database is a configuration value
rather than an architectural commitment — `"sqlite:///..."` becomes
`"postgresql://..."` without touching any other code.

`[YOUR TEXT — do you agree with this reasoning? Would you decide differently
today, and why?]`

### 2.2 An ORM instead of hand-written SQL

My first design had no ORM: hand-written mappers, a generic repository base
class, a transaction wrapper, a schema manager. I dropped it after the
guidance that no large custom effort was expected.

What surprised me is that the ORM version demonstrates **more** object
orientation, not less. The hand-written version would have been plumbing —
code that shows effort. The SQLAlchemy version puts the object-oriented work
into the domain model, where polymorphic loading and cascades are actual
modelling decisions.

`[YOUR TEXT — did you find this convincing? What did you have to look up to
follow the SQLAlchemy parts?]`

### 2.3 `profit_loss` as a generated column

The requirements list it as a column, so it is one — but declared
`GENERATED ALWAYS AS (revenue - expenses)`. It can never contradict the
values it derives from.

The price: on a freshly built object the attribute is `None`, and it is only
populated on objects read back from the database. I accepted that because a
value that cannot be inconsistent is worth more than one that is convenient.

`[YOUR TEXT — would you have made the same call?]`

### 2.4 One save slot

`enclosure_id` is the primary key of `enclosures`, so two slots cannot both
hold an enclosure `"e_01"`. The MVP uses slot 1 and replaces it wholesale, so
it never surfaces. The fix — a composite primary key — is documented in
`architecture.md` rather than silently left out.

`[YOUR TEXT — why did you accept this limitation for now?]`

---

## 3. Where AI helped, and where I had to check it

AI was used to draft the module. That is allowed; what matters is what
happened afterwards. Concretely:

### 3.1 Six real bugs that only surfaced through verification

**A performance bug, found by measuring.** `get_stats(30)` eagerly loaded
every message of every day — data the charts never touch. The code looked
correct and passed every functional test. Only timing it exposed the problem:

| | measured |
|---|---|
| with messages eagerly loaded | 15.6 ms |
| after suppressing that load | 0.51 ms |

A 30× difference that no amount of reading the code would have revealed.

**A usability bug in the ORM defaults.** SQLAlchemy applies `default=` values
when *writing a row*, not when constructing an object. A freshly built
`Lion(animal_id="a_01")` therefore carried `hp = None`, and `is_critical()`
crashed on it. Fixed with an `init` event listener so defaults apply at
construction.

**A promise the code did not keep.** The documentation claimed `save_day()`
was "safe to retry". Running the same script twice showed that only the day
row was replaced — the messages piled up, two calls giving four events
instead of two. The appending itself is correct, because mid-day flushes
through `append_events()` must survive the day-end call. What was wrong was
the description. Fixed by making the two behaviours explicit in the
signature (`replace_events`) and saying so plainly in the docs.

That one is worth noting for a different reason than the others: it was not
a coding mistake but a **documentation** mistake, and documentation mistakes
are the ones that silently mislead whoever uses the module next.

**Two bugs that only a realistic walkthrough exposed.** Writing a short
script that stored some animals and read one back found both of these, and
neither would have shown up in a unit test of a single method:

* `animal.enclosure` raised `DetachedInstanceError` after `load_game()`
  returned. The downward relationships were eager-loaded, the upward ones
  were not — and SQLAlchemy silently stops eager-loading when the two form a
  cycle. Fixed by resolving those links while the session is still open,
  which costs no extra queries because every parent is already in memory.
* `save_game()` on a graph that came from `load_game()` failed with
  `StaleDataError`. Load–play–save is *the* normal cycle, and it did not
  work. The cause was subtle: a loaded graph still carries its database
  identity, so adding it back emitted `UPDATE` statements against rows the
  same transaction had just deleted.

**A silent data loss.** Identifiers such as ``a_01`` are chosen by the
caller, and an obvious way to produce them is a counter. After a savegame is
loaded, a counter that restarts at one hands out identifiers that already
exist — and because the graph is written with ``merge()``, the new animal
*overwrote* the old one. No exception, only a warning about something else
entirely, and one animal fewer than before.

That was the worst of them: the other bugs announced themselves with a stack
trace, this one just quietly deleted a lion. Fixed twice over — a
`next_animal_id()` helper that counts from the highest existing identifier,
and a guard in `save_game()` that refuses a graph containing duplicates.

The lesson across all of them: methods that pass their own tests can still
fail the moment they are used together, and the failures that produce no
error message are the ones worth hunting hardest.

`[YOUR TEXT — which of these did you spot yourself, and what did you learn
about trusting generated code that "looks right"?]`

### 3.2 How I verified it rather than trusting it

- 120 assertions against real SQLite databases, including cascades, foreign
  key enforcement, polymorphic loading and transaction rollback.
- An AST-based audit checking that all 67 functions carry docstrings with
  `Args:`, `Returns:` and at least two described test cases.
- Timing measurements instead of assumptions about what is fast.
- A grep-checkable layering rule instead of a promise that the layers are
  separate.

`[YOUR TEXT — what did you check by hand? Which part did you have to read
several times before you understood it?]`

### 3.3 What I would not have found without help

`[YOUR TEXT — be honest. Example candidates: that SQLite ignores foreign keys
unless PRAGMA foreign_keys=ON is set per connection; that a discriminator
column can drive class selection; how selectin loading avoids detached-object
errors.]`

---

## 4. What I understand now that I did not before

`[YOUR TEXT — pick two or three. Suggestions, only if they are actually
true for you:]`

- *Why an abstract base class is more than decoration:* Python refuses to
  instantiate an implementation that misses a method, so the contract is
  enforced at start-up rather than discovered mid-session.
- *Why validation belongs in two places:* the Python validator protects
  against our own bugs, the `CHECK` constraint protects the file itself.
- *Why the direction of dependencies matters:* the module imports nothing
  from the code that uses it, which is what makes it replaceable at all.
- *What polymorphism buys concretely:* no `if species == "lion"` chain
  anywhere, and a new species costs three lines.

---

## 5. What I would do differently next time

`[YOUR TEXT — one or two honest points. For example: measure earlier instead
of assuming; agree the schema with the other focus areas before implementing;
start the reflection while working rather than at the end.]`

---

## 6. Open points I am handing over

1. Nothing calls `save_day()` yet — until something does, this module
   contributes nothing observable to a running program.
2. The root `README.md` still needs install and run instructions for the
   whole application.
3. `planning/general/` is empty.

`[YOUR TEXT — anything else you know is unfinished. Naming it is worth more
than hoping it goes unnoticed.]`
