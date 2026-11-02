"""
Gestione portafoglio paper trading (simulato).
Capitale iniziale ~110 USD (≈ 100 EUR).
Massimo 2-3 posizioni.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
import yfinance as yf


STATE_FILE = Path(__file__).parent.parent / "state" / "portfolio.json"


class PaperPortfolio:
    def __init__(self, initial_cash: float = 110.0, max_positions: int = 3):
        self.initial_cash = initial_cash
        self.max_positions = max_positions
        self.state = self._load()

    def _load(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "cash": self.initial_cash,
            "positions": {},          # symbol -> {qty, avg_price, opened_at}
            "history": [],            # lista di trade chiusi
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        prices = {}
        if not symbols:
            return prices
        try:
            data = yf.download(symbols, period="1d", progress=False, threads=False)
            if len(symbols) == 1:
                prices[symbols[0]] = float(data["Close"].iloc[-1])
            else:
                for sym in symbols:
                    try:
                        prices[sym] = float(data["Close"][sym].iloc[-1])
                    except Exception:
                        pass
        except Exception as e:
            print(f"Errore download prezzi: {e}")
        return prices

    def portfolio_value(self) -> dict:
        positions = self.state["positions"]
        symbols = list(positions.keys())
        prices = self.get_current_prices(symbols) if symbols else {}

        positions_value = 0.0
        details = []
        for sym, pos in positions.items():
            price = prices.get(sym, pos["avg_price"])
            value = pos["qty"] * price
            pnl = (price - pos["avg_price"]) * pos["qty"]
            pnl_pct = ((price / pos["avg_price"]) - 1) * 100 if pos["avg_price"] > 0 else 0
            positions_value += value
            details.append({
                "symbol": sym,
                "qty": round(pos["qty"], 6),
                "avg_price": round(pos["avg_price"], 4),
                "current_price": round(price, 4),
                "value": round(value, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
            })

        cash = self.state["cash"]
        total = cash + positions_value
        total_pnl = total - self.initial_cash
        total_pnl_pct = (total / self.initial_cash - 1) * 100

        return {
            "cash": round(cash, 2),
            "positions_value": round(positions_value, 2),
            "total_value": round(total, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "positions": details,
            "num_positions": len(positions),
        }

    def can_open_position(self) -> bool:
        return len(self.state["positions"]) < self.max_positions

    def suggest_size(self, price: float, max_pct: float = 0.40) -> float:
        """Calcola quantità consigliata (frazionaria)."""
        available = self.state["cash"] * max_pct
        if price <= 0:
            return 0.0
        qty = available / price
        return round(qty, 6)

    def open_position(self, symbol: str, qty: float, price: float, reason: str = ""):
        cost = qty * price
        if cost > self.state["cash"] + 0.01:
            raise ValueError(f"Cash insufficiente: serve {cost:.2f}, hai {self.state['cash']:.2f}")
        if not self.can_open_position() and symbol not in self.state["positions"]:
            raise ValueError(f"Hai già {self.max_positions} posizioni aperte")

        if symbol in self.state["positions"]:
            # media ponderata
            old = self.state["positions"][symbol]
            new_qty = old["qty"] + qty
            new_avg = (old["qty"] * old["avg_price"] + qty * price) / new_qty
            self.state["positions"][symbol] = {
                "qty": new_qty,
                "avg_price": new_avg,
                "opened_at": old["opened_at"],
            }
        else:
            self.state["positions"][symbol] = {
                "qty": qty,
                "avg_price": price,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }

        self.state["cash"] -= cost
        self.state["history"].append({
            "type": "BUY",
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "cost": round(cost, 2),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.save()

    def close_position(self, symbol: str, price: float, reason: str = ""):
        if symbol not in self.state["positions"]:
            raise ValueError(f"Nessuna posizione aperta su {symbol}")
        pos = self.state["positions"][symbol]
        proceeds = pos["qty"] * price
        pnl = (price - pos["avg_price"]) * pos["qty"]

        self.state["cash"] += proceeds
        self.state["history"].append({
            "type": "SELL",
            "symbol": symbol,
            "qty": pos["qty"],
            "price": price,
            "proceeds": round(proceeds, 2),
            "pnl": round(pnl, 2),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        del self.state["positions"][symbol]
        self.save()
        return pnl
