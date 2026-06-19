// Mostra solo i campi quantità pertinenti alla categoria selezionata.
const CAMPI_PER_CATEGORIA = {
  trasferta_italia: "giorni",
  trasferta_estero: "giorni",
  pasto: "giorni",
  chilometrico: "km",
  alloggio: "notti",
  lavoro_agile: "giorni",
};

const selettoreCategoria = document.getElementById("categoria");
if (selettoreCategoria) {
  const aggiornaCampi = () => {
    const campoAttivo = CAMPI_PER_CATEGORIA[selettoreCategoria.value];
    document.querySelectorAll("[data-campo]").forEach((label) => {
      const attivo = label.dataset.campo === campoAttivo;
      label.hidden = !attivo;
      label.querySelector("input").required = attivo;
      if (!attivo) label.querySelector("input").value = "";
    });
  };
  selettoreCategoria.addEventListener("change", aggiornaCampi);
  aggiornaCampi();
}

// Elenco richieste: clic su una riga per aprire/chiudere il dettaglio del calcolo.
document.querySelectorAll(".riga-richiesta").forEach((riga) => {
  riga.addEventListener("click", () => {
    const dettaglio = riga.nextElementSibling;
    if (dettaglio && dettaglio.classList.contains("riga-dettaglio")) {
      dettaglio.hidden = !dettaglio.hidden;
    }
  });
});
