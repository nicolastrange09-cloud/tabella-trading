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
CAPITALE_INIZIALE = 10000.0   # euro virtuali
QUOTA_CATEGORIA = 0.20        # 20% del capitale per ognuna delle 5 categorie
SOGLIA_COMPRA = 65            # punteggio minimo per COMPRA
SOGLIA_EVITA = 40             # sotto questo punteggio: EVITA

# Massimo 10 strumenti per categoria. (ticker Yahoo Finance, nome)
# Puoi modificare la lista: i ticker che non danno dati vengono saltati
# e compaiono nell'elenco "errori" del file data.json.
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
        ("ETH-USD", "Ethereum"),
        ("SOL-USD", "Solana"),
        ("BNB-USD", "BNB"),
        ("XRP-USD", "XRP"),
        ("ADA-USD", "Cardano"),
        ("DOGE-USD", "Dogecoin"),
        ("AVAX-USD", "Avalanche"),
        ("LINK-USD", "Chainlink"),
        ("DOT-USD", "Polkadot"),
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
def scarica(ticker):
    """Ultimi 2 anni di prezzi di chiusura, oppure None se mancano dati."""
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
    }


def segnale(r):
    if r["p"] < r["sma200"] or r["punteggio"] < SOGLIA_EVITA:
        return "EVITA"
    if r["punteggio"] >= SOGLIA_COMPRA and r["p"] > r["sma50"]:
        return "COMPRA"
    return "MANTIENI"


def motivo(r):
    m50 = "sopra" if r["p"] > r["sma50"] else "sotto"
    m200 = "sopra" if r["p"] > r["sma200"] else "sotto"
    return (f"Prezzo {m50} la media a 50 giorni e {m200} quella a 200. "
            f"Rendimento {r['r3']:+.0%} a 3 mesi, {r['r6']:+.0%} a 6 mesi. "
            f"Volatilità {r['vol']:.0%} annua.")


def analizza_categoria(nome_cat, strumenti, eurusd, errori):
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
        r["motivo"] = motivo(r)

    # peso consigliato (% del capitale totale): la quota della categoria
    # divisa tra gli strumenti COMPRA in proporzione al punteggio
    compra = [r for r in righe if r["segnale"] == "COMPRA"]
    somma = sum(r["punteggio"] for r in compra)
    for r in righe:
        r["peso"] = round(QUOTA_CATEGORIA * 100 * r["punteggio"] / somma, 1) \
            if r["segnale"] == "COMPRA" and somma else 0.0
    return sorted(righe, key=lambda r: -r["punteggio"])


# --------------------------------------------------------------- portafoglio virtuale
def carica_portafoglio():
    if FILE_PORTAFOGLIO.exists():
        return json.loads(FILE_PORTAFOGLIO.read_text(encoding="utf-8"))
    return {"inizio": datetime.now(timezone.utc).date().isoformat(),
            "cash": CAPITALE_INIZIALE, "posizioni": {}, "operazioni": [], "storico": []}


def valore_posizioni(pf, prezzi):
    return sum(x["quote"] * prezzi.get(t, x["carico"]) for t, x in pf["posizioni"].items())


def simula(pf, categorie, oggi):
    """Regola semplice: vendi se il segnale diventa EVITA, compra i nuovi COMPRA
    fino al 20% del capitale per categoria."""
    info = {r["ticker"]: (cat, r) for cat, righe in categorie.items() for r in righe}
    prezzi = {t: r["p_eur"] for t, (_, r) in info.items()}

    for t in list(pf["posizioni"]):
        if t in info and info[t][1]["segnale"] == "EVITA":
            x = pf["posizioni"].pop(t)
            pf["cash"] += x["quote"] * prezzi[t]
            pf["operazioni"].append({"data": oggi, "tipo": "VENDI", "ticker": t,
                                     "prezzo": round(prezzi[t], 2)})

    totale = pf["cash"] + valore_posizioni(pf, prezzi)
    for cat, righe in categorie.items():
        detenuto = sum(pf["posizioni"][r["ticker"]]["quote"] * r["p_eur"]
                       for r in righe if r["ticker"] in pf["posizioni"])
        nuovi = [r for r in righe if r["segnale"] == "COMPRA" and r["ticker"] not in pf["posizioni"]]
        budget = min(totale * QUOTA_CATEGORIA - detenuto, pf["cash"])
        if not nuovi or budget <= 1:
            continue
        for r in nuovi:
            spesa = budget / len(nuovi)
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
    try:
        eurusd = float(yf.Ticker("EURUSD=X").history(period="5d")["Close"].dropna().iloc[-1])
    except Exception:
        eurusd = 1.0
        print("Attenzione: cambio EUR/USD non disponibile, uso 1.0")

    errori = []
    categorie = {nome: analizza_categoria(nome, lista, eurusd, errori)
                 for nome, lista in UNIVERSO.items()}

    pf = carica_portafoglio()
    totale, prezzi, info = simula(pf, categorie, oggi)

    posizioni = []
    for t, x in pf["posizioni"].items():
        prezzo = prezzi.get(t, x["carico"])
        posizioni.append({"ticker": t, "nome": info[t][1]["nome"] if t in info else t,
                          "valore": round(x["quote"] * prezzo, 2),
                          "rendimento": round(prezzo / x["carico"] - 1, 4)})

    def pulisci(r):
        return {"ticker": r["ticker"], "nome": r["nome"], "prezzo": round(r["p"], 2),
                "valuta": r["valuta"], "var": round(r["var"], 4), "punteggio": r["punteggio"],
                "segnale": r["segnale"], "peso": r["peso"], "motivo": r["motivo"]}

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
        "errori": errori,
    }
    FILE_DATI.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    FILE_PORTAFOGLIO.write_text(json.dumps(pf, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Fatto. Valore portafoglio virtuale: {totale:,.2f} EUR. Ticker senza dati: {errori or 'nessuno'}")


if __name__ == "__main__":
    main()
