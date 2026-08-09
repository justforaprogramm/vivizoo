# Backend — Test-Plan

> **Hinweis:** Die fertigen Tests sind **bewusst nicht** Teil dieses Moduls;
> das Schreiben der Tests ist eine Studierenden-Aufgabe. Dieses Dokument
> konsolidiert die in den Docstrings verteilten Testvorgaben (`Tests:`-Blöcke)
> und beschreibt, *wo, was und mit welchen Randbedingungen* getestet werden
> soll. Den konkreten Rahmen (Framework, Ordnerstruktur, Fixture-Vorlagen)
> liefert die `README.md` unter **Tests**.

Grundprinzip: **Ein Produktivmodul → eine Testdatei** in `backend/tests/`,
gespiegelt zum Produktivcode, plus ein gemeinsames `conftest.py` für die
Setup-Logik. Jedes Produktivmodul hat genau eine Entsprechung — es bleibt
keines übrig.

```
backend/tests/
├── __init__.py
├── conftest.py               # Fixtures: frischer Zoo, hungriger Löwe, Engine
├── test_action_handler.py    # backend/core/action_handler.py  (God mode)
├── test_animal.py            # backend/core/animal.py          (Kapitel 2)
├── test_behaviour.py         # backend/core/behaviour.py       (Strategy)
├── test_demo.py              # backend/demo.py                 (Smoke-Test)
├── test_employee.py          # backend/core/employee.py        (Kapitel 1)
├── test_enclosure.py         # backend/core/enclosure.py
├── test_engine.py            # backend/core/engine.py          (Tick-Loop)
├── test_environment.py       # backend/core/environment.py
├── test_event_scheduler.py   # backend/core/event_scheduler.py
├── test_finances.py          # backend/core/finances.py
├── test_inventory.py         # backend/core/inventory.py
├── test_message_logger.py    # backend/core/message_logger.py  (Singleton)
├── test_persistence.py       # backend/persistence/db_gateway.py
├── test_status_effect.py     # backend/core/status_effect.py
├── test_visitor.py           # backend/core/visitor.py
└── test_zoo.py               # backend/core/zoo.py             (Aggregat)
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
| Ruhen | `tick_update(t, is_night=True)` heilt ein verwundetes Tier über `act()` → `rest()` | nur auf dem getakteten Tick |
| Altern | `age_one_day()` erhöht `age_days` um genau 1 | wird von `Zoo.begin_new_day()` getrieben |
| Tod | `is_dead` nach 3 Hunger-Updates am Limit, HP 0 | siehe *Tod-Semantik* unten |
| Klemmung | Konstruktion mit `150` wirft; Ops klemmt Überschuss | Werte 0–100 |

### `behaviour.py` — Kapitel 2 (Strategy Pattern)
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Interface | `Behaviour` ist abstrakt; `perform()` liefert immer einen Modul-Tag (`feed`/`rest`/`idle`) | direkt instanziieren wirft `TypeError` |
| Feeding | hungriges Tier am Tag → `feed`; sattes Tier oder Nacht → `idle` | `hunger >= get_feed_threshold()` |
| Resting | Nacht → `rest` unabhängig von HP; am Tag nur bei `hp < 30` | — |
| Stateful | `StatefulBehaviour` startet mit leerem `_state`; `reset()` leert ihn wieder | ist selbst abstrakt (`perform` fehlt) |
| Auswahl | `Animal.act()` nimmt die erste Nicht-Idle-Antwort, sonst `idle` | Reihenfolge der `_behaviours` zählt |

### `employee.py` — Kapitel 1 (Personal)
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Keeper | füttert nur `hunger >= threshold`, putzt alle Enclosures | Lager muss die Ressource haben |
| Tierarzt | heilt das *erste* kritische Tier (≤25 HP oder ≥75 Hunger) | tote Tiere unangetastet; Status-Effekt fällt nur bei vorhandener `MEDICINE` weg |
| Admin | setzt Ticketpreis aus Reputation; der Basiswert ist bei `0.0` gedeckelt | auch bei stark negativer Reputation kein `ValueError` |

### `enclosure.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Kapazität | `free_slots()`/`is_full()` korrekt, nie negativ | tote Tiere belegen Slot |
| Reinigung | `clean()` → `100.0`; Abnahme getaktet | genug Ticks (`TICKS_PER_CLEAN_UPDATE`), `_update_offset` setzen |
| Untergrenze | Abnahme bleibt bei `0.0` stehen und wirft nicht | `_clamp_clean` prüft nur Eingaben von außen |
| Wohlbefinden | `average_welfare()` lebender Tiere; leere ⇒ `0.0` | tote Tiere ausgeschlossen |

### `zoo.py` — Aggregat (Kapitel 1)
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Bauen | Enclosure/Tier/Personal anlegen, eindeutige IDs | `e_01`, `a_01`, `v_001` |
| Lookups | `find_animal`/`find_enclosure` | unbekannt ⇒ `None` |
| Besucher | Spawn zahlt Ticket (Revenue + `_visitors_today`) | — |
| Tick | `update_animals()` treibt Tiere **und** die Enclosure-Abnutzung | `is_night` wird an die Behaviours durchgereicht |
| Tageswechsel | `begin_new_day()` sichert Umsatz und altert alle Tiere | vor `daily_snapshot()` aufgerufen |
| Snapshot | `daily_snapshot()` hat alle Persistenz-Felder | — |
| State | `to_game_state()` mit system/finances/inventory/map | leere Listen bei leerem Zoo |

### `engine.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Tick | erhöht den Zähler um 1 | — |
| Phasen | `_phase_of()` liefert MORNING/NOON/EVENING/NIGHT; nachts `zoo.is_open == False` | `tick % 480 == 0` ⇒ MORNING |
| Speed | `set_speed(2.0)` ok, `0`/negativ ⇒ `ValueError` | — |
| Pause | nach `pause()` steht der Zähler, nach `resume()` läuft er wieder | Thread-Test mit kurzem `sleep` |
| Read-API | `get_game_state`/`get_entity_info`/`get_chat_messages`/`get_stats` liefern die in `docs/api.md` beschriebenen Formen | `get_entity_info` ⇒ `{}` bei unbekannter ID; `get_stats` ⇒ `[]` ohne Gateway |
| Tagesabschluss | bei `tick % 480 == 0` wird der Tag geschlossen | Engine **eine volle Runde** laufen lassen |

### `action_handler.py` — God mode
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Dispatch | unbekannte Aktion ⇒ `ValueError` | — |
| `feed_all` | füttert nur Hungrige und nur bei Lagerbestand | Lager startet **leer** |
| `feed_one`/`heal` | unbekannte ID ⇒ `success: false` | tote Tiere werden nicht geheilt |
| `buy_food` | bucht vom Budget ab; ohne Deckung ⇒ `success: false` | — |
| `buy_animal` | kauft und platziert; volles Gehege ⇒ `success: false` | unbekannte `enclosure_id` fällt auf das erste Gehege zurück |
| `clean` | setzt Sauberkeit auf `100.0` | unbekannte ID ⇒ `success: false` |
| Ergebnis | `ActionResult.to_dict()` hat `success`/`message`/`chat_entries` | — |

### `visitor.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Bewegung | `move()` verschiebt um einen kleinen, begrenzten Betrag | nur Invarianten prüfen, keine Festwerte |
| Lebensdauer | `tick()` senkt `remaining_ticks`; `is_leaving()` bei `0` | — |
| Serialisierung | `to_dict()` liefert `id`/`x`/`y` | — |

### `message_logger.py` — Singleton
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Singleton | `instance()` gibt zweimal dasselbe Objekt | `reset_to_fresh()` vor jedem Test |
| Log | `log()` hängt einen `LogEntry` an; über `MAX_BUFFER` (500) fallen die ältesten weg | — |
| Drain | `drain()` liefert die Einträge **und leert** den Puffer | zweiter Aufruf ⇒ `[]` |
| Zustand | `has_unread()`/`__len__()` spiegeln den Füllstand; `clear()` leert | — |
| Eintrag | `LogEntry.to_dict()` hat `tick_count`/`type`/`text`/`entity_id`, `details` nur wenn gesetzt | — |

### `event_scheduler.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Chance | `EventScheduler(None).event_chance == DEFAULT_CHANCE` (0.01) | — |
| Auslösen | `event_chance=0.0` ⇒ nie, `1.0` ⇒ bei jedem `check()` | `random.seed()` für den Ereignistyp |
| Auswahl | `_random_living_animal()` liefert das einzige lebende Tier, sonst `None` | tote Tiere ausgeschlossen |

### `environment.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Wetter | `welfare_modifier`/`visitor_multiplier` | nur Invarianten, kein fester Zufallswert |
| Zufall | `randomize()` liefert immer ein Wetter aus `WEATHERS` | `random.seed()` setzen |

> **Hinweis:** `visitor_multiplier()` wird vom Tick-Loop benutzt
> (`Zoo.update_visitors`), `welfare_modifier()` derzeit **nicht** —
> `Zoo.average_happiness()` rechnet mit einer eigenen Tabelle. Der Modifier ist
> deshalb nur isoliert als Unit-Test prüfbar, nicht end-to-end.

### `finances.py`, `inventory.py`, `status_effect.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Budget | `spend()` nie negativ, ohne Deckung `False` | `start_new_day()` setzt Zähler zurück, Guthaben bleibt |
| Ticket | `set_ticket_price()` speichert; negativ ⇒ `ValueError` | — |
| Lager | `consume` nie negativ, gekappt | negative Mengen ⇒ `ValueError` |
| Preise | `price_of()` kennt jeden `FoodType` | — |
| Effekt | `tick()` zahlt `hp_drain` nur auf dem fälligen Tick aus | Takt über `offset`-Parameter setzen, nicht über `_offset` |
| Verfall | `is_expired()` bei `remaining_ticks == 0` | kein fester Zeitpunkt |

### `persistence/db_gateway.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Tag speichern | nach 1 Tag genau ein `DailyStats`-Eintrag lesbar | Engine **eine volle Runde** laufen lassen (`for _ in range(TICKS_PER_DAY)`), erst dann schließt der Tag |
| Events | teilen die `day_id` des Tages | **nicht** `get_chat_messages()` aufrufen — siehe *Chat-Puffer* unten |
| Lesen | `fetch_stats()` liefert Dicts in der Form aus `docs/api.md` | in-memory `ZooDatabase(":memory:")`, `storage.close()` |

### `demo.py`
| Fall | Verhalten | Randbedingung |
| --- | --- | --- |
| Aufbau | `build_demo_zoo()` liefert einen Zoo mit Gehegen, Tieren und Personal | Lager ist gefüllt |
| Lauf | `run_demo(False)` läuft durch und gibt `0` zurück | rein in-memory |
| CLI | `main()` erkennt `--with-db` | — |

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
5. **Lager füllen** — `Inventory` startet **leer**. Jeder Fütterungstest muss
   vorher `zoo.inventory.add(FoodType.MEAT, …)` aufrufen, sonst füttert
   `feed_all` null Tiere.
6. **Tod-Semantik** — `days_starved` zählt pro *Hunger-Update*
   (`TICKS_PER_HUNGER_UPDATE`), nicht pro Simulationstag. Ein Löwe mit
   `_update_offset = 0` stirbt nach rund 530 Ticks, nicht nach 3 × 480.
7. **Chat-Puffer** — `get_chat_messages()` und `DbGateway.save_daily_summary()`
   leeren **denselben** Singleton-Puffer. In einem Persistenztest darf während
   des Tages nicht gepollt werden, sonst sind 0 Events gespeichert.
8. **Keine echten Ressourcen** — Persistenz nur mit SQLite in-memory.
9. **Pro Test eine Sache** — ein Fehlschlag ≈ eine Ursache.

Ausführliche Umsetzung samt Fixture-Code: `README.md`, Abschnitt **Tests**.
