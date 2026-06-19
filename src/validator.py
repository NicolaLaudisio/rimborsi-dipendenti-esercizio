"""Regole di validazione delle richieste di rimborso."""

from datetime import date, timedelta

from src import rules

TRASFERTE = ("trasferta_italia", "trasferta_estero")


def valida(richiesta):
    """Restituisce (True, "") se la richiesta è valida, altrimenti (False, motivazione)."""
    if not richiesta.get("dipendente"):
        return False, "dipendente mancante"

    categoria = richiesta.get("categoria")
    if categoria not in rules.CATEGORIE:
        return False, "categoria non riconosciuta"

    importo = richiesta.get("importo")
    if importo is None or importo <= 0:
        return False, "importo non positivo"

    try:
        giorno = date.fromisoformat(richiesta.get("data") or "")
    except ValueError:
        return False, "data mancante o non valida"

    # Sez. 5: la data di sostenimento non può essere successiva alla presentazione.
    # Non essendo memorizzata la data di presentazione, si usa la data odierna.
    if giorno > date.today():
        return False, "data successiva alla presentazione"

    # La categoria lavoro agile esiste solo nel regime 2026 (Sez. 7).
    if categoria == "lavoro_agile" and not rules.regime_2026(richiesta["data"]):
        return False, "categoria non riconosciuta"

    if categoria in rules.CATEGORIE_A_GIORNATE:
        giorni = richiesta.get("giorni")
        if not giorni or giorni <= 0:
            return False, "numero di giornate non valido"

    if categoria == "chilometrico":
        km = richiesta.get("km")
        if not km or km <= 0:
            return False, "numero di chilometri non valido"

    if categoria == "alloggio":
        notti = richiesta.get("notti")
        if not notti or notti <= 0:
            return False, "numero di notti non valido"

    return True, ""


def giornate(richiesta):
    """Insieme delle date coperte dalla richiesta (periodo continuativo da `data`)."""
    inizio = date.fromisoformat(richiesta["data"])
    durata = richiesta.get("giorni") or 1
    return {inizio + timedelta(days=i) for i in range(durata)}


def compatibile(richiesta, richieste):
    """Verifica l'incompatibilità lavoro agile / trasferta (Sez. 5, dal 2026).

    Una richiesta di lavoro agile (o di trasferta) è respinta se almeno una delle sue
    giornate è coperta da una trasferta (o da un lavoro agile) valida dello stesso
    dipendente. Rilevano solo le richieste valide. Restituisce (ok, motivazione).
    """
    categoria = richiesta["categoria"]
    if categoria == "lavoro_agile":
        opposte = TRASFERTE
    elif categoria in TRASFERTE:
        opposte = ("lavoro_agile",)
    else:
        return True, ""

    if not rules.regime_2026(richiesta["data"]):
        return True, ""

    giorni_richiesta = giornate(richiesta)
    for r in richieste:
        if (
            r.get("stato") == "valida"
            and r["dipendente"] == richiesta["dipendente"]
            and r["categoria"] in opposte
            and giornate(r) & giorni_richiesta
        ):
            return False, "incompatibilità lavoro agile / trasferta"
    return True, ""
