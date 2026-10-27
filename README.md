# Tabella segnali giornaliera (soldi finti)

Ogni giorno un programma scarica i prezzi, calcola un punteggio per ogni strumento e aggiorna una pagina web che puoi aprire dal telefono (anche da Telegram). Simula anche un portafoglio virtuale da 10.000 €.
Solo scopo didattico, non è consulenza finanziaria.

## Cosa c'è nella cartella

- `aggiorna.py`: scarica i prezzi, calcola punteggi e segnali, gestisce il portafoglio virtuale.
- `index.html`: la pagina con la tabella.
- `.github/workflows/aggiorna.yml`: dice a GitHub di eseguire tutto ogni mattina, gratis.

## Messa online (una volta sola, circa 15 minuti)

1. **Account GitHub.** Vai su github.com e crea un account gratuito.
2. **Nuovo repository.** Clicca su "+" in alto a destra, poi "New repository". Nome a scelta (es. `tabella-trading`), lascialo **Public** (serve per le pagine gratuite; contiene solo soldi finti). Clicca "Create repository".
3. **Carica i file.** Nella pagina del repository scegli "uploading an existing file" e trascina `aggiorna.py` e `index.html`. Poi clicca "Commit changes".
4. **Aggiungi il workflow.** Clicca "Add file" > "Create new file". Nel campo del nome scrivi esattamente `.github/workflows/aggiorna.yml` (le barre creano le cartelle). Incolla il contenuto del file `aggiorna.yml` e clicca "Commit changes".
5. **Permessi.** Vai su Settings > Actions > General, in fondo "Workflow permissions": scegli "Read and write permissions" e salva.
6. **Attiva le pagine.** Vai su Settings > Pages. In "Source" scegli **GitHub Actions**.
7. **Primo avvio.** Vai nella scheda Actions, clicca "Aggiorna tabella" a sinistra, poi "Run workflow". Dopo 1-2 minuti il pallino diventa verde. Se diventa rosso, aprilo e mandami il messaggio di errore.
8. **Apri la pagina.** L'indirizzo è `https://IL-TUO-NOME-UTENTE.github.io/NOME-REPOSITORY/`. Salvalo nei "Messaggi salvati" di Telegram: da lì lo apri dal telefono.

Da questo momento si aggiorna da sola ogni mattina (circa 07:30-08:30 italiane, con i prezzi dell'ultima chiusura).

## Come funziona il punteggio (0-100)

- 40 punti di **trend**: prezzo sopra la media a 50 giorni (20) e sopra la media a 200 giorni (20).
- 40 punti di **momentum**: rendimento medio a 3 e 6 mesi, confrontato con gli altri della stessa categoria.
- 20 punti di **stabilità**: meno volatilità, più punti.

Segnale: **COMPRA** se il punteggio è almeno 65 e il prezzo è sopra la media a 50 giorni; **EVITA** se è sotto 40 o il prezzo è sotto la media a 200 giorni; altrimenti **MANTIENI**.

## Come funziona il portafoglio virtuale

- Parte da 10.000 € finti, 20% massimo per categoria.
- Compra (a quote frazionarie) gli strumenti che passano a COMPRA e vende quelli che passano a EVITA.
- I prezzi in dollari vengono convertiti in euro con il cambio del giorno. Commissioni e tasse non sono simulate.

## Modificare la lista degli strumenti

Apri `aggiorna.py` su GitHub (icona matita) e cambia le righe in `UNIVERSO`. Il ticker è quello di Yahoo Finance (es. `ENI.MI`). Massimo 10 per categoria. I ticker senza dati compaiono in fondo alla pagina, così sai quali correggere.
