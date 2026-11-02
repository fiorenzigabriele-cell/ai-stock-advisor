# AI Stock Advisor

Bot di analisi e paper trading azionario basato su **Google Gemini** + dati reali (yfinance).

- Capitale simulato di partenza: **≈ 100 €** (110 USD)
- Massimo **2-3 titoli** contemporaneamente
- Solo **consigli** (nessun trade automatico)
- Report giornalieri automatici su GitHub

## Cosa fa

Ogni giorno (lun-ven dopo la chiusura dei mercati USA) il bot:

1. Aggiorna il valore del portafoglio paper
2. Scarica i dati di mercato dei titoli in watchlist
3. Chiede a Gemini un’analisi in italiano
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

### 4. Test manuale
Vai su **Actions → Daily AI Stock Report → Run workflow**.

Dopo qualche minuto vedrai i file `STATUS.md` e `REPORT.md` aggiornati.

## Struttura

```
ai-stock-advisor/
├── bot/
│   ├── main.py          ← entry point
│   ├── portfolio.py     ← portafoglio paper
│   ├── analyze.py       ← Gemini + yfinance
│   └── report.py        ← genera i markdown
├── .github/workflows/
│   └── daily_report.yml
├── config.yaml
├── requirements.txt
├── STATUS.md            ← generato automaticamente
├── REPORT.md            ← generato automaticamente
└── state/
    └── portfolio.json   ← stato del portafoglio
```

## Prossimi passi (quando vorrai)

1. Creare account **Alpaca Paper** (gratis)
2. Aggiungere esecuzione trade solo dopo tua approvazione
3. Affinare la watchlist e i parametri di rischio

---

**Disclaimer**: Questo è solo un tool educativo di paper trading. Non è consulenza finanziaria. I mercati possono farti perdere denaro.
