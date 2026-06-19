"""Persistenza delle richieste su file JSON."""

import json
from pathlib import Path

PERCORSO_DATI = Path(__file__).resolve().parent.parent / "data" / "richieste.json"


def carica():
    if not PERCORSO_DATI.exists():
        return []
    with open(PERCORSO_DATI, encoding="utf-8") as f:
        return json.load(f)


def salva(richieste):
    PERCORSO_DATI.parent.mkdir(parents=True, exist_ok=True)
    with open(PERCORSO_DATI, "w", encoding="utf-8") as f:
        json.dump(richieste, f, ensure_ascii=False, indent=2)


def prossimo_id(richieste):
    return max((r["id"] for r in richieste), default=0) + 1


def mese(richiesta):
    """Mese di riferimento di una richiesta, nel formato AAAA-MM."""
    return richiesta["data"][:7]
