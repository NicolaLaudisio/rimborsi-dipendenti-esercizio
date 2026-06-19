"""Calcolo della quota esente e della quota imponibile di una richiesta."""

from decimal import ROUND_HALF_UP, Decimal

from src import rules


def _arr(importo):
    """Arrotondamento aritmetico al centesimo (half-up), come richiesto dalla Sez. 2.

    `round()` di Python usa l'arrotondamento bancario (half-to-even): su un confine di
    mezzo centesimo restituirebbe un valore diverso da quello previsto dalla circolare.
    """
    return float(Decimal(str(importo)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _massimale_estero_ridotto(giorni, fasce):
    """Massimale trasferta estera con riduzione progressiva per fascia (Sez. 4)."""
    piene = min(giorni, 5)
    ridotte_10 = min(max(giorni - 5, 0), 5)
    ridotte_20 = max(giorni - 10, 0)
    totale = (
        piene * fasce["piena"]
        + ridotte_10 * fasce["ridotta_10"]
        + ridotte_20 * fasce["ridotta_20"]
    )
    return _arr(totale)


def massimale_teorico(richiesta, giornate_agile_nel_mese=0):
    """Massimale di esenzione applicabile alla richiesta, in base a categoria e data.

    Il regime (massimali 2025 o 2026) è scelto da `rules` sulla data di sostenimento.
    Per il lavoro agile, `giornate_agile_nel_mese` sono le giornate già rimborsate nel
    mese: contano per il limite delle 12 giornate mensili (Sez. 3).
    """
    categoria = richiesta["categoria"]
    data = richiesta["data"]
    if categoria == "lavoro_agile":
        ammesse = min(
            richiesta["giorni"],
            max(rules.MAX_GIORNATE_AGILE - giornate_agile_nel_mese, 0),
        )
        return _arr(rules.massimali_giornalieri(data)["lavoro_agile"] * ammesse)
    if categoria == "trasferta_estero":
        fasce = rules.riduzione_estero(data)
        if fasce:
            return _massimale_estero_ridotto(richiesta["giorni"], fasce)
        # Senza riduzione (regime 2025) ricade nel calcolo a giornate generico sottostante.
    if categoria in rules.CATEGORIE_A_GIORNATE:
        return _arr(rules.massimali_giornalieri(data)[categoria] * richiesta["giorni"])
    if categoria == "chilometrico":
        return _arr(rules.massimale_km(data) * richiesta["km"])
    if categoria == "alloggio":
        return _arr(rules.massimale_notte(data) * richiesta["notti"])
    raise ValueError(f"categoria non gestita: {categoria}")


def ripartisci_mese(richieste_ordinate):
    """Ripartisce il plafond mensile su un gruppo di richieste valide già ordinate.

    Le richieste vanno passate nell'ordine di imputazione (data di sostenimento, poi
    ordine di presentazione, Sez. 1). Accumula sia la quota esente sia le giornate di
    lavoro agile, così che plafond e limite delle 12 giornate seguano lo stesso ordine.
    Restituisce una lista di (quota_esente, quota_imponibile, dettaglio) allineata
    all'input.
    """
    esente_cumulata = 0.0
    giornate_agile = 0
    risultati = []
    for r in richieste_ordinate:
        esente, imponibile, dettaglio = calcola(r, esente_cumulata, giornate_agile)
        esente_cumulata = _arr(esente_cumulata + esente)
        if r["categoria"] == "lavoro_agile":
            giornate_agile += r["giorni"]
        risultati.append((esente, imponibile, dettaglio))
    return risultati


def calcola(richiesta, esente_gia_riconosciuta, giornate_agile_nel_mese=0):
    """Restituisce (quota_esente, quota_imponibile, dettaglio).

    `esente_gia_riconosciuta` è la quota esente già riconosciuta al dipendente
    nel mese della richiesta, ai fini del plafond mensile. `giornate_agile_nel_mese`
    sono le giornate di lavoro agile già rimborsate nel mese (limite delle 12 giornate).
    """
    importo = richiesta["importo"]
    teorico = massimale_teorico(richiesta, giornate_agile_nel_mese)
    esente_teorica = min(importo, teorico)
    capienza = max(rules.plafond_mensile(richiesta["data"]) - esente_gia_riconosciuta, 0.0)
    esente = _arr(min(esente_teorica, capienza))
    imponibile = _arr(importo - esente)
    dettaglio = {
        "massimale_teorico": teorico,
        "esente_teorica": _arr(esente_teorica),
        "capienza_plafond": _arr(capienza),
    }
    return esente, imponibile, dettaglio
