"""Parametri normativi per il calcolo dei rimborsi spese.

Regime transitorio: le spese con data di sostenimento fino al 31/12/2025 seguono la
Circolare MEF n. 41/2024 (massimali 2025, plafond 1.200 €); le spese dal 01/01/2026
seguono la Circolare MEF n. 18/2026 (massimali aggiornati, plafond 1.400 €).

Il regime applicabile si seleziona in base all'anno della data di sostenimento: i
parametri restano l'unica fonte di verità: aggiornare la normativa significa modificare
solo questo file.
"""

from datetime import date

_PARAMETRI = {
    2025: {
        "massimali_giornalieri": {
            "trasferta_italia": 46.48,
            "trasferta_estero": 77.47,
            "pasto": 8.00,
        },
        "massimale_km": 0.42,
        "massimale_notte": 150.00,
        "plafond_mensile": 1200.00,
        "riferimento": "Circolare MEF n. 41/2024",
    },
    2026: {
        "massimali_giornalieri": {
            "trasferta_italia": 50.00,
            "trasferta_estero": 85.00,
            "pasto": 10.00,
            "lavoro_agile": 3.50,
        },
        "massimale_km": 0.45,
        "massimale_notte": 170.00,
        "plafond_mensile": 1400.00,
        "riferimento": "Circolare MEF n. 18/2026",
        # Riduzione progressiva trasferte estere > 5 giorni (Sez. 4): tariffa per fascia.
        "riduzione_estero": {
            "piena": 85.00,       # 1ª – 5ª giornata
            "ridotta_10": 76.50,  # 6ª – 10ª giornata (−10%)
            "ridotta_20": 68.00,  # 11ª giornata in poi (−20%)
        },
    },
}

# Indennità lavoro agile (Sez. 3, dal 01/01/2026): massimo di giornate esenti al mese.
MAX_GIORNATE_AGILE = 12

CATEGORIE = {
    "trasferta_italia": "Trasferta in Italia",
    "trasferta_estero": "Trasferta all'estero",
    "pasto": "Rimborso pasto",
    "chilometrico": "Rimborso chilometrico",
    "alloggio": "Rimborso alloggio",
    "lavoro_agile": "Indennità lavoro agile",
}

CATEGORIE_A_GIORNATE = ("trasferta_italia", "trasferta_estero", "pasto", "lavoro_agile")


def _regime(data):
    """Parametri del regime applicabile alla `data` di sostenimento.

    `data` è una stringa ISO (`AAAA-MM-GG`) o un mese (`AAAA-MM`): in entrambi i casi
    i primi 4 caratteri sono l'anno. Dal 2026 si applica la Circolare 18/2026.
    """
    anno = int(data[:4])
    return _PARAMETRI[2026] if anno >= 2026 else _PARAMETRI[2025]


def regime_2026(data):
    """True se alla `data` di sostenimento si applica il regime 18/2026.

    Unico punto, insieme a `_regime`, che conosce la soglia del regime transitorio:
    le regole introdotte dal 2026 (lavoro agile, incompatibilità, riduzione estero)
    devono derivare da qui, non da confronti d'anno sparsi nel codice.
    """
    return _regime(data) is _PARAMETRI[2026]


def massimali_giornalieri(data):
    return _regime(data)["massimali_giornalieri"]


def massimale_km(data):
    return _regime(data)["massimale_km"]


def massimale_notte(data):
    return _regime(data)["massimale_notte"]


def plafond_mensile(data):
    return _regime(data)["plafond_mensile"]


def riduzione_estero(data):
    """Tariffe per fascia delle trasferte estere, o None se il regime non la prevede."""
    return _regime(data).get("riduzione_estero")


def regime_corrente():
    """Parametri del regime in vigore alla data odierna, per la pagina normativa."""
    return _regime(date.today().isoformat())
