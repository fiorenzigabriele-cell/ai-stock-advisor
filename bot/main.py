#!/usr/bin/env python3
"""
Entry point del bot AI Stock Advisor.
Gira su GitHub Actions una volta al giorno (lun-ven).
"""

import sys
from pathlib import Path

# Aggiungi la root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.portfolio import PaperPortfolio
from bot.analyze import run_analysis, load_config, risk_alerts
from bot.report import write_reports


def main():
    print("=== AI Stock Advisor – avvio ===")
    config = load_config()
    cap = config["capital"]

    portfolio = PaperPortfolio(initial_cash=cap["initial_usd"], max_positions=cap["max_positions"])
    summary = portfolio.portfolio_value()

    print(f"Valore attuale: {summary['total_value']:.2f} USD | "
          f"P&L: {summary['total_pnl']:+.2f} ({summary['total_pnl_pct']:+.2f}%)")
    print(f"Posizioni: {summary['num_positions']}")

    alerts = risk_alerts(summary, config)
    for a in alerts:
        print("ALERT:", a)

    print("Chiamo Gemini per l'analisi...")
    analysis = run_analysis(summary, config)

    write_reports(summary, analysis, cap["max_positions"], alerts)

    print("=== Fine run ===")


if __name__ == "__main__":
    main()
