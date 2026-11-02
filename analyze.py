"""
Analisi di mercato con Gemini + yfinance.
Produce suggerimenti chiari in italiano.
"""

import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
import yfinance as yf
import google.generativeai as genai
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_market_data(symbols: List[str]) -> Dict[str, Any]:
    """Scarica dati recenti + indicatori base per ogni titolo."""
    result = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="3mo")
            if hist.empty:
                continue

            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last

            # Indicatori semplici
            close = float(last["Close"])
            change_1d = ((close / float(prev["Close"])) - 1) * 100
            change_1w = ((close / float(hist["Close"].iloc[-6])) - 1) * 100 if len(hist) > 5 else 0
            change_1m = ((close / float(hist["Close"].iloc[-22])) - 1) * 100 if len(hist) > 21 else 0

            # Media mobile 20 e 50
            ma20 = float(hist["Close"].rolling(20).mean().iloc[-1]) if len(hist) >= 20 else close
            ma50 = float(hist["Close"].rolling(50).mean().iloc[-1]) if len(hist) >= 50 else close

            # RSI 14
            delta = hist["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float(100 - (100 / (1 + rs.iloc[-1]))) if not rs.empty else 50

            # Volatilità 20 giorni
            returns = hist["Close"].pct_change()
            vol = float(returns.rolling(20).std().iloc[-1] * (252 ** 0.5) * 100) if len(hist) >= 20 else 0

            info = t.info
            result[sym] = {
                "price": round(close, 2),
                "change_1d_pct": round(change_1d, 2),
                "change_1w_pct": round(change_1w, 2),
                "change_1m_pct": round(change_1m, 2),
                "ma20": round(ma20, 2),
                "ma50": round(ma50, 2),
                "rsi_14": round(rsi, 1),
                "volatility_ann_pct": round(vol, 1),
                "volume": int(last["Volume"]),
                "name": info.get("shortName", sym),
                "sector": info.get("sector", "N/A"),
                "market_cap": info.get("marketCap"),
            }
        except Exception as e:
            print(f"Errore dati {sym}: {e}")
    return result


def build_prompt(portfolio_summary: dict, market_data: dict, config: dict) -> str:
    """Costruisce il prompt per Gemini in italiano."""
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
        market_txt += (
            f"{sym} ({d.get('name', '')}): "
            f"prezzo {d['price']}, "
            f"1g {d['change_1d_pct']:+.1f}%, 1s {d['change_1w_pct']:+.1f}%, 1m {d['change_1m_pct']:+.1f}%, "
            f"RSI {d['rsi_14']}, vol {d['volatility_ann_pct']}%, "
            f"MA20 {d['ma20']}, MA50 {d['ma50']}\n"
        )

    prompt = f"""Sei un assistente di analisi azionaria per un piccolo investitore italiano.
Capitale totale attuale: {portfolio_summary['total_value']:.2f} USD (partenza 110 USD ≈ 100 EUR).
Cash disponibile: {portfolio_summary['cash']:.2f} USD.
Posizioni massime consentite: {config['capital']['max_positions']}.
Attualmente hai {portfolio_summary['num_positions']} posizioni aperte.

POSIZIONI ATTUALI:
{positions_txt}

DATI DI MERCATO (ultimi giorni):
{market_txt}

REGOLE IMPORTANTI:
- L'investitore vuole investire al massimo su 2-3 titoli.
- Capitale molto piccolo → risk management stretto.
- Preferisci titoli liquidi USA.
- Stile: aggressivo ma non suicida (momentum, volatilità controllata).
- Stop loss consigliato intorno all'8%, take profit intorno al 15-20%.
- Non inventare numeri. Usa solo i dati forniti + la tua conoscenza generale.
- Rispondi SEMPRE in italiano chiaro e diretto.

COMPITO:
1. Fai un breve commento sullo stato del portafoglio (guadagno/perdita).
2. Analizza i titoli più interessanti in questo momento.
3. Dai al massimo 1-2 consigli concreti di azione (COMPRA / VENDI / MANTIENI / NON FARE NULLA).
4. Per ogni consiglio di COMPRA indica: titolo, quantità approssimativa (rispettando max 40% del capitale), prezzo di riferimento, stop loss e take profit.
5. Motiva ogni consiglio in 2-3 frasi.
6. Alla fine dai un livello di confidenza complessivo da 1 a 10.

Formato risposta:
### Stato portafoglio
...

### Analisi mercati
...

### Consigli
- ...

### Confidenza
X/10
"""
    return prompt


def call_gemini(prompt: str, config: dict) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return (
            "### Stato portafoglio\n"
            "Chiave GEMINI_API_KEY non trovata. Aggiungila come Secret su GitHub.\n\n"
            "### Analisi mercati\n"
            "Impossibile chiamare Gemini.\n\n"
            "### Consigli\n"
            "- Nessun consiglio generato (manca API key).\n\n"
            "### Confidenza\n"
            "0/10"
        )

    genai.configure(api_key=api_key)
    model_name = config.get("gemini", {}).get("model", "gemini-1.5-flash")
    temperature = config.get("gemini", {}).get("temperature", 0.3)

    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=1500,
        ),
    )
    return response.text


def run_analysis(portfolio_summary: dict) -> str:
    config = load_config()
    symbols = config.get("watchlist", ["NVDA", "TSLA", "AMD", "AAPL", "MSFT"])
    # Aggiungi eventuali posizioni già aperte
    open_symbols = [p["symbol"] for p in portfolio_summary.get("positions", [])]
    all_symbols = list(dict.fromkeys(symbols + open_symbols))  # unique preserve order

    print(f"Scarico dati per: {all_symbols}")
    market_data = get_market_data(all_symbols)
    print(f"Dati ricevuti per {len(market_data)} titoli")

    prompt = build_prompt(portfolio_summary, market_data, config)
    analysis = call_gemini(prompt, config)
    return analysis
