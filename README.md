# vivizoo — Digitaler Zwilling einer Zoo-Simulation

Objektorientierte Zoo-Simulation in Python mit PyQt6-Oberfläche, in drei
klar getrennte Module aufgeteilt.

---

## Zuständigkeiten

| Modul | Ordner | Modulverantwortlicher | Schwerpunkt |
|---|---|---|---|
| **Frontend** | [`frontend/`](frontend/) | **Erik** | PyQt6-Oberfläche: Karte, Sprites, Panels, Interaktion |
| **Backend** | [`backend/`](backend/) | **Benjamin** | Simulationslogik: Tick-Loop, Tiere, Personal, Finanzen, Aktionen |
| **Datenbank** | [`db/`](db/) | **Jannes** | Persistenz: Tagesstatistiken, Ereignisse, Spielstände (SQLAlchemy/SQLite) |

Der Modulverantwortliche steht zusätzlich im Docstring der Python-Dateien
(`Module owner: …`) — im Frontend und in der Datenbank in jeder Datei, im
Backend bisher nur in einem Teil.

---

## Architektur

```
┌─────────────┐   API-Aufrufe   ┌─────────────┐   domain→models   ┌─────────────┐
│  Frontend   │ ──────────────▶ │   Backend   │ ───────────────▶ │  Datenbank  │
│   (PyQt6)   │ ◀────────────── │             │ ◀─────────────── │   (db/)     │
└─────────────┘   Snapshots     └─────────────┘   models          └─────────────┘
     Erik                        Benjamin                            Jannes
```

**Die Schnittstellen sind einseitig und dokumentiert:**

* Das Frontend spricht mit genau einem Objekt, der `SimulationEngine`.
  Vertrag: [`backend/docs/api.md`](backend/docs/api.md). Es importiert
  weder `db` noch (außerhalb seines Einstiegspunkts) `backend`.
* Das Backend schreibt kein SQL. Nur
  [`backend/persistence/db_gateway.py`](backend/persistence/db_gateway.py)
  kennt das Datenbankmodul und benutzt dessen Vertrag
  `db.interface.AbstractPersistence`.
* Die Datenbank kennt weder Frontend noch Backend.

---

## Schnellstart

Voraussetzung: Python 3.14 (der Devcontainer bringt ihn mit). Alle Befehle
aus dem Projektwurzelverzeichnis.

```bash
# Abhängigkeiten (das Backend ist reine Standardbibliothek und braucht
# keine eigene requirements.txt — seine Datenbankanbindung deckt db/ ab)
pip install -r frontend/requirements.txt
pip install -r db/requirements.txt

# PyQt6 braucht unter Linux zwei Systembibliotheken
sudo apt-get install -y libgl1 libegl1
```

### Die Anwendung starten

```bash
python -m frontend.main
```

Es öffnet sich das Simulationsfenster mit einem vorbereiteten Zoo
(drei Gehege, vier Tiere). Bedienung und Maussteuerung:
[`frontend/README.md`](frontend/README.md).

### Module einzeln prüfen

```bash
python -m frontend.main --no-engine   # Oberfläche ohne Backend
python -m backend.demo                # Simulationslogik in der Konsole
python -m backend.demo --with-db      # zusätzlich mit Datenbankanbindung
python -m db.demo                     # Datenbank: drei Tage schreiben und lesen
```

### Ohne Bildschirm (CI, SSH)

```bash
QT_QPA_PLATFORM=offscreen python -c "
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from frontend.main import _get_qss, _create_demo_engine
from frontend.core.frontend_controller import FrontendController
from frontend.core.main_window import ZooMainWindow
app = QApplication([]); app.setStyleSheet(_get_qss())
engine, grund = _create_demo_engine()          # Tupel: (Engine, Fehlergrund)
win = ZooMainWindow(FrontendController(engine)); win.show()
QTimer.singleShot(2000, app.quit); app.exec()
tiere = len(win._controller.get_state().get('animals_on_map') or [])
print(f'Frontend laeuft. Tiere im Snapshot: {tiere}   Backend: {grund or \"ok\"}')
"
```

---

## Dokumentation je Modul

| Modul | Einstieg | Diagramme | Testplan | Reflexion |
|---|---|---|---|---|
| Frontend | [README](frontend/README.md) · [Architektur](frontend/FRONTEND_ARCHITECTURE.md) · [Planung & Ausblick](frontend/docs/IMPLEMENTATION_PLAN.md) | [Klassen-, Sequenz-, Zustands- & Komponentendiagramme](frontend/docs/frontend_class_diagram.md) | [test_plan.md](frontend/docs/test_plan.md) · [criteria_audit.md](frontend/docs/criteria_audit.md) | [KI_REFLEXION.md](frontend/docs/KI_REFLEXION.md) |
| Backend | [README](backend/README.md) · [api.md](backend/docs/api.md) | [class_diagram.md](backend/docs/class_diagram.md) · [sequence_diagrams.md](backend/docs/sequence_diagrams.md) | [test_plan.md](backend/docs/test_plan.md) | — |
| Datenbank | [README](db/README.md) · [usage.md](db/docs/usage.md) | [uml_class_diagram.md](db/docs/uml_class_diagram.md) · [uml_er_diagram.md](db/docs/uml_er_diagram.md) | [test_plan.md](db/docs/test_plan.md) | [reflection.md](db/docs/reflection.md) |

**Tests:** Die Aufgabenstellung verlangt beschriebene, nicht implementierte
Tests. Jedes Modul hinterlegt sie als `Tests:`-Block im Docstring der
jeweiligen Funktion; die Strategie steht im Testplan des Moduls.

Das Frontend hat darüber hinaus **229 ausgeführte Tests** — ohne
zusätzliche Abhängigkeit, `unittest` gehört zur Standardbibliothek:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s frontend/tests -t .
```

Und es ist statisch geprüft: `pylint frontend/` gibt **10,00/10**. Jede der
25 begründeten Ausnahmen steht einzeln in
[`frontend/docs/test_plan.md`](frontend/docs/test_plan.md) §8.

---

## Hinweis zur Abgabe

Beim Zippen `.venv/`, `__pycache__/` und `data/*.sqlite*` ausschließen:

```bash
zip -r vivizoo.zip . -x "*.venv/*" "*__pycache__/*" "*.git/*" "data/*.sqlite*"
```

---

## requirements

Due: Sunday, 9 August 2026, 11:59 PM
Digitaler Zwilling einer Zoo-Simulation

Entwicklung eines digitalen Zwillings einer Zoo-Simulation unter konsequenter Anwendung der Prinzipien der Objektorientierten Programmierung (OOP) in Python. Das Projekt soll sowohl die administrativen und wirtschaftlichen Aspekte eines Zoos als auch die biologischen Prozesse der Tierwelt abbilden.

Dieses Projekt bietet die Möglichkeit, die im Modul erlernten Konzepte der objektorientierten Programmierung praktisch anzuwenden und zu vertiefen. Sie werden ein komplexes System modellieren, das die Interaktionen zwischen verschiedenen Entitäten eines Zoos simuliert. Der digitale Zwilling soll dabei helfen, ein besseres Verständnis für die Zusammenhänge zwischen Zooverwaltung und Tierwohl zu entwickeln.

! Hinweis: Das Projekt ist nicht darauf ausgelegt vollständig und vollumfänglich als Kundenprodukt umgesetzt zu werden - es ist wichtig das Planung mit Umsetzung übereinstimmt, der Planungsteil ist die Individualleistung

Ihre Aufgabe ist es, ein Softwaremodell eines Zoos zu entwerfen und zu implementieren. Der Schwerpunkt liegt auf einer sauberen, modularen und erweiterbaren Implementierung unter Verwendung von Python und den Kernprinzipien der OOP.

Bevor Sie mit der Implementierung beginnen, ist eine sorgfältige Planungsphase entscheidend. Sie sollen Ihr objektorientiertes Design mithilfe von **Mermaid-Diagrammen** visualisieren. Dies hilft Ihnen, die Struktur Ihres Systems zu durchdenken, potenzielle Probleme frühzeitig zu erkennen und Ihr Design klar zu kommunizieren. Sollten Sie in einer Gruppe arbeiten entscheiden sie sich für einen Schwerpunkt (z.B. Frontend, Backend, Datenbank, Schnittstellendesign, ... ) und belassen die Planung auf ihren selbstgewählten Schwerpunkt individuell (Wer was macht muss ersichtlich sein in der Readme und im Code) (!! Abzugrelevant) 

Erstellen Sie mindestens ein schwerpunktspezifisches umfassendes Klassendiagramm, das die wichtigsten Klassen Ihres Systems, deren Attribute, Methoden und die Beziehungen zueinander (Vererbung, Aggregation, Komposition, Assoziation) darstellt.

Zur Darstellung wichtiger Interaktionen (z.B. "Tierpfleger füttert Tier", "Besucher kauft Ticket") können Sie zusätzlich Sequenzdiagramme erstellen.

Die Simulation ist in drei Hauptbereiche unterteilt, die durch eine gemeinsame Architektur miteinander verbunden sein müssen:

Teilbereich 1: Zoo-Verwaltung (Business-Perspektive)

Dieser Teil modelliert die organisatorischen und wirtschaftlichen Aspekte des Zoobetriebs.

Beispiel (abwandelbar):

`Zoo`: Eine zentrale Klasse, die den gesamten Zoo repräsentiert und andere Verwaltungsobjekte wie `Gehege`, `Mitarbeiter`, `Finanzen` und `Inventar` aggregiert.
`Mitarbeiter` (Abstrakte Basisklasse): Definiert gemeinsame Eigenschaften (z.B. `Name`, `ID`) und grundlegende Verhaltensweisen.
Mindestens drei spezifische Mitarbeitertypen, z.B. `Tierpfleger`, `Tierarzt`, `Verwaltungspersonal`. Jede Unterklasse erbt von `Mitarbeiter` und implementiert spezifische Methoden, die ihre Aufgaben widerspiegeln (z.B. `füttern()`, `behandeln()`, `budgetVerwalten()`).
`Gehege`: Repräsentiert einzelne Gehege mit Attributen wie `Größe`, `Kapazität`, `Zustand` (z.B. Sauberkeit) und einer Liste der darin befindlichen `Tier`-Objekte.
Finanzen`: Verwaltet Einnahmen (z.B. Ticketverkauf) und Ausgaben (z.B. Futterkosten, Gehälter). Methoden zur Aktualisierung und Abfrage des Budgets.
`Inventar`: Verwaltet verfügbare Ressourcen wie `Futter` (verschiedene Typen) oder `Medikamente`.
Anwendung von OOP-Prinzipien:

**Kapselung:** Sicherstellen, dass interne Zustände von Objekten geschützt sind und nur über definierte Schnittstellen (Methoden) manipuliert werden können.
**Vererbung & Polymorphie:** Nutzung der Vererbungshierarchie für `Mitarbeiter`. Polymorphe Methoden sollen je nach Mitarbeitertyp unterschiedliche Aktionen ausführen können.
**Komposition & Aggregation:** Der `Zoo` soll als Kompositionsobjekt fungieren, das andere Objekte wie `Gehege` und `Mitarbeiter` enthält. `Gehege` soll `Tier`-Objekte aggregieren.
Teilbereich 2: Tiersimulation (Biologische Perspektive)

Dieser Teil modelliert das Leben, Verhalten und die Interaktionen der Tiere im Zoo.

Beispiel (abwandelbar):

`Tier` (Abstrakte Basisklasse): Definiert grundlegende Attribute (`Name`, `Spezies`, `Alter`, `Gesundheit`, `Hunger`, `Energie`) und abstrakte Methoden (`fressen()`, `schlafen()`, `bewegen()`, `altern()`).

Mindestens drei spezifische Tierarten, z.B. `Löwe`, `Giraffe`, `Pinguin`. Diese erben von `Tier` und implementieren artspezifische Details (z.B. `Nahrungspräferenzen`, `typischesVerhalten()`).

`Verhalten` (Abstrakte Basisklasse oder Interface): Definiert allgemeine Verhaltensmuster.

Beispiele könnten `Fressverhalten`, `Sozialverhalten` oder `Ruheverhalten` sein. Diese können als separate Klassen implementiert werden, die von Tieren genutzt werden.

`Umweltfaktor`: Eine Klasse zur Modellierung einfacher Umwelteinflüsse wie `Wetter` (z.B. Temperatur) oder `Tageszeit`, die das Tierverhalten beeinflussen können.

Anwendung von OOP-Prinzipien:

**Vererbung & Polymorphie:** Eine klare Vererbungshierarchie für `Tier`-Objekte, um allgemeine Tierlogik zu definieren und spezifische Arten zu modellieren. Polymorphe Methoden (z.B. `fressen()`) sollen sich der jeweiligen Tierart anpassen.

**Abstraktion:** Einsatz abstrakter Klassen (`Tier`, `Verhalten`) und Methoden, um eine klare Schnittstelle für die Implementierung spezifischer Tierarten und Verhaltensweisen zu schaffen.

**Komposition:** Ein `Tier`-Objekt kann aus verschiedenen `Verhalten`-Objekten zusammengesetzt sein, um komplexe Verhaltensmuster zu modellieren.

Teilbereich 3: Simulationskern & Interaktion

Dieses Modul koordiniert die Interaktion zwischen den Verwaltungs- und Tiersimulationsmodulen und steuert den Zeitablauf.

Beispiel (abwandelbar):

`SimulationsEngine`: Die Hauptklasse, die den Simulationsablauf steuert. Sie enthält eine Referenz zum `Zoo`-Objekt und ist verantwortlich für die Aktualisierung aller Objekte pro Simulationsschritt (z.B. `tick`-Methode).

`EventScheduler`: Eine einfache Klasse, die zeitgesteuerte Ereignisse (z.B. Fütterungszeiten, Gehegereinigung) verwalten kann.

Anwendung von OOP-Prinzipien:

**Single Responsibility Principle (SRP):** Jede Klasse sollte eine klar definierte Aufgabe haben. Die `SimulationsEngine` steuert den Ablauf, die `Finanzen` verwalten Geld, die `Tier`-Klassen simulieren Tiere.

**Konsequente Anwendung von OOP-Prinzipien:** Vererbung, Polymorphie, Kapselung und Abstraktion müssen im Code erkennbar und korrekt angewendet werden.

*Modulare Architektur:** Das System sollte so gestaltet sein, dass es leicht um neue Tierarten, Gehegetypen oder Verwaltungsfunktionen erweitert werden kann.

**Python-Implementierung:** Der gesamte Code muss in Python geschrieben sein. (Ausnahmen in Frontend Darstellung kann abgewandelt werden -> PyQT HTML, Javascript, ... --> Fokus aber Python)

**Code-Qualität:** Der Code sollte gut strukturiert, lesbar und kommentiert sein (Docstrings für Klassen und Methoden sind erwünscht).

**Einfache Interaktion:** Eine grundlegende Möglichkeit zur Interaktion mit der Simulation (z.B. über die Konsole, um den Zustand des Zoos abzufragen oder Aktionen auszulösen) ist erforderlich.

Allgemein:

Der Code soll eine vollständige wie aus der Veranstaltung bekannte Dokumentation Vollumfänglich beinhalten (docstrings, inline docs)
für jede Funktion müssen mindestens 2 Tests beschrieben jedoch nicht implementiert werden
Es muss von der Architektur her Frontend, Backend, Schnittstelle, Datenbank erfüllt werden und sichtbar getrennt sein (über Datei/Ordnerstruktur -> !nicht alles in eine Python Datei schreiben)
klare Klassentrennung -> eine Aufgabe eine Datei
KI darf verwendet werden muss immer mittels "human in the loop" Prinzipien verifiziert und mit der Planung abgeglichen werden
Dieses Projekt wird anhand der folgenden Kriterien bewertet. Der Einsatz von KI-Tools ist erlaubt und wird im Kriterium "Reflexion & KI-Einsatz" bewertet. Entscheidend ist nicht der Umfang des KI-Einsatzes, sondern die Fähigkeit, den generierten Code zu verstehen, kritisch zu hinterfragen, anzupassen und den eigenen Lernprozess zu reflektieren.

Bewertungskriterien:

Objektorientierte Programmierung (OOP) – Design & Implementierung (40 Punkte)

Klassenstruktur & Modellierung (12 Punkte)

Vererbung & Polymorphie (10 Punkte)

Kapselung & Datenintegrität (8 Punkte)

Modularität & Erweiterbarkeit (10 Punkte)

Funktionalität & Korrektheit (15 Punkte)

Implementierung der Kernfunktionen (8 Punkte)

Simulationslogik & Realismus (7 Punkte)

Testbeschreibung & Teststrategie (15 Punkte)

Testplan & Testfälle (10 Punkte)

Testabdeckung & Randfälle (5 Punkte)

Dokumentation (15 Punkte)

Code-Dokumentation (Docstrings & Kommentare) (15 Punkte)

Design-Visualisierung (Mermaid) (10 Punkte)

Reflexion & KI-Einsatz (5 Punkte)

! Achten sie auf die abzurelevanten Positionen die sich in den Kriterien auch widerspiegeln !

! Auch bei einer Gruppenarbeit wird von allen Teilnehmern eine Abgabe erwartet !

Bei Einzelarbeit auch auf einen Schwerpunkt reduzieren in der Individualleistung 

Bitte laden sie alle nötigen Dateien ausschließlich als gezippte Datei hoch - achten sie darauf das das virtuelle Environment nicht mit in der Abgabe enthalten ist aber eine Anleitung zum Testen der Applikation vorliegt (es muss gewährleistet werden das bei mir mit einem 3.14 Python Kernel die Applikation ausgeführt werden kann). Legen sie dafür die entsprechenden Requirement.txt für ihre Module und Readme Files mit an.

Es muss in der Readme ersichtlich sein wer sich für welchen Bereich entschieden hat.

(Abzugrelevant wenn nicht vorhanden!!) 