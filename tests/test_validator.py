from datetime import date, timedelta

from src import validator


def richiesta(**campi):
    base = {
        "dipendente": "Maria Rossi",
        "data": "2025-10-06",
        "categoria": "pasto",
        "importo": 10.0,
        "giorni": 1,
        "km": None,
        "notti": None,
    }
    base.update(campi)
    return base


def test_richiesta_valida():
    assert validator.valida(richiesta()) == (True, "")


def test_dipendente_mancante():
    ok, motivazione = validator.valida(richiesta(dipendente=""))
    assert not ok
    assert motivazione == "dipendente mancante"


def test_categoria_non_riconosciuta():
    ok, motivazione = validator.valida(richiesta(categoria="parcheggio"))
    assert not ok
    assert motivazione == "categoria non riconosciuta"


def test_importo_zero():
    ok, motivazione = validator.valida(richiesta(importo=0))
    assert not ok
    assert motivazione == "importo non positivo"


def test_importo_negativo():
    ok, motivazione = validator.valida(richiesta(importo=-5.0))
    assert not ok
    assert motivazione == "importo non positivo"


def test_importo_mancante():
    ok, motivazione = validator.valida(richiesta(importo=None))
    assert not ok
    assert motivazione == "importo non positivo"


def test_data_mancante():
    ok, motivazione = validator.valida(richiesta(data=""))
    assert not ok
    assert motivazione == "data mancante o non valida"


def test_data_non_valida():
    ok, motivazione = validator.valida(richiesta(data="06/10/2025"))
    assert not ok
    assert motivazione == "data mancante o non valida"


def test_data_futura():
    # Sez. 5: la data di sostenimento non può essere successiva alla presentazione.
    futura = (date.today() + timedelta(days=1)).isoformat()
    ok, motivazione = validator.valida(richiesta(data=futura))
    assert not ok
    assert motivazione == "data successiva alla presentazione"


def test_data_odierna_ammessa():
    oggi = date.today().isoformat()
    assert validator.valida(richiesta(data=oggi)) == (True, "")


def test_giornate_mancanti_per_trasferta():
    ok, motivazione = validator.valida(
        richiesta(categoria="trasferta_italia", giorni=None)
    )
    assert not ok
    assert motivazione == "numero di giornate non valido"


def test_giornate_zero_per_pasto():
    ok, motivazione = validator.valida(richiesta(categoria="pasto", giorni=0))
    assert not ok
    assert motivazione == "numero di giornate non valido"


def test_chilometri_non_validi():
    ok, motivazione = validator.valida(
        richiesta(categoria="chilometrico", km=0)
    )
    assert not ok
    assert motivazione == "numero di chilometri non valido"


def test_notti_non_valide():
    ok, motivazione = validator.valida(
        richiesta(categoria="alloggio", notti=None)
    )
    assert not ok
    assert motivazione == "numero di notti non valido"


def test_chilometrico_valido():
    assert validator.valida(
        richiesta(categoria="chilometrico", km=120, giorni=None)
    ) == (True, "")


def test_alloggio_valido():
    assert validator.valida(
        richiesta(categoria="alloggio", notti=3, giorni=None)
    ) == (True, "")


def test_lavoro_agile_valido_dal_2026():
    assert validator.valida(
        richiesta(categoria="lavoro_agile", data="2026-03-10", giorni=3)
    ) == (True, "")


def test_lavoro_agile_non_ammesso_prima_del_2026():
    ok, motivazione = validator.valida(
        richiesta(categoria="lavoro_agile", data="2025-12-31", giorni=3)
    )
    assert not ok
    assert motivazione == "categoria non riconosciuta"


def test_lavoro_agile_giornate_non_valide():
    ok, motivazione = validator.valida(
        richiesta(categoria="lavoro_agile", data="2026-03-10", giorni=0)
    )
    assert not ok
    assert motivazione == "numero di giornate non valido"


def esistente(**campi):
    base = richiesta()
    base.update(stato="valida")
    base.update(campi)
    return base


CONFLITTO = "incompatibilità lavoro agile / trasferta"


class TestIncompatibilitaAgileTrasferta:
    """Sez. 5: lavoro agile e trasferta non cumulabili nella stessa giornata (dal 2026)."""

    def test_agile_su_giornata_di_trasferta(self):
        # Caso 6.5: trasferta 02–06/03, nuovo agile 06–08/03 → sovrapposto il 06/03.
        trasferta = esistente(
            categoria="trasferta_italia", data="2026-03-02", giorni=5
        )
        nuova = richiesta(categoria="lavoro_agile", data="2026-03-06", giorni=3)
        assert validator.compatibile(nuova, [trasferta]) == (False, CONFLITTO)

    def test_trasferta_su_giornata_di_agile(self):
        # Bidirezionale: agile esistente, nuova trasferta sovrapposta.
        agile = esistente(categoria="lavoro_agile", data="2026-03-06", giorni=3)
        nuova = richiesta(categoria="trasferta_italia", data="2026-03-02", giorni=5)
        assert validator.compatibile(nuova, [agile]) == (False, CONFLITTO)

    def test_senza_sovrapposizione_ok(self):
        trasferta = esistente(
            categoria="trasferta_italia", data="2026-03-02", giorni=4
        )  # 02–05
        nuova = richiesta(categoria="lavoro_agile", data="2026-03-06", giorni=3)  # 06–08
        assert validator.compatibile(nuova, [trasferta]) == (True, "")

    def test_richiesta_respinta_non_blocca(self):
        trasferta = esistente(
            categoria="trasferta_italia", data="2026-03-02", giorni=5, stato="respinta"
        )
        nuova = richiesta(categoria="lavoro_agile", data="2026-03-06", giorni=3)
        assert validator.compatibile(nuova, [trasferta]) == (True, "")

    def test_altro_dipendente_non_blocca(self):
        trasferta = esistente(
            categoria="trasferta_italia",
            data="2026-03-02",
            giorni=5,
            dipendente="Luca Bianchi",
        )
        nuova = richiesta(categoria="lavoro_agile", data="2026-03-06", giorni=3)
        assert validator.compatibile(nuova, [trasferta]) == (True, "")

    def test_nessun_controllo_prima_del_2026(self):
        trasferta = esistente(
            categoria="trasferta_italia", data="2025-03-02", giorni=5
        )
        nuova = richiesta(categoria="lavoro_agile", data="2025-03-06", giorni=3)
        assert validator.compatibile(nuova, [trasferta]) == (True, "")
