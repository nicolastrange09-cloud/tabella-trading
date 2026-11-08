#!/usr/bin/env python3
"""Aggiorna la tabella dei segnali e il portafoglio virtuale.

Solo scopo didattico: soldi finti, nessuna consulenza finanziaria.
Uso:  python aggiorna.py   ->  scrive data.json e portfolio.json
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

# ----------------------------------------------------------------- impostazioni
CAPITALE_INIZIALE = 1000.0   # euro
QUOTA_CATEGORIA = 0.20       # 20% del capitale per ognuna delle 5 categorie
SOGLIA_COMPRA = 65           # punteggio minimo per il segnale COMPRA
SOGLIA_EVITA = 40            # sotto questo punteggio: EVITA
SOGLIA_FORTE = 70            # punteggio da cui il consiglio è "SI" (il portafoglio compra solo da qui)
STOP_PERDITA = 0.05          # vende se la perdita supera il 5% e il segnale non è più COMPRA
# Volatilità annua massima per COMPRARE (si applica solo agli acquisti: le posizioni
# già aperte restano sempre monitorate e vendibili). Soglie diverse per categoria,
# perché una crypto non è mai stabile quanto un'obbligazione.
MAX_VOL = {"ETF": 0.25, "Obbligazioni": 0.20, "Azioni": 0.40,
           "Crypto": 0.90, "Materie prime": 0.40}

# Massimo 10 strumenti per categoria. (ticker Yahoo Finance, nome)
# I ticker che non danno dati vengono saltati e compaiono in "errori" di data.json.
UNIVERSO = {
    "ETF": [
        ("SWDA.MI", "iShares Core MSCI World"),
        ("CSSPX.MI", "iShares Core S&P 500"),
        ("EIMI.MI", "iShares Core MSCI Emerging Markets"),
        ("VWCE.MI", "Vanguard FTSE All-World"),
        ("SMEA.MI", "iShares Core MSCI Europe"),
        ("MEUD.MI", "Amundi Stoxx Europe 600"),
        ("CNDX.MI", "iShares Nasdaq 100"),
        ("ISAC.MI", "iShares MSCI ACWI"),
    ],
    "Obbligazioni": [
        ("IEGA.MI", "iShares Core Euro Govt Bond"),
        ("IEAC.MI", "iShares Core Euro Corp Bond"),
        ("IBGS.MI", "iShares Euro Govt Bond 1-3 anni"),
        ("IBGL.MI", "iShares Euro Govt Bond 15-30 anni"),
        ("IBTS.MI", "iShares US Treasury 1-3 anni"),
        ("IDTL.MI", "iShares US Treasury 20+ anni"),
        ("IHYG.MI", "iShares Euro High Yield"),
        ("IBCI.MI", "iShares Euro Inflation Linked"),
    ],
    "Azioni": [
        ("ENI.MI", "Eni"),
        ("ENEL.MI", "Enel"),
        ("ISP.MI", "Intesa Sanpaolo"),
        ("UCG.MI", "UniCredit"),
        ("RACE.MI", "Ferrari"),
        ("G.MI", "Generali"),
        ("STLAM.MI", "Stellantis"),
        ("LDO.MI", "Leonardo"),
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
    ],
    "Crypto": [
        ("BTC-USD", "Bitcoin"),
        ("ETH-USD", "Ethereum")
    ],
    "Materie prime": [
        ("GC=F", "Oro"),
        ("SI=F", "Argento"),
        ("CL=F", "Petrolio WTI"),
        ("BZ=F", "Petrolio Brent"),
        ("NG=F", "Gas naturale"),
        ("HG=F", "Rame"),
        ("PL=F", "Platino"),
        ("ZW=F", "Grano"),
        ("ZC=F", "Mais"),
        ("KC=F", "Caffè"),
    ],
}

QUI = Path(__file__).parent
FILE_DATI = QUI / "data.json"
FILE_PORTAFOGLIO = QUI / "portfolio.json"


# ------------------------------------------------------------------ dati e calcoli
def RSI(series, period=14):
    """Relative Strength Index: restituisce una serie (usa l'ultimo valore)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + gain / loss))


def calcola_sentimento_mercato(categorie):
    """RSI medio di tutti gli strumenti gia' analizzati (nessun nuovo download).
    Restituisce 'Bullish', 'Bearish' o 'Neutral'."""
    valori = [r["rsi"] for righe in categorie.values() for r in righe
              if r.get("rsi") is not None]
    if not valori:
        return "Neutral"
    medio = sum(valori) / len(valori)
    if medio >= 60:
        return "Bullish"
    if medio <= 40:
        return "Bearish"
    return "Neutral"


def scarica(ticker):
    """Scarica due anni di chiusure da yfinance (None se mancano dati)."""
    try:
        chiusure = yf.Ticker(ticker).history(period="2y", auto_adjust=True)["Close"].dropna()
    except Exception:
        return None
    return chiusure if len(chiusure) >= 210 else None


def valuta_di(ticker):
    try:
        return yf.Ticker(ticker).fast_info["currency"]
    except Exception:
        return "EUR" if ticker.endswith((".MI", ".DE")) else "USD"


def metriche(c):
    p = float(c.iloc[-1])
    return {
        "p": p,
        "var": p / float(c.iloc[-2]) - 1,
        "sma50": float(c.tail(50).mean()),
        "sma200": float(c.tail(200).mean()),
        "r3": p / float(c.iloc[-64]) - 1,
        "r6": p / float(c.iloc[-127]) - 1,
        "vol": float(c.pct_change().tail(30).std() * math.sqrt(252)),
        "rsi": None if pd.isna(RSI(c).iloc[-1]) else float(RSI(c).iloc[-1]),
    }


def segnale(r):
    if r["p"] < r["sma200"] or r["punteggio"] < SOGLIA_EVITA:
        return "EVITA"
    if r["punteggio"] >= SOGLIA_COMPRA and r["p"] > r["sma50"]:
        return "COMPRA"
    return "MANTIENI"


def consiglio(r):
    """Etichetta semplice per la pagina: SI, DEBOLE, MANTIENI, EVITA."""
    if r["segnale"] == "COMPRA":
        return "SI" if r["punteggio"] >= SOGLIA_FORTE else "DEBOLE"
    return r["segnale"]


def motivo(r):
    m50 = "sopra" if r["p"] > r["sma50"] else "sotto"
    m200 = "sopra" if r["p"] > r["sma200"] else "sotto"
    return (f"Prezzo {m50} la media a 50 giorni e {m200} quella a 200. "
            f"Rendimento {r['r3']:+.0%} a 3 mesi, {r['r6']:+.0%} a 6 mesi. "
            f"Volatilità {r['vol']:.0%} annua.")


def analizza_categoria(strumenti, eurusd, errori):
    righe = []
    for ticker, nome in strumenti:
        c = scarica(ticker)
        if c is None:
            errori.append(ticker)
            continue
        r = metriche(c)
        r.update(ticker=ticker, nome=nome, valuta=valuta_di(ticker))
        r["p_eur"] = r["p"] / eurusd if r["valuta"] == "USD" else r["p"]
        righe.append(r)
    if not righe:
        return []

    df = pd.DataFrame(righe)
    momentum = (df["r3"] + df["r6"]) / 2
    punteggio = ((df["p"] > df["sma50"]) * 20 + (df["p"] > df["sma200"]) * 20
                 + momentum.rank(pct=True) * 40 + (1 - df["vol"].rank(pct=True)) * 20)
    for r, s in zip(righe, punteggio):
        r["punteggio"] = int(round(float(s)))
        r["segnale"] = segnale(r)
        r["consiglia"] = consiglio(r)
        r["motivo"] = motivo(r)

    # peso consigliato (% del capitale totale): la quota della categoria
    # divisa tra gli strumenti COMPRA in proporzione al punteggio
    somma = sum(r["punteggio"] for r in righe if r["segnale"] == "COMPRA")
    for r in righe:
        r["peso"] = round(QUOTA_CATEGORIA * 100 * r["punteggio"] / somma, 1) \
            if r["segnale"] == "COMPRA" and somma else 0.0
    return sorted(righe, key=lambda r: -r["punteggio"])


def pulisci(r):
    """Tiene solo i campi che servono alla pagina."""
    base = {
        "ticker": r["ticker"], "nome": r["nome"], "prezzo": round(r["p"], 2),
        "valuta": r["valuta"], "var": round(r["var"], 4), "punteggio": r["punteggio"],
        "segnale": r["segnale"], "peso": r["peso"], "motivo": r["motivo"],
    }
    base["consiglia"] = r["consiglia"]
    return base


# --------------------------------------------------------------- portafoglio virtuale
def carica_portafoglio():
    pf = {}
    if FILE_PORTAFOGLIO.exists():
        pf = json.loads(FILE_PORTAFOGLIO.read_text(encoding="utf-8"))
    if not pf:
        pf = {"inizio": datetime.now(timezone.utc).date().isoformat(),
              "cash": CAPITALE_INIZIALE, "posizioni": {}, "operazioni": [], "storico": []}
    return pf


def valore_posizioni(pf, prezzi):
    return sum(x["quote"] * prezzi.get(t, x["carico"]) for t, x in pf["posizioni"].items())


def _vendi(pf, ticker, prezzo, oggi, motivo=None):
    x = pf["posizioni"].pop(ticker)
    pf["cash"] += x["quote"] * prezzo
    op = {"data": oggi, "tipo": "VENDI", "ticker": ticker,
          "prezzo": round(prezzo, 2)}
    if motivo:
        op["motivo"] = motivo
    # Evita vendite duplicate dello stesso strumento nello stesso giorno
    if not any(o.get("data") == oggi and o.get("ticker") == ticker and o.get("tipo") == "VENDI"
               for o in pf["operazioni"]):
        pf["operazioni"].append(op)


def simula(pf, categorie, oggi):
    """Vende se il segnale è EVITA, oppure se la perdita supera il 5% e il segnale
    non è più COMPRA. Compra solo gli strumenti con consiglio "SI" (punteggio forte)."""
    info = {r["ticker"]: (cat, r) for cat, righe in categorie.items() for r in righe}
    prezzi = {t: r["p_eur"] for t, (_, r) in info.items()}

    for t in list(pf["posizioni"]):
        if t not in info:
            continue
        r = info[t][1]
        carico = pf["posizioni"][t]["carico"]
        in_perdita = carico > 0 and prezzi[t] < carico * (1 - STOP_PERDITA)

        if r["segnale"] == "EVITA":
            _vendi(pf, t, prezzi[t], oggi, "EVITA")
        elif in_perdita and r["segnale"] != "COMPRA":
            _vendi(pf, t, prezzi[t], oggi, f"Perdita >{STOP_PERDITA:.0%}")

    totale = pf["cash"] + valore_posizioni(pf, prezzi)
    for cat, righe in categorie.items():
        detenuto = sum(pf["posizioni"][r["ticker"]]["quote"] * r["p_eur"]
                       for r in righe if r["ticker"] in pf["posizioni"])
        nuovi = [r for r in righe
                 if r["consiglia"] == "SI" and r["ticker"] not in pf["posizioni"]
                 and r.get("vol", 0) <= MAX_VOL.get(cat, 0.40)]
        budget = min(totale * QUOTA_CATEGORIA - detenuto, pf["cash"])
        if not nuovi or budget <= 1:
            continue
        spesa = budget / len(nuovi)
        for r in nuovi:
            pf["cash"] -= spesa
            pf["posizioni"][r["ticker"]] = {"quote": spesa / r["p_eur"], "carico": r["p_eur"]}
            pf["operazioni"].append({"data": oggi, "tipo": "COMPRA", "ticker": r["ticker"],
                                     "prezzo": round(r["p_eur"], 2)})

    totale = pf["cash"] + valore_posizioni(pf, prezzi)
    pf["storico"] = [s for s in pf["storico"] if s["data"] != oggi]
    pf["storico"].append({"data": oggi, "valore": round(totale, 2)})
    pf["operazioni"] = pf["operazioni"][-200:]
    return totale, prezzi, info


# ------------------------------------------------------------------------------ main
def main():
    ora = datetime.now(timezone.utc)
    oggi = ora.date().isoformat()
    pf = carica_portafoglio()
    try:
        eurusd = float(yf.Ticker("EURUSD=X").history(period="5d")["Close"].dropna().iloc[-1])
    except Exception:
        # Meglio l'ultimo cambio reale salvato che un valore inventato.
        eurusd = pf.get("eurusd")
        if not eurusd:
            raise SystemExit("Errore: cambio EUR/USD non disponibile e nessun valore salvato, riprova più tardi.")
        print(f"Attenzione: uso l'ultimo cambio salvato ({eurusd:.4f}).")
    pf["eurusd"] = round(eurusd, 5)

    errori = []
    categorie = {nome: analizza_categoria(lista, eurusd, errori)
                 for nome, lista in UNIVERSO.items()}

    # Calcola sentimento del mercato
    sentimento_mercato = calcola_sentimento_mercato(categorie)

    totale, prezzi, info = simula(pf, categorie, oggi)

    posizioni = []
    for t, x in pf["posizioni"].items():
        prezzo = prezzi.get(t, x["carico"])
        posizioni.append({"ticker": t, "nome": info[t][1]["nome"] if t in info else t,
                          "valore": round(x["quote"] * prezzo, 2),
                          "rendimento": round(prezzo / x["carico"] - 1, 4)})

    dati = {
        "aggiornato": ora.isoformat(timespec="minutes"),
        "capitale_iniziale": CAPITALE_INIZIALE,
        "valore": round(totale, 2),
        "cash": round(pf["cash"], 2),
        "rendimento": round(totale / CAPITALE_INIZIALE - 1, 4),
        "categorie": {c: [pulisci(r) for r in righe] for c, righe in categorie.items()},
        "posizioni": sorted(posizioni, key=lambda p: -p["valore"]),
        "operazioni": pf["operazioni"][-15:][::-1],
        "storico": pf["storico"],
        "sentimento": sentimento_mercato,
        "errori": errori,
    }
    FILE_DATI.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    FILE_PORTAFOGLIO.write_text(json.dumps(pf, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Fatto. Valore portafoglio virtuale: {totale:,.2f} EUR. "
          f"Ticker senza dati: {errori or 'nessuno'}")


if __name__ == "__main__":
    main()