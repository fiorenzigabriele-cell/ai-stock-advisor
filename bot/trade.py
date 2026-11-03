#!/usr/bin/env python3
"""
Esegue un trade PAPER (simulato) su richiesta manuale.

Uso:
    python -m bot.trade buy NVDA --amount 40      # compra per 40 USD (quantità frazionaria)
    python -m bot.trade buy NVDA --qty 0.25       # oppure per quantità
    python -m bot.trade sell NVDA                 # chiude l'intera posizione
    python -m bot.trade buy NVDA --amount 40 --price 180.5   # prezzo manuale (opzionale)

Il prezzo di default è l'ultima chiusura disponibile da yfinance.
Usato anche dal workflow "Paper Trade" (azione manuale su GitHub).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.analyze import load_config
from bot.portfolio import PaperPortfolio, fetch_prices


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Paper trade manuale")
    ap.add_argument("action", choices=["buy", "sell"])
    ap.add_argument("symbol")
    ap.add_argument("--amount", type=float, help="importo in USD (solo buy)")
    ap.add_argument("--qty", type=float, help="quantità (solo buy)")
    ap.add_argument("--price", type=float, help="prezzo manuale (default: ultimo prezzo di mercato)")
    ap.add_argument("--reason", default="manuale")
    args = ap.parse_args(argv)

    config = load_config()
    cap = config["capital"]
    pf = PaperPortfolio(initial_cash=cap["initial_usd"], max_positions=cap["max_positions"])
    sym = args.symbol.strip().upper()

    price = args.price or fetch_prices([sym]).get(sym)
    if not price:
        print(f"ERRORE: prezzo non disponibile per {sym}")
        return 1

    try:
        if args.action == "buy":
            if (args.amount is None) == (args.qty is None):
                print("ERRORE: indica --amount oppure --qty (uno solo)")
                return 1
            qty = args.qty if args.qty is not None else round(args.amount / price, 6)

            # Rispetta i limiti di rischio del config
            total = pf.portfolio_value()["total_value"]
            if qty * price > total * cap["max_position_pct"] + 0.01:
                print(f"ERRORE: supera il {cap['max_position_pct']:.0%} del capitale per singolo titolo")
                return 1
            if pf.state["cash"] - qty * price < total * cap["cash_reserve_pct"] - 0.01:
                print(f"ERRORE: devi tenere almeno il {cap['cash_reserve_pct']:.0%} in cash")
                return 1

            pf.open_position(sym, qty, price, reason=args.reason)
            print(f"BUY {sym}: {qty} @ {price:.2f} USD (costo {qty * price:.2f})")
        else:
            pnl = pf.close_position(sym, price, reason=args.reason)
            print(f"SELL {sym} @ {price:.2f} USD | P&L {pnl:+.2f} USD")
    except ValueError as e:
        print(f"ERRORE: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
