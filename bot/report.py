"""
Genera STATUS.md e REPORT.md in italiano.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo

from tabulate import tabulate


ROOT = Path(__file__).parent.parent
TZ = ZoneInfo("Europe/Rome")
STATUS_FILE = ROOT / "STATUS.md"
REPORT_FILE = ROOT / "REPORT.md"


def _now() -> str:
    return datetime.now(TZ).strftime("%d/%m/%Y %H:%M %Z")


def generate_status(portfolio_summary: dict, max_positions: int = 3, alerts: Optional[List[str]] = None) -> str:
    now = _now()
    pnl = portfolio_summary["total_pnl"]
    pnl_pct = portfolio_summary["total_pnl_pct"]
    emoji = "🟢" if pnl >= 0 else "🔴"

    lines = [
        f"# Stato Portafoglio – {now}",
        "",
        f"**Valore totale:** {portfolio_summary['total_value']:.2f} USD",
        f"**Cash:** {portfolio_summary['cash']:.2f} USD",
        f"**Valore posizioni:** {portfolio_summary['positions_value']:.2f} USD",
        f"**P&L totale:** {emoji} {pnl:+.2f} USD ({pnl_pct:+.2f}%)",
        f"**Posizioni aperte:** {portfolio_summary['num_positions']} / {max_positions}",
        "",
    ]

    if alerts:
        lines += ["## ⚠️ Alert rischio", ""] + [f"- {a}" for a in alerts] + [""]

    if portfolio_summary["positions"]:
        lines.append("## Posizioni")
        lines.append("")
        headers = ["Titolo", "Qty", "Prezzo medio", "Prezzo attuale", "Valore", "P&L", "P&L %"]
        rows = []
        for p in portfolio_summary["positions"]:
            rows.append([
                p["symbol"],
                p["qty"],
                f"{p['avg_price']:.2f}",
                f"{p['current_price']:.2f}",
                f"{p['value']:.2f}",
                f"{p['pnl']:+.2f}",
                f"{p['pnl_pct']:+.1f}%",
            ])
        lines.append(tabulate(rows, headers=headers, tablefmt="github"))
        lines.append("")
    else:
        lines.append("_Nessuna posizione aperta._")
        lines.append("")

    lines.append("---")
    lines.append("*Aggiornato automaticamente dal bot AI Stock Advisor*")
    return "\n".join(lines)


def generate_report(portfolio_summary: dict, analysis_text: str, max_positions: int = 3,
                    alerts: Optional[List[str]] = None) -> str:
    now = _now()
    alerts_txt = ""
    if alerts:
        alerts_txt = "## ⚠️ Alert rischio\n" + "\n".join(f"- {a}" for a in alerts) + "\n\n---\n\n"
    pnl = portfolio_summary["total_pnl"]
    pnl_pct = portfolio_summary["total_pnl_pct"]
    emoji = "🟢" if pnl >= 0 else "🔴"

    content = f"""# Report Giornaliero – {now}

## Riepilogo rapido
- Valore portafoglio: **{portfolio_summary['total_value']:.2f} USD**
- P&L da inizio: {emoji} **{pnl:+.2f} USD ({pnl_pct:+.2f}%)**
- Cash disponibile: {portfolio_summary['cash']:.2f} USD
- Posizioni aperte: {portfolio_summary['num_positions']} / {max_positions}

---

{alerts_txt}## Analisi AI

{analysis_text}

---

## Come usare questo report
1. Leggi i consigli sopra.
2. Se vuoi simulare un trade: **Actions → Paper Trade → Run workflow** (scegli buy/sell, titolo e importo).
3. Il bot **non esegue trade da solo**: aspetta la tua azione.

*Questo è solo paper trading. Non è consulenza finanziaria.*
"""
    return content


def write_reports(portfolio_summary: dict, analysis_text: str, max_positions: int = 3,
                  alerts: Optional[List[str]] = None):
    status = generate_status(portfolio_summary, max_positions, alerts)
    report = generate_report(portfolio_summary, analysis_text, max_positions, alerts)

    STATUS_FILE.write_text(status, encoding="utf-8")
    REPORT_FILE.write_text(report, encoding="utf-8")

    print("Scritti STATUS.md e REPORT.md")
    return status, report
