#!/usr/bin/env python3
"""Test veloci, senza internet. Uso:  python test_aggiorna.py"""
import sys
import types

try:
    import yfinance  # noqa: F401
except ImportError:  # i test non scaricano nulla: basta un finto modulo
    sys.modules["yfinance"] = types.ModuleType("yfinance")

import pandas as pd

import aggiorna as a


def riga(punteggio=75, segnale="COMPRA", p=100.0, ticker="T"):
    r = {"ticker": ticker, "nome": "Test", "p": p, "p_eur": p, "var": 0.01,
         "punteggio": punteggio, "segnale": segnale, "peso": 0.0, "motivo": "x",
         "valuta": "EUR", "sma50": 90.0, "sma200": 80.0}
    r["consiglia"] = a.consiglio(r)
    return r


def test_consiglio():
    assert a.consiglio(riga(75, "COMPRA")) == "SI"
    assert a.consiglio(riga(68, "COMPRA")) == "DEBOLE"
    assert a.consiglio(riga(70, "MANTIENI")) == "MANTIENI"
    assert a.consiglio(riga(30, "EVITA")) == "EVITA"


def test_segnale():
    base = {"p": 100, "sma50": 90, "sma200": 80, "punteggio": 70}
    assert a.segnale(base) == "COMPRA"
    assert a.segnale({**base, "punteggio": 50}) == "MANTIENI"
    assert a.segnale({**base, "punteggio": 30}) == "EVITA"
    assert a.segnale({**base, "sma200": 120}) == "EVITA"


def test_pulisci():
    out = a.pulisci(riga())
    assert out["consiglia"] == "SI" and "p_eur" not in out


def test_metriche():
    c = pd.Series([100.0 + i for i in range(250)])
    m = a.metriche(c)
    assert m["p"] == 349.0 and m["sma50"] < m["p"] and m["r3"] > 0


def nuovo_pf(cash=1000.0):
    return {"inizio": "2026-01-01", "cash": cash, "posizioni": {}, "operazioni": [], "storico": []}


def test_compra_solo_segnali_forti():
    pf = nuovo_pf()
    cats = {"A": [riga(80, "COMPRA", ticker="FORTE"), riga(67, "COMPRA", ticker="DEBOLE")]}
    a.simula(pf, cats, "2026-01-02")
    assert "FORTE" in pf["posizioni"] and "DEBOLE" not in pf["posizioni"]
    assert abs(pf["cash"] - 800) < 1e-6  # 20% del capitale


def test_vende_su_evita():
    pf = nuovo_pf(900)
    pf["posizioni"]["T"] = {"quote": 1.0, "carico": 100.0}
    a.simula(pf, {"A": [riga(20, "EVITA")]}, "2026-01-02")
    assert "T" not in pf["posizioni"] and abs(pf["cash"] - 1000) < 1e-6


def test_stop_perdita():
    pf = nuovo_pf(900)
    pf["posizioni"]["T"] = {"quote": 1.0, "carico": 120.0}  # ora vale 100: -16%
    a.simula(pf, {"A": [riga(50, "MANTIENI")]}, "2026-01-02")
    assert "T" not in pf["posizioni"]


def test_tiene_se_in_perdita_ma_compra():
    pf = nuovo_pf(900)
    pf["posizioni"]["T"] = {"quote": 1.0, "carico": 120.0}
    a.simula(pf, {"A": [riga(80, "COMPRA")]}, "2026-01-02")
    assert "T" in pf["posizioni"]


if __name__ == "__main__":
    prove = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for f in prove:
        f()
        print("OK ", f.__name__)
    print(f"\nTutti i {len(prove)} test sono passati.")
