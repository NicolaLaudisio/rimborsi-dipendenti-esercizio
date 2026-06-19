import pytest

from src import storage
from src.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PERCORSO_DATI", tmp_path / "richieste.json")
    app.config["TESTING"] = True
    return app.test_client()


def nuova_richiesta_pasto(client, **campi):
    dati = {
        "dipendente": "Maria Rossi",
        "data": "2025-10-06",
        "categoria": "pasto",
        "importo": "24.00",
        "giorni": "3",
    }
    dati.update(campi)
    return client.post("/nuova", data=dati)


def test_home_reindirizza_a_elenco(client):
    risposta = client.get("/")
    assert risposta.status_code == 302
    assert "/richieste" in risposta.headers["Location"]


def test_pagine_principali_raggiungibili(client):
    for percorso in ("/richieste", "/nuova", "/riepilogo", "/normativa"):
        assert client.get(percorso).status_code == 200


def test_registrazione_richiesta_valida(client):
    risposta = nuova_richiesta_pasto(client)
    assert risposta.status_code == 200
    assert "registrata" in risposta.get_data(as_text=True)

    richieste = storage.carica()
    assert len(richieste) == 1
    assert richieste[0]["stato"] == "valida"
    assert richieste[0]["quota_esente"] == 24.0
    assert richieste[0]["quota_imponibile"] == 0.0


def test_registrazione_richiesta_respinta(client):
    risposta = nuova_richiesta_pasto(client, importo="-10")
    assert "respinta" in risposta.get_data(as_text=True)
    assert "importo non positivo" in risposta.get_data(as_text=True)

    richieste = storage.carica()
    assert richieste[0]["stato"] == "respinta"
    assert richieste[0]["quota_esente"] == 0.0


def test_eccedenza_oltre_massimale_diventa_imponibile(client):
    nuova_richiesta_pasto(client, importo="30.00", giorni="3")
    richieste = storage.carica()
    assert richieste[0]["quota_esente"] == 24.0
    assert richieste[0]["quota_imponibile"] == 6.0


def test_plafond_mensile_condiviso_tra_richieste(client):
    nuova_richiesta_pasto(
        client, categoria="alloggio", notti="8", importo="1150.00", giorni=""
    )
    nuova_richiesta_pasto(client, importo="80.00", giorni="10")
    richieste = storage.carica()
    assert richieste[0]["quota_esente"] == 1150.0
    # Capienza residua: 1200 - 1150 = 50, quindi del pasto sono esenti solo 50.
    assert richieste[1]["quota_esente"] == 50.0
    assert richieste[1]["quota_imponibile"] == 30.0


def test_registrazione_lavoro_agile(client):
    nuova_richiesta_pasto(
        client,
        data="2026-03-10",
        categoria="lavoro_agile",
        importo="10.50",
        giorni="3",
    )
    richieste = storage.carica()
    assert richieste[0]["stato"] == "valida"
    assert richieste[0]["quota_esente"] == 10.50
    assert richieste[0]["quota_imponibile"] == 0.0


def test_lavoro_agile_cap_mensile_tra_richieste(client):
    # 10 giornate, poi altre 5: la seconda è limitata a 2 giornate ammesse (12 - 10).
    nuova_richiesta_pasto(
        client, data="2026-03-05", categoria="lavoro_agile", importo="35.00", giorni="10"
    )
    nuova_richiesta_pasto(
        client, data="2026-03-20", categoria="lavoro_agile", importo="17.50", giorni="5"
    )
    richieste = storage.carica()
    assert richieste[0]["quota_esente"] == 35.0
    # Ammesse = min(5, 12 - 10) = 2 → massimale 7,00 €.
    assert richieste[1]["quota_esente"] == 7.0
    assert richieste[1]["quota_imponibile"] == 10.5


def test_incompatibilita_agile_trasferta_respinge(client):
    nuova_richiesta_pasto(
        client,
        data="2026-03-02",
        categoria="trasferta_italia",
        importo="200.00",
        giorni="5",
    )
    nuova_richiesta_pasto(
        client,
        data="2026-03-06",
        categoria="lavoro_agile",
        importo="10.50",
        giorni="3",
    )
    richieste = storage.carica()
    assert richieste[1]["stato"] == "respinta"
    assert richieste[1]["motivazione"] == "incompatibilità lavoro agile / trasferta"
    assert richieste[1]["quota_esente"] == 0.0
    assert richieste[1]["dettaglio"] is None


def test_plafond_imputato_per_data_non_per_inserimento(client):
    # Inserisco prima la richiesta con data POSTERIORE, poi quella anteriore:
    # il plafond deve dare priorità alla data anteriore (Sez. 1), riscrivendo la prima.
    nuova_richiesta_pasto(
        client,
        data="2026-05-20",
        categoria="alloggio",
        notti="8",
        importo="1360.00",
        giorni="",
    )
    nuova_richiesta_pasto(
        client,
        data="2026-05-10",
        categoria="alloggio",
        notti="8",
        importo="1360.00",
        giorni="",
    )
    richieste = storage.carica()
    # richieste[0] = data posteriore (inserita per prima) → ridotta alla capienza residua
    assert richieste[0]["data"] == "2026-05-20"
    assert richieste[0]["quota_esente"] == 40.0
    # richieste[1] = data anteriore → piena
    assert richieste[1]["data"] == "2026-05-10"
    assert richieste[1]["quota_esente"] == 1360.0


def test_plafond_pareggio_data_ordina_per_id(client):
    nuova_richiesta_pasto(
        client, data="2026-06-01", categoria="alloggio", notti="8", importo="1360.00", giorni=""
    )
    nuova_richiesta_pasto(
        client, data="2026-06-01", categoria="alloggio", notti="8", importo="1360.00", giorni=""
    )
    richieste = storage.carica()
    # Stessa data → vince l'ordine di presentazione (id): la prima inserita resta piena.
    assert richieste[0]["quota_esente"] == 1360.0
    assert richieste[1]["quota_esente"] == 40.0


def test_elenco_filtra_per_dipendente(client):
    nuova_richiesta_pasto(client, dipendente="Maria Rossi")
    nuova_richiesta_pasto(client, dipendente="Luca Bianchi")
    testo = client.get("/richieste?dipendente=Luca+Bianchi").get_data(as_text=True)
    assert "Luca Bianchi" in testo
    assert "Maria Rossi" not in testo.split("</thead>")[1].split("Clicca")[0]


def test_riepilogo_mostra_totali(client):
    nuova_richiesta_pasto(client)
    nuova_richiesta_pasto(client, importo="16.00", giorni="2")
    testo = client.get("/riepilogo").get_data(as_text=True)
    assert "Maria Rossi" in testo
    assert "40.00" in testo


def test_form_nuova_include_lavoro_agile(client):
    testo = client.get("/nuova").get_data(as_text=True)
    assert 'value="lavoro_agile"' in testo
    assert "Indennità lavoro agile" in testo


def test_normativa_mostra_massimali_vigenti(client):
    # La pagina mostra il regime in vigore oggi (2026): massimali e plafond aggiornati.
    testo = client.get("/normativa").get_data(as_text=True)
    assert "50.00" in testo
    assert "85.00" in testo
    assert "1400.00" in testo


def test_plafond_2026_condiviso_tra_richieste(client):
    # Stesso meccanismo del plafond mensile, ma su date 2026: capienza su 1400 €.
    nuova_richiesta_pasto(
        client,
        data="2026-02-10",
        categoria="alloggio",
        notti="8",
        importo="1360.00",
        giorni="",
    )
    nuova_richiesta_pasto(client, data="2026-02-11", importo="80.00", giorni="8")
    richieste = storage.carica()
    assert richieste[0]["quota_esente"] == 1360.0
    # Capienza residua: 1400 - 1360 = 40, quindi del pasto sono esenti solo 40.
    assert richieste[1]["quota_esente"] == 40.0
    assert richieste[1]["quota_imponibile"] == 40.0
