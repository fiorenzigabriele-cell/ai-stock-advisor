"""
Analisi di mercato con Gemini + yfinance.
Produce suggerimenti chiari in italiano.
"""

import os
import time
from typing import List, Dict, Any
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _rsi(close: pd.Series, period: int = 14) -> float:
    """RSI con smoothing di Wilder; gestisce loss = 0 e dati insufficienti."""
    if len(close) <= period:
        return 50.0
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    g, l = float(gain.iloc[-1]), float(loss.iloc[-1])
    if l == 0:
        return 100.0 if g > 0 else 50.0
    return float(100 - 100 / (1 + g / l))


def _safe_info(t: yf.Ticker, sym: str) -> dict:
    """t.info è lento e spesso fallisce: non deve mai bloccare l'analisi."""
    try:
        info = t.info or {}
    except Exception:
        info = {}
    return {
        "name": info.get("shortName", sym),
        "sector": info.get("sector", "N/A"),
        "market_cap": info.get("marketCap"),
    }


def get_market_data(symbols: List[str]) -> Dict[str, Any]:
    """Scarica dati recenti + indicatori base per ogni titolo."""
    result = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="6mo").dropna(subset=["Close"])
            if len(hist) < 2:
                print(f"Dati insufficienti per {sym}")
                continue

            closes = hist["Close"]
            close = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])

            def chg(n: int) -> float:
                return (close / float(closes.iloc[-1 - n]) - 1) * 100 if len(closes) > n else 0.0

            ma20 = float(closes.rolling(20).mean().iloc[-1]) if len(closes) >= 20 else close
            ma50 = float(closes.rolling(50).mean().iloc[-1]) if len(closes) >= 50 else close
            vol = (
                float(closes.pct_change().rolling(20).std().iloc[-1] * (252 ** 0.5) * 100)
                if len(closes) >= 21 else 0.0
            )
            high_52 = float(closes.tail(126).max())

            result[sym] = {
                "price": round(close, 2),
                "change_1d_pct": round((close / prev - 1) * 100, 2),
                "change_1w_pct": round(chg(5), 2),
                "change_1m_pct": round(chg(21), 2),
                "ma20": round(ma20, 2),
                "ma50": round(ma50, 2),
                "rsi_14": round(_rsi(closes), 1),
                "volatility_ann_pct": round(vol, 1),
                "from_6m_high_pct": round((close / high_52 - 1) * 100, 1),
                "volume": int(hist["Volume"].iloc[-1]),
                "last_date": str(hist.index[-1].date()),
                **_safe_info(t, sym),
            }
        except Exception as e:
            print(f"Errore dati {sym}: {e}")
    return result


def risk_alerts(portfolio_summary: dict, config: dict) -> List[str]:
    """Controllo deterministico (senza AI) di stop loss / take profit sulle posizioni aperte."""
    sl = config["risk"]["stop_loss_pct"] * 100
    tp = config["risk"]["take_profit_pct"] * 100
    alerts = []
    for p in portfolio_summary.get("positions", []):
        if p["pnl_pct"] <= -sl:
            alerts.append(
                f"🔴 **{p['symbol']}**: {p['pnl_pct']:+.1f}% → stop loss (-{sl:.0f}%) raggiunto. "
                f"Valuta di chiudere (Actions → Paper Trade → sell {p['symbol']})."
            )
        elif p["pnl_pct"] >= tp:
            alerts.append(
                f"🟢 **{p['symbol']}**: {p['pnl_pct']:+.1f}% → take profit (+{tp:.0f}%) raggiunto. "
                f"Valuta di incassare (Actions → Paper Trade → sell {p['symbol']})."
            )
    return alerts


def build_prompt(portfolio_summary: dict, market_data: dict, config: dict) -> str:
    """Costruisce il prompt per Gemini in italiano."""
    cap, risk = config["capital"], config["risk"]
    sl, tp = risk["stop_loss_pct"] * 100, risk["take_profit_pct"] * 100
    min_conf = round(risk["min_confidence"] * 10)

    positions_txt = ""
    if portfolio_summary["positions"]:
        for p in portfolio_summary["positions"]:
            positions_txt += (
                f"- {p['symbol']}: qty {p['qty']}, prezzo medio {p['avg_price']}, "
                f"attuale {p['current_price']}, P&L {p['pnl']:+.2f} USD ({p['pnl_pct']:+.1f}%)\n"
            )
    else:
        positions_txt = "Nessuna posizione aperta.\n"

    market_txt = ""
    for sym, d in market_data.items():
        trend = "sopra" if d["price"] > d["ma50"] else "sotto"
        market_txt += (
            f"{sym} ({d.get('name', '')}, {d.get('sector', 'N/A')}): prezzo {d['price']} (al {d['last_date']}), "
            f"1g {d['change_1d_pct']:+.1f}%, 1s {d['change_1w_pct']:+.1f}%, 1m {d['change_1m_pct']:+.1f}%, "
            f"RSI {d['rsi_14']}, vol annua {d['volatility_ann_pct']}%, "
            f"MA20 {d['ma20']}, MA50 {d['ma50']} (prezzo {trend} MA50), "
            f"{d['from_6m_high_pct']:+.1f}% dal massimo a 6 mesi\n"
        )

    max_invest = portfolio_summary["total_value"] * cap["max_position_pct"]
    free_cash = max(portfolio_summary["cash"] - portfolio_summary["total_value"] * cap["cash_reserve_pct"], 0)

    return f"""Sei un assistente di analisi azionaria per un piccolo investitore italiano (paper trading, nessuna esecuzione automatica).

SITUAZIONE
- Valore totale: {portfolio_summary['total_value']:.2f} USD (partenza {cap['initial_usd']:.0f} USD ≈ 100 EUR).
- Cash: {portfolio_summary['cash']:.2f} USD, di cui investibile rispettando la riserva del {cap['cash_reserve_pct']:.0%}: {free_cash:.2f} USD.
- Posizioni: {portfolio_summary['num_positions']} aperte su max {cap['max_positions']}.
- Importo massimo per singolo titolo: {max_invest:.2f} USD ({cap['max_position_pct']:.0%} del capitale).

POSIZIONI ATTUALI:
{positions_txt}
DATI DI MERCATO:
{market_txt}
REGOLE:
- Usa SOLO i dati forniti sopra. Non inventare prezzi, notizie, trimestrali o eventi: se non li hai, dillo.
- Capitale molto piccolo → risk management stretto, è accettabile non fare nulla.
- Stile: momentum con volatilità controllata. Evita di comprare con RSI > 75 o titoli molto sotto la MA50 senza motivo.
- Stop loss {sl:.0f}%, take profit {tp:.0f}%. Se una posizione li ha raggiunti, segnalalo.
- Suggerisci COMPRA solo se la confidenza è almeno {min_conf}/10; altrimenti "NON FARE NULLA".
- Mai più di 1-2 azioni concrete. Non superare i limiti di importo e di numero posizioni.
- Per ogni COMPRA: titolo, importo in USD, quantità frazionaria approssimativa, prezzo di riferimento, stop loss e take profit in USD.
- Rispondi in italiano chiaro e diretto, motivando ogni consiglio in 2-3 frasi.

FORMATO RISPOSTA (rispettalo):
### Stato portafoglio
...

### Analisi mercati
...

### Consigli
- ...

### Confidenza
X/10
"""


def _fallback_report(reason: str) -> str:
    return (
        "### Stato portafoglio\n"
        "Analisi AI non disponibile in questo run.\n\n"
        "### Analisi mercati\n"
        f"{reason}\n\n"
        "### Consigli\n"
        "- Nessun consiglio generato: **non fare nulla** finché l'analisi non torna disponibile.\n\n"
        "### Confidenza\n"
        "0/10"
    )


def call_gemini(prompt: str, config: dict) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _fallback_report("Chiave `GEMINI_API_KEY` non trovata: aggiungila nei Secret del repository.")

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return _fallback_report("Libreria `google-genai` non installata (`pip install -r requirements.txt`).")

    gcfg = config.get("gemini", {})
    client = genai.Client(api_key=api_key)
    gen_config = types.GenerateContentConfig(
        temperature=gcfg.get("temperature", 0.3),
        max_output_tokens=gcfg.get("max_output_tokens", 4096),
    )

    # Solo modelli GRATUITI (Free Tier) – dal più leggero al più capace
    models = [
        gcfg.get("model", "gemini-2.5-flash-lite"),
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
    ]
    # Rimuovi duplicati mantenendo l'ordine
    seen = set()
    models = [m for m in models if not (m in seen or seen.add(m))]

    last_err = None
    for model in models:
        for attempt in range(1, gcfg.get("retries", 8) + 1):
            try:
                print(f"Tentativo {attempt} con modello {model}...")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=gen_config,
                )
                if response.text:
                    print(f"OK con {model}")
                    return response.text
                last_err = "risposta vuota"
            except Exception as e:
                last_err = str(e)
                print(f"Gemini {model} tentativo {attempt} fallito: {last_err}")
                # Se è 503/429 aspetta di più
                if any(x in last_err for x in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                    time.sleep(8 * attempt)
                else:
                    time.sleep(3 * attempt)
        print(f"Passo al modello successivo dopo fallimenti su {model}")

    return _fallback_report(f"Errore Gemini dopo vari tentativi su modelli free: {last_err}")


def run_analysis(portfolio_summary: dict, config: dict = None) -> str:
    config = config or load_config()
    symbols = config.get("watchlist", ["NVDA", "TSLA", "AMD", "AAPL", "MSFT"])
    open_symbols = [p["symbol"] for p in portfolio_summary.get("positions", [])]
    all_symbols = list(dict.fromkeys(symbols + open_symbols))

    print(f"Scarico dati per: {all_symbols}")
    market_data = get_market_data(all_symbols)
    print(f"Dati ricevuti per {len(market_data)} titoli")

    if not market_data:
        return _fallback_report("Nessun dato di mercato scaricato (mercato chiuso o yfinance non raggiungibile).")

    return call_gemini(build_prompt(portfolio_summary, market_data, config), config)