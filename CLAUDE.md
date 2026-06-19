# CLAUDE.md


This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


## Commands


- Setup: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
- Run app: flask --app src.app run
- Run all tests: pytest
- Run single test file: pytest tests/test_calculator.py
- Run single test: pytest tests/test_calculator.py::TestCalcola::test_plafond_esaurito_tutto_imponibile


## Architecture


Flask webapp with no database — state lives in `data/richieste.json`. No external services.


**Data flow for a new request:**


1. `app.py` → `validator.valida()` checks field presence and category-specific fields
2. `app.py` → `validator.compatibile()` checks the lavoro agile ↔ trasferta incompatibility (2026)
3. `app.py` → appends the record, then `_ricalcola_mese()` → `calculator.ripartisci_mese()` imputes the monthly plafond across the whole `(dipendente, mese)` group in date order, splitting each into `quota_esente` / `quota_imponibile`
4. `app.py` → `storage.salva()` writes the full list (recomputed records included) to JSON


**Key domain rules (regime by `data` di sostenimento — 41/2024 ≤ 2025, 18/2026 ≥ 2026):**


`rules.py` selects the regime from the year of the request's `data` (see `_regime`); all
massimali/plafond are reached through date-aware accessors (`massimali_giornalieri(data)`,
`plafond_mensile(data)`, …), never bare constants.

- Categories `trasferta_italia`, `trasferta_estero`, `pasto` → capped per day (`giorni`)
- Category `chilometrico` → capped per km (`km`)
- Category `alloggio` → capped per night (`notti`)
- Category `lavoro_agile` (2026 only, 3,50 €/g) → capped per day, max 12 giornate/month via
  `storage.giornate_agile_riconosciute_nel_mese`; rejected for dates ≤ 2025 with
  `"categoria non riconosciuta"`
- `trasferta_estero` > 5 giorni (2026 only) → progressive reduction in
  `calculator._massimale_estero_ridotto`
- Incompatibility `lavoro_agile` ↔ trasferta on overlapping days (2026 only) →
  `validator.compatibile`, called in `_registra` after `valida`
- Monthly tax-free cap (`plafond_mensile(data)`: 1.200 € → 2025, 1.400 € → 2026) is shared
  across all valid requests of the same employee in the same calendar month. Imputation
  follows the **data di sostenimento** (ties by `id`/presentation order, Sez. 1): on each
  valid insert `_registra` recomputes the whole `(dipendente, mese)` group via
  `calculator.ripartisci_mese`, so prior records' quotas may be rewritten.


**Module responsibilities:**


| File | Responsibility |
|------|---------------|
| `src/rules.py` | All regulatory constants (massimali, plafond). Change only when law changes. |
| `src/calculator.py` | Pure computation: massimale teorico → esente teorica → capped by plafond |
| `src/validator.py` | Input validation; returns `(bool, str)` |
| `src/storage.py` | JSON read/write, ID generation, month helpers |
| `src/app.py` | Flask routes only; orchestrates the above |


## Working style


For every non-trivial request:


1. **Plan first** — before writing any code, produce a numbered step-by-step plan covering all files to touch, logic changes, and tests to add/update.
2. **Confirm each step** — after presenting the plan, execute one step at a time. At the end of each step, pause and ask the user to confirm before proceeding to the next.
3. **Never skip ahead** — do not execute step N+1 without explicit user approval of step N.


Exception: single-file typo fixes or pure read operations do not need step-by-step confirmation.


**Never delete files.** If a file should be removed, propose it and wait for explicit user confirmation before touching it.


## Strict Architecture & Code Style Rules


- **No OOP/Dataclass Over-engineering:** Do NOT refactor the codebase to use Python classes, models, or dataclasses for data entities. Keep using plain dictionaries (`dict`) across all modules and tests to preserve the lightweight nature of the project.
- **State & Concurrency:** Since state lives entirely in `data/richieste.json` without an ACID database, ensure that any modifications to `src/storage.py` handle file I/O safely (e.g., proper error handling or atomic writes if necessary) to prevent data corruption during concurrent Flask requests.
- **Source of Truth for Rules:** The business logic in `src/rules.py` and `src/calculator.py` is dictated by the PDF circular located in the `docs/` folder. Always consult the document in `docs/` before making any structural changes to tax-free calculations or adding new expense categories.


## Multi-agent system


Read `AGENTS.md` for the full agent hierarchy and routing rules. Summary:


- Every task involving `src/` goes through an agent — see routing table in `AGENTS.md`
- Invocation order: `mef-circular-compliance` → `arch-state-integrity` → `test-writer`
- `test-writer` is always last; never skip it after a code change


## Task files


- `.tasks/initial_state.md` — **read-only** baseline scan (2026-06-19). Richiesta dict schema, 2025 vs 2026 regulatory gap table, test coverage map, agent triggers, arch constraints. Never modify.
- `.tasks/current_state.md` — **living doc**. All session changes, open gaps, decisions. Update this after every significant change.


## Testing conventions


Tests use plain dicts (not dataclasses/models). Helper `richiesta(**campi)` in test files builds a base dict and merges overrides — follow this pattern when adding tests. All imports use `from src import <module>` (project root on `pythonpath` via `pyproject.toml`).







# AGENTS.md - Multi-Agent System Configuration


Specialized sub-agents for `rimborsi-dipendenti-esercizio`. All requests should flow through the orchestrator.


## Agent Hierarchy


1. **Orchestrator (`.claude/agents/orchestrator.md`):** Entry point for all tasks. Analyzes requests, routes to specialist agents, synthesizes results.
2. **Compliance Agent (`.claude/agents/mef-circular-compliance.md`):** Guards regulatory logic (`src/rules.py`, `src/calculator.py`, `src/validator.py`) against Circolare MEF n. 18/2026.
3. **Architecture & State Agent (`.claude/agents/arch-state-integrity.md`):** Enforces layer boundaries, JSON state integrity, and testing conventions (`src/app.py`, `src/storage.py`, `tests/`).
4. **Test Writer (`.claude/agents/test-writer.md`):** Writes and updates pytest tests after any `src/` code change. Always invoked last, after implementation agents.


## Routing at a glance


| Change scope | Agent(s) invoked | Order |
|---|---|---|
| `rules.py` / `calculator.py` / `validator.py` | `mef-circular-compliance` + `test-writer` | sequential |
| `app.py` / `storage.py` / `data/` / test files | `arch-state-integrity` + `test-writer` | sequential |
| New category or cross-cutting feature | `mef-circular-compliance` + `arch-state-integrity` + `test-writer` | sequential |
| Explicit test request only | `test-writer` | alone |
| Ambiguous | orchestrator asks one clarifying question | n/a |





