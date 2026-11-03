# AI Stock Advisor

Bot di analisi e paper trading azionario basato su **Google Gemini** + dati reali (yfinance).

- Capitale simulato di partenza: **≈ 100 €** (110 USD)
- Massimo **2-3 titoli** contemporaneamente
- Solo **consigli** (nessun trade automatico)
- Report giornalieri automatici su GitHub (lun-ven)
- Alert automatici di stop loss / take profit sulle posizioni aperte

## Cosa fa

Ogni giorno (lun-ven dopo la chiusura dei mercati USA) il bot:

1. Aggiorna il valore del portafoglio paper
2. Scarica i dati di mercato dei titoli in watchlist
3. Controlla stop loss / take profit (senza AI)
3. Chiede a Gemini (2.5 Flash) un’analisi in italiano
4. Scrive due file chiari:
   - `STATUS.md` → situazione attuale (guadagno/perdita)
   - `REPORT.md` → analisi + consigli concreti

## Setup rapido

### 1. Crea il repository su GitHub
Crea un repo **privato** e carica tutti i file di questa cartella.

### 2. Aggiungi il Secret
Vai su **Settings → Secrets and variables → Actions** e crea:

| Nome             | Valore                  |
|------------------|-------------------------|
| `GEMINI_API_KEY` | la tua chiave Google AI |

### 3. Abilita Actions
Vai su **Actions** e abilita i workflow se richiesto.

### 4. Permessi di scrittura
**Settings → Actions → General → Workflow permissions → Read and write permissions**
(il workflow committa `STATUS.md`, `REPORT.md` e `state/`).

### 5. Test manuale
**Actions → Daily AI Stock Report → Run workflow**. Dopo qualche minuto trovi `STATUS.md` e `REPORT.md` aggiornati.

## Eseguire un trade (simulato)
Il bot consiglia, tu decidi. Per registrare un trade nel portafoglio paper:

**Actions → Paper Trade → Run workflow** → scegli `buy`/`sell`, il ticker e l'importo in USD
(il prezzo è l'ultima chiusura, salvo prezzo manuale). Vengono rispettati i limiti di `config.yaml`
(max 40% per titolo, 10% di cash minimo, max 3 posizioni).

In locale: `python -m bot.trade buy NVDA --amount 40` / `python -m bot.trade sell NVDA`.

## Struttura

```
ai-stock-advisor/
├── bot/
│   ├── main.py          ← entry point del report giornaliero
│   ├── trade.py         ← paper trade manuale (buy/sell)
│   ├── portfolio.py     ← portafoglio paper
│   ├── analyze.py       ← yfinance + Gemini + alert di rischio
│   └── report.py        ← genera i markdown
├── .github/workflows/
│   ├── daily_report.yml ← report lun-ven
│   └── paper_trade.yml  ← trade manuale
├── config.yaml          ← capitale, watchlist, rischio, modello
├── requirements.txt
├── STATUS.md / REPORT.md ← generati automaticamente
└── state/portfolio.json ← stato del portafoglio
```

## Prossimi passi (quando vorrai)

1. Creare account **Alpaca Paper** (gratis) per esecuzione con approvazione
2. Affinare la watchlist e i parametri di rischio

---

**Disclaimer**: Questo è solo un tool educativo di paper trading. Non è consulenza finanziaria. I mercati possono farti perdere denaro.
