# Backend — Test-Plan

> **Hinweis:** Die fertigen Tests sind **bewusst nicht** Teil dieses Moduls;
> das Schreiben der Tests ist eine Studierenden-Aufgabe. Dieses Dokument
> konsolidiert die in den Docstrings verteilten Testvorgaben (`Tests:`-Blöcke)
> und beschreibt, *wo, was und mit welchen Randbedingungen* getestet werden
> soll. Den konkreten Rahmen (Framework, Ordnerstruktur, Fixture-Vorlagen)
> liefert die `README.md` unter **Tests**.

Grundprinzip: **Ein Produktivmodul → eine Testdatei** in `backend/tests/`,
gespiegelt zum Produktivcode, plus ein gemeinsames `conftest.py` für die
Setup-Logik.

```
backend/tests/
├── __init__.py
├── conftest.py            # Fixtures: frischer Zoo, hungriger Löwe, Engine
├── test_animal.py         # backend/core/animal.py       (Kapitel 2)
├── test_employee.py       # backend/core/employee.py     (Kapitel 1)
├── test_enclosure.py      # backend/core/enclosure.py
├── test_zoo.py            # backend/core/zoo.py          (Aggregat)
├── test_engine.py         # backend/core/engine.py + action_handler.py
├── test_finances.py       # backend/core/finances.py
├── test_inventory.py      # backend/core/inventory.py
├── test_environment.py    # backend/core/environment.py
├── test_status_effect.py  # backend/core/status_effect.py
└── test_persistence.py    # backend/persistence/db_gateway.py
```

---

## Vorgaben aus den Docstrings nach Modul

### `animal.py` — Kapitel 2 (Tiersimulation)
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Art-Diskriminator | `Lion.PREFERRED_FOOD == MEAT`, `species_key() == "lion"` | — |
| Factory | `create_animal("penguin", …)` ist `Penguin`; `"dragon"` → `ValueError` | Art key case-insensitive |
| Feed | `feed(35)` senkt Hunger und setzt `days_starved` zurück; klemmt auf 0 | Hunger `0 = satt` / `100 = verhungernd` |
| Hunger-Anstieg | nach genug Ticks +`DIGESTION_RATE` | `_update_offset` für Determinismus setzen |
| Tod | `is_dead` nach 3 verhungerten Tagen, HP 0 | genug Ticks ausführen |
| Klemmung | Konstruktion mit `150` wirft; Ops klemmt Überschuss | Werte 0–100 |

### `employee.py` — Kapitel 1 (Personal)
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Keeper | füttert nur `hunger >= threshold`, putzt alle Enclosures | Lager muss die Ressource haben |
| Tierarzt | heilt das *erste* kritische Tier (≤25 HP oder ≥75 Hunger) | tote Tiere unangetastet |
| Admin | setzt Ticketpreis aus Reputation (nicht negativ) | — |

### `enclosure.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Kapazität | `free_slots()`/`is_full()` korrekt, nie negativ | tote Tiere belegen Slot |
| Reinigung | `clean()` → `100.0`; Abnahme getaktet | genug Ticks (`TICKS_PER_CLEAN_UPDATE`) |
| Wohlbefinden | `average_welfare()` lebender Tiere; leere ⇒ `0.0` | tote Tiere ausgeschlossen |

### `zoo.py` — Aggregat (Kapitel 1)
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Bauen | Enclosure/Tier/Personal anlegen, eindeutige IDs | `e_01`, `a_01`, `v_…` |
| Lookups | `find_animal`/`find_enclosure` | unbekannt ⇒ `None` |
| Besucher | Spawn zahlt Ticket (Revenue + `_visitors_today`) | — |
| Snapshot | `daily_snapshot()` hat alle Persistenz-Felder | — |
| State | `to_game_state()` mit system/finances/inventory/map | leere Listen bei leerem Zoo |

### `engine.py` + `action_handler.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Tick | erhöht den Zähler um 1 | — |
| God mode | `feed_all` füttert nur Hungrige; `buy_food`/`buy_animal` budgetiert | unbekannte Aktion ⇒ `ValueError` |
| Entity Info | `{}` bei unbekannter ID | — |

### `persistence/db_gateway.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Tag speichern | nach 1 Tag genau ein `DailyStats`-Eintrag lesbar | Engine **eine volle Runde** laufen lassen (`for _ in range(TICKS_PER_DAY)`), erst dann schließt der Tag |
| Events | teilen die `day_id` des Tages | in-memory `ZooDatabase(":memory:")`, `storage.close()` |

### `finances.py`, `inventory.py`, `environment.py`, `status_effect.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Budget | `spend()` nie negativ, ohne Deckung `False` | `start_new_day()` setzt Zähler zurück, Guthaben bleibt |
| Lager | `consume` nie negativ, gekappt | negative Mengen ⇒ `ValueError` |
| Wetter | `welfare_modifier`/`visitor_multiplier` | nur Invarianten, kein fester Zufallswert |
| Effekt | `tick()` friedlich; Verfall wie planen | kein fester Zeitpunkt |

---

## Übergreifende Randbedingungen

1. **Logger isolieren** — `MessageLogger` ist ein Singleton; vor Tests mit
   Chat, `MessageLogger.reset_to_fresh()` und die Instanz neu holen.
2. **Zufall deterministisch** — keine Festwerte auf Koordinaten; wo nötig
   `random.seed(...)` oder `_update_offset = 0`.
3. **Tick-Grenzen** — getaktete Abläufe brauchen genug Ticks; der Tag schließt
   erst bei `tick % 480 == 0`.
4. **Hunger-Semantik** — Tier zum Fütterungstest hungrig starten
   (`_hunger = 80.0`), sonst wird nicht gefüttert.
5. **Keine echten Ressourcen** — Persistenz nur mit SQLite in-memory.
6. **Pro Test eine Sache** — ein Fehlschlag ≈ eine Ursache.

Ausführliche Umsetzung samt Fixture-Code: `README.md`, Abschnitt **Tests**.
