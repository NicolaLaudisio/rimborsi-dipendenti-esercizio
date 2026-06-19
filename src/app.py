"""Webapp Flask per la gestione dei rimborsi spese dei dipendenti."""

from flask import Flask, redirect, render_template, request, url_for

from src import calculator, rules, storage, validator

app = Flask(__name__)


def _numero(valore):
    try:
        return float(valore)
    except (TypeError, ValueError):
        return None


def _intero(valore):
    try:
        return int(valore)
    except (TypeError, ValueError):
        return None


def _registra(form):
    """Valida, calcola e registra una nuova richiesta. Restituisce la richiesta salvata."""
    richieste = storage.carica()
    richiesta = {
        "id": storage.prossimo_id(richieste),
        "dipendente": (form.get("dipendente") or "").strip(),
        "data": form.get("data") or "",
        "categoria": form.get("categoria") or "",
        "importo": _numero(form.get("importo")),
        "giorni": _intero(form.get("giorni")),
        "km": _numero(form.get("km")),
        "notti": _intero(form.get("notti")),
    }
    ok, motivazione = validator.valida(richiesta)
    if ok:
        ok, motivazione = validator.compatibile(richiesta, richieste)
    richiesta.update(
        stato="valida" if ok else "respinta",
        motivazione="" if ok else motivazione,
        quota_esente=0.0,
        quota_imponibile=0.0,
        dettaglio=None,
    )
    richieste.append(richiesta)
    # Una nuova richiesta valida può cambiare la ripartizione del plafond delle altre
    # richieste dello stesso mese: si ricalcola l'intero gruppo in ordine di data (Sez. 1).
    if ok:
        _ricalcola_mese(richieste, richiesta["dipendente"], storage.mese(richiesta))
    storage.salva(richieste)
    return richiesta


def _ricalcola_mese(richieste, dipendente, mese):
    """Riallinea le quote del gruppo (dipendente, mese) imputando il plafond per data."""
    gruppo = sorted(
        (
            r
            for r in richieste
            if r["stato"] == "valida"
            and r["dipendente"] == dipendente
            and storage.mese(r) == mese
        ),
        key=lambda r: (r["data"], r["id"]),
    )
    for r, (esente, imponibile, dettaglio) in zip(
        gruppo, calculator.ripartisci_mese(gruppo)
    ):
        r.update(
            quota_esente=esente, quota_imponibile=imponibile, dettaglio=dettaglio
        )


@app.get("/")
def home():
    return redirect(url_for("elenco"))


@app.route("/nuova", methods=["GET", "POST"])
def nuova_richiesta():
    esito = None
    if request.method == "POST":
        esito = _registra(request.form)
    return render_template("nuova_richiesta.html", categorie=rules.CATEGORIE, esito=esito)


@app.get("/richieste")
def elenco():
    richieste = storage.carica()
    dipendente = request.args.get("dipendente", "")
    mese = request.args.get("mese", "")
    filtrate = [
        r
        for r in richieste
        if (not dipendente or r["dipendente"] == dipendente)
        and (not mese or storage.mese(r) == mese)
    ]
    filtrate.sort(key=lambda r: (r["data"], r["id"]), reverse=True)
    return render_template(
        "elenco.html",
        richieste=filtrate,
        categorie=rules.CATEGORIE,
        dipendenti=sorted({r["dipendente"] for r in richieste}),
        mesi=sorted({storage.mese(r) for r in richieste}, reverse=True),
        filtro_dipendente=dipendente,
        filtro_mese=mese,
    )


@app.get("/riepilogo")
def riepilogo():
    richieste = storage.carica()
    gruppi = {}
    for r in richieste:
        if r["stato"] != "valida":
            continue
        chiave = (storage.mese(r), r["dipendente"])
        gruppo = gruppi.setdefault(
            chiave, {"esente": 0.0, "imponibile": 0.0, "richieste": 0}
        )
        gruppo["esente"] = round(gruppo["esente"] + r["quota_esente"], 2)
        gruppo["imponibile"] = round(gruppo["imponibile"] + r["quota_imponibile"], 2)
        gruppo["richieste"] += 1
    righe = []
    for (mese, dipendente), dati in sorted(gruppi.items(), reverse=True):
        plafond = rules.plafond_mensile(mese)
        righe.append(
            {
                "mese": mese,
                "dipendente": dipendente,
                "esente": dati["esente"],
                "imponibile": dati["imponibile"],
                "richieste": dati["richieste"],
                "plafond": plafond,
                "percentuale_plafond": min(round(dati["esente"] / plafond * 100), 100),
            }
        )
    return render_template("riepilogo.html", righe=righe)


@app.get("/normativa")
def normativa():
    return render_template(
        "normativa.html", regime=rules.regime_corrente(), categorie=rules.CATEGORIE
    )


if __name__ == "__main__":
    app.run(debug=True)
