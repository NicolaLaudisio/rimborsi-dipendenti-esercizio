from src import calculator, rules


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


class TestMassimaleTeorico:
    def test_trasferta_italia(self):
        r = richiesta(categoria="trasferta_italia", giorni=4)
        assert calculator.massimale_teorico(r) == 185.92

    def test_trasferta_estero(self):
        r = richiesta(categoria="trasferta_estero", giorni=3)
        assert calculator.massimale_teorico(r) == 232.41

    def test_pasto(self):
        r = richiesta(categoria="pasto", giorni=5)
        assert calculator.massimale_teorico(r) == 40.0

    def test_chilometrico(self):
        r = richiesta(categoria="chilometrico", km=250)
        assert calculator.massimale_teorico(r) == 105.0

    def test_alloggio(self):
        r = richiesta(categoria="alloggio", notti=2)
        assert calculator.massimale_teorico(r) == 300.0


class TestCalcola:
    def test_importo_sotto_massimale_tutto_esente(self):
        r = richiesta(categoria="pasto", giorni=5, importo=35.0)
        esente, imponibile, _ = calculator.calcola(r, esente_gia_riconosciuta=0.0)
        assert esente == 35.0
        assert imponibile == 0.0

    def test_importo_sopra_massimale_eccedenza_imponibile(self):
        r = richiesta(categoria="trasferta_italia", giorni=2, importo=120.0)
        esente, imponibile, _ = calculator.calcola(r, esente_gia_riconosciuta=0.0)
        assert esente == 92.96
        assert imponibile == 27.04

    def test_plafond_incapiente_limita_la_quota_esente(self):
        r = richiesta(categoria="alloggio", notti=2, importo=300.0)
        esente, imponibile, _ = calculator.calcola(r, esente_gia_riconosciuta=1100.0)
        assert esente == 100.0
        assert imponibile == 200.0

    def test_plafond_esaurito_tutto_imponibile(self):
        r = richiesta(categoria="pasto", giorni=1, importo=8.0)
        esente, imponibile, _ = calculator.calcola(r, esente_gia_riconosciuta=1200.0)
        assert esente == 0.0
        assert imponibile == 8.0

    def test_dettaglio_del_calcolo(self):
        r = richiesta(categoria="trasferta_estero", giorni=2, importo=200.0)
        _, _, dettaglio = calculator.calcola(r, esente_gia_riconosciuta=1100.0)
        assert dettaglio == {
            "massimale_teorico": 154.94,
            "esente_teorica": 154.94,
            "capienza_plafond": 100.0,
        }


class TestRegimePerData:
    """Dispatch transitorio: spese <= 2025 col vecchio regime, dal 2026 col nuovo."""

    def test_massimale_pasto_alla_soglia_2025(self):
        r = richiesta(categoria="pasto", giorni=1, data="2025-12-31")
        assert calculator.massimale_teorico(r) == 8.00

    def test_massimale_pasto_alla_soglia_2026(self):
        r = richiesta(categoria="pasto", giorni=1, data="2026-01-01")
        assert calculator.massimale_teorico(r) == 10.00

    def test_plafond_2025_alla_soglia(self):
        # Plafond 1200: con 1199 già usati resta 1 € di capienza.
        r = richiesta(categoria="pasto", giorni=1, importo=8.0, data="2025-12-31")
        esente, _, _ = calculator.calcola(r, esente_gia_riconosciuta=1199.0)
        assert esente == 1.0

    def test_plafond_2026_alla_soglia(self):
        # Plafond 1400: con 1399 già usati resta 1 € di capienza.
        r = richiesta(categoria="pasto", giorni=1, importo=8.0, data="2026-01-01")
        esente, _, _ = calculator.calcola(r, esente_gia_riconosciuta=1399.0)
        assert esente == 1.0

    def test_caso_6_6_spesa_2025_presentata_nel_2026(self):
        # Caso 6.6: pasto 3 giorni, data 18/12/2025 → massimale 24,00, plafond mese = 1200.
        r = richiesta(categoria="pasto", giorni=3, data="2025-12-18")
        assert calculator.massimale_teorico(r) == 24.00
        assert rules.plafond_mensile("2025-12") == 1200.0


class TestMassimaleTeorico2026:
    """Massimali aggiornati dal 01/01/2026 (estero piatto: niente riduzione Sez.4)."""

    def test_trasferta_italia(self):
        r = richiesta(categoria="trasferta_italia", giorni=2, data="2026-03-10")
        assert calculator.massimale_teorico(r) == 100.0

    def test_trasferta_estero(self):
        r = richiesta(categoria="trasferta_estero", giorni=3, data="2026-03-10")
        assert calculator.massimale_teorico(r) == 255.0

    def test_pasto(self):
        r = richiesta(categoria="pasto", giorni=5, data="2026-03-10")
        assert calculator.massimale_teorico(r) == 50.0

    def test_chilometrico(self):
        r = richiesta(categoria="chilometrico", km=100, data="2026-03-10")
        assert calculator.massimale_teorico(r) == 45.0

    def test_alloggio(self):
        r = richiesta(categoria="alloggio", notti=2, data="2026-03-10")
        assert calculator.massimale_teorico(r) == 340.0

    def test_plafond_capienza_residua(self):
        # Caso 6.1 della circolare: già riconosciuti 1350 €, capienza 50 € sul plafond 1400.
        r = richiesta(categoria="pasto", giorni=5, importo=50.0, data="2026-03-10")
        esente, imponibile, dettaglio = calculator.calcola(
            r, esente_gia_riconosciuta=1350.0
        )
        assert esente == 50.0
        assert imponibile == 0.0
        assert dettaglio["capienza_plafond"] == 50.0

    def test_plafond_capienza_parziale(self):
        # Caso 6.1 (seconda parte): già riconosciuti 1380 €, capienza 20 € → esente 20.
        r = richiesta(categoria="pasto", giorni=5, importo=50.0, data="2026-03-10")
        esente, imponibile, dettaglio = calculator.calcola(
            r, esente_gia_riconosciuta=1380.0
        )
        assert esente == 20.0
        assert imponibile == 30.0
        assert dettaglio["capienza_plafond"] == 20.0


class TestLavoroAgile:
    """Sez. 3: 3,50 €/giorno, max 12 giornate/mese (dal 01/01/2026)."""

    def test_massimale_base(self):
        r = richiesta(categoria="lavoro_agile", giorni=1, data="2026-03-10")
        assert calculator.massimale_teorico(r) == 3.50

    def test_cap_12_giornate(self):
        # Caso 6.4: 15 giornate, 0 già rimborsate → ammesse 12 → 42,00 €.
        r = richiesta(categoria="lavoro_agile", giorni=15, data="2026-03-10")
        assert calculator.massimale_teorico(r) == 42.00

    def test_cap_12_giornate_calcolo_completo(self):
        # Caso 6.4: importo 52,50 → esente 42,00, imponibile 10,50.
        r = richiesta(
            categoria="lavoro_agile", giorni=15, importo=52.50, data="2026-03-10"
        )
        esente, imponibile, _ = calculator.calcola(r, esente_gia_riconosciuta=0.0)
        assert esente == 42.00
        assert imponibile == 10.50

    def test_giornate_gia_rimborsate_riducono_le_ammesse(self):
        # Sez. 3 esempio: 8 già rimborsate, richiesti 6 → ammesse 4 → 14,00 €.
        r = richiesta(categoria="lavoro_agile", giorni=6, data="2026-03-10")
        assert calculator.massimale_teorico(r, giornate_agile_nel_mese=8) == 14.00

    def test_limite_mensile_esaurito(self):
        # 12 giornate già rimborsate → ammesse 0 → massimale 0,00 €.
        r = richiesta(categoria="lavoro_agile", giorni=5, data="2026-03-10")
        assert calculator.massimale_teorico(r, giornate_agile_nel_mese=12) == 0.00


class TestRiduzioneEstero2026:
    """Sez. 4: trasferte estere > 5 giorni dal 01/01/2026, riduzione progressiva."""

    def test_sei_giorni(self):
        # Caso 6.2: (5 × 85) + (1 × 76,50) = 501,50 €.
        r = richiesta(categoria="trasferta_estero", giorni=6, data="2026-04-01")
        assert calculator.massimale_teorico(r) == 501.50

    def test_sei_giorni_calcolo_completo(self):
        # Caso 6.2: importo 500 → tutto esente, niente imponibile.
        r = richiesta(
            categoria="trasferta_estero", giorni=6, importo=500.0, data="2026-04-01"
        )
        esente, imponibile, _ = calculator.calcola(r, esente_gia_riconosciuta=0.0)
        assert esente == 500.0
        assert imponibile == 0.0

    def test_dodici_giorni(self):
        # Sez. 4 esempio: (5 × 85) + (5 × 76,50) + (2 × 68) = 943,50 €.
        r = richiesta(categoria="trasferta_estero", giorni=12, data="2026-04-01")
        assert calculator.massimale_teorico(r) == 943.50

    def test_cinque_giorni_esatti_nessuna_riduzione(self):
        # Caso 6.3: 5 × 85 = 425,00 €, nessuna riduzione.
        r = richiesta(categoria="trasferta_estero", giorni=5, data="2026-04-01")
        assert calculator.massimale_teorico(r) == 425.00

    def test_estero_2025_resta_piatto(self):
        # Caso 6.7: la riduzione non si applica alle trasferte 2025.
        r = richiesta(categoria="trasferta_estero", giorni=12, data="2025-07-01")
        assert calculator.massimale_teorico(r) == 929.64

    def test_caso_6_7_trasferta_a_cavallo_anno(self):
        # Caso 6.7: trasferta estera iniziata nel 2025 (data di inizio) → intera previgente,
        # 77,47 €/g senza riduzione progressiva, anche se prosegue nel 2026.
        r = richiesta(categoria="trasferta_estero", giorni=10, data="2025-12-28")
        assert calculator.massimale_teorico(r) == 774.70

    def test_trasferta_italia_non_ridotta(self):
        r = richiesta(categoria="trasferta_italia", giorni=8, data="2026-04-01")
        assert calculator.massimale_teorico(r) == 400.00

    def test_arrotondamento_aritmetico(self):
        # Sez. 2: arrotondamento aritmetico (half-up), non "bankers'".
        # 0,45 × 4,5 = 2,025 → 2,03 € (half-up), non 2,02 (half-to-even).
        r = richiesta(categoria="chilometrico", km=4.5, data="2026-04-01")
        assert calculator.massimale_teorico(r) == 2.03


class TestRipartisciMese:
    """Sez. 1: il plafond è imputato in ordine di data; allocazione sequenziale."""

    def test_allocazione_sequenziale(self):
        # Due alloggi da 1360 €, plafond 1400: il primo pieno, il secondo solo la capienza.
        primo = richiesta(
            categoria="alloggio", notti=8, importo=1360.0, data="2026-05-10", giorni=None
        )
        secondo = richiesta(
            categoria="alloggio", notti=8, importo=1360.0, data="2026-05-20", giorni=None
        )
        risultati = calculator.ripartisci_mese([primo, secondo])
        assert risultati[0][0] == 1360.0  # esente del primo
        assert risultati[1][0] == 40.0    # esente del secondo (1400 - 1360)

    def test_cumulo_giornate_agile(self):
        # Due richieste agile: il cap 12 giornate si applica progressivamente.
        primo = richiesta(
            categoria="lavoro_agile", giorni=10, importo=35.0, data="2026-05-05"
        )
        secondo = richiesta(
            categoria="lavoro_agile", giorni=5, importo=17.5, data="2026-05-15"
        )
        risultati = calculator.ripartisci_mese([primo, secondo])
        assert risultati[0][0] == 35.0  # 10 giornate × 3,50
        assert risultati[1][0] == 7.0   # ammesse 2 (12 - 10) × 3,50
