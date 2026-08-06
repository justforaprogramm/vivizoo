# 🤖 KI-Reflexion — Frontend vivizoo

> **Modul:** Frontend  
> **Modulverantwortlicher:** Erik  
> **Datum:** 2026-08-06  
> **Bewertungskriterium:** Reflexion & KI-Einsatz (5 Punkte)

---

## 1. Eingesetzte KI-Tools

| Tool | Verwendungszweck | Phase |
|------|-----------------|-------|
| **Cline (VS Code AI Assistant)** | Architekturplanung: Cross-Dokument-Vergleich (FRONTEND_ARCHITECTURE.md vs backend_core_plan.md), Identifikation von 10 Konflikten, Erstellung des IMPLEMENTATION_PLAN.md | Planung |
| **Cline (VS Code AI Assistant)** | Dokumentation: Testbeschreibungen (§8), QSS-Theme-Design, Mermaid-Klassendiagramm, KI_REFLEXION.md Template | Dokumentation |
| **Cline (VS Code AI Assistant)** | Codegenerierung: [HIER EINTRAGEN welche Dateien per KI generiert wurden — z.B. constants.py, animal_sprite.py, ...] | Implementierung |

---

## 2. Human-in-the-Loop Verifikation

### 2.1 Architekturplanung
- **KI-Output:** IMPLEMENTATION_PLAN.md mit 10 identifizierten Konflikten zwischen FRONTEND_ARCHITECTURE.md und backend_core_plan.md
- **Verifikation durch Erik:** Jeder Konflikt wurde einzeln geprüft:
  - [ ] §2.1 Food-Typen (3 statt 5) — mit Benjamin abgestimmt?
  - [ ] §2.2 Day/Night-Lighting — mit Benjamin abgestimmt?
  - [ ] §2.3 Animal-Stage — korrekt?
  - [ ] §2.4 Heal-Button — Korrektur durchgeführt?
  - [ ] §2.5 Enclosure-Daten — Fallback-Logik verstanden?
  - [ ] §2.6 Deferred Features — alle korrekt identifiziert?
- **Gelernt:** Die Backend-API ist der "Single Source of Truth". Das Frontend darf NIE mehr Felder erwarten als das Backend liefert. Frühzeitige API-Abstimmung verhindert Phantom-Features.

### 2.2 Codegenerierung
- **KI-Output:** [HIER EINTRAGEN: Welche Dateien wurden per KI generiert?]
- **Verifikation durch Erik:**
  - [ ] Jede generierte Datei wurde auf korrekte Imports geprüft
  - [ ] Jede Klasse hat genau eine Verantwortung (SRP)
  - [ ] Alle `_privaten` Attribute sind wirklich privat
  - [ ] Docstrings enthalten `Args:`, `Returns:`, `Tests:` Blöcke
  - [ ] Keine unerwarteten Abhängigkeiten zu `backend/` oder `db/`
- **Gelernt:** [HIER EINTRAGEN: Was wurde durch den Review gelernt?]

### 2.3 QSS Dark Theme
- **KI-Output:** ~100 Zeilen QSS in `main.py::_get_qss()`
- **Verifikation durch Erik:**
  - [ ] Alle Farben referenzieren `C_*` Konstanten aus `constants.py`
  - [ ] Alle Widget-Typen sind abgedeckt (QPushButton, QComboBox, QProgressBar, etc.)
  - [ ] Hover/Disabled/Pressed States funktionieren
  - [ ] Theme ist augenfreundlich (kein reines #000 Schwarz)
- **Gelernt:** [HIER EINTRAGEN]

---

## 3. Reflexion zum Lernprozess

### 3.1 Was habe ich über OOP gelernt?
[HIER EINTRAGEN: Konkrete Erkenntnisse zu Vererbung, Polymorphie, Kapselung, Komposition]

### 3.2 Was habe ich über PyQt6 gelernt?
[HIER EINTRAGEN: Signals/Slots, QGraphicsScene, QSS, Layout-Management]

### 3.3 Was habe ich über Software-Architektur gelernt?
[HIER EINTRAGEN: Trennung Frontend/Backend, Dependency Injection, API-Verträge]

### 3.4 Was würde ich beim nächsten Mal anders machen?
[HIER EINTRAGEN: Verbesserungsvorschläge für zukünftige Projekte]

---

## 4. KI-Kritik

### 4.1 Was hat die KI gut gemacht?
[HIER EINTRAGEN]

### 4.2 Wo lag die KI falsch?
[HIER EINTRAGEN: Konkrete Beispiele von falschem oder suboptimalem KI-Code]

### 4.3 Wie wurde der KI-Output verbessert?
[HIER EINTRAGEN: Welche manuellen Änderungen waren nötig?]

---

*Diese Datei ist Teil der Abgabe und wird für die 5 Punkte "Reflexion & KI-Einsatz" bewertet.*