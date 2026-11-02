#!/usr/bin/env python3
"""
Entry point del bot AI Stock Advisor.
Gira su GitHub Actions una volta al giorno.
"""

import sys
from pathlib import Path

# Aggiungi la root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.portfolio import PaperPortfolio
from bot.analyze import run_analysis, load_config
from bot.report import write_reports


def main():
    print("=== AI Stock Advisor – avvio ===")
    config = load_config()
    initial = config["capital"]["initial_usd"]
    max_pos = config["capital"]["max_positions"]

    portfolio = PaperPortfolio(initial_cash=initial, max_positions=max_pos)
    summary = portfolio.portfolio_value()

    print(f"Valore attuale: {summary['total_value']:.2f} USD | P&L: {summary['total_pnl']:+.2f} ({summary['total_pnl_pct']:+.2f}%)")
    print(f"Posizioni: {summary['num_positions']}")

    # Analisi AI
    print("Chiamo Gemini per l'analisi...")
    analysis = run_analysis(summary)

    # Scrivi report
    write_reports(summary, analysis)

    print("=== Fine run ===")
    print("Controlla STATUS.md e REPORT.md nel repository.")


if __name__ == "__main__":
    main()
