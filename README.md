# Trading Decision System
# System Wspomagania Decyzji Tradingowych

System wielomodelowy do generowania sygnałów tradingowych dla Forex i Kryptowalut.

## 🎯 Cel

System analizuje rynek używając:
- Modeli Hugging Face (FinBERT, CryptoBERT, Polish BERT)
- Wskaźników technicznych (dla Forex)
- Danych z social media (Fear & Greed Index)
- Strategii tradingowych (Mean Reversion, Momentum)

**UWAGA:** System NIE wykonuje automatycznie transakcji. Generuje rekomendacje, które użytkownik realizuje ręcznie na XTB (Forex) i Bybit (Crypto).

## 📁 Struktura Projektu

```
TradingSystem/
├── config/           # Konfiguracja
├── data/             # Pobieranie i przechowywanie danych
├── models/           # Modele ML i strategie
├── strategies/       # Strategie tradingowe
├── aggregator/       # Agregacja sygnałów
├── output/           # Export JSON dla AntiGravity LLM
├── social_tracking/  # Śledzenie social media
├── dashboard/        # Streamlit UI
├── alerts/           # Telegram, email
├── backtesting/      # Testowanie strategii
└── tests/            # Testy jednostkowe
```

## 🚀 Instalacja

```bash
pip install -r requirements.txt
```

## 💡 Użycie

```bash
# Uruchom analizę
python main.py

# Uruchom dashboard
streamlit run dashboard/app.py
```

## 📊 Workflow

1. System pobiera dane rynkowe
2. Uruchamia wszystkie modele i strategie
3. Agreguje sygnały z wagami
4. Eksportuje JSON z wynikami
5. Wklejasz JSON do AntiGravity → Dostajesz finalną rekomendację

## ⚠️ Disclaimer

Ten system jest narzędziem edukacyjnym i analitycznym. Nie stanowi porady inwestycyjnej. Trading wiąże się z ryzykiem utraty kapitału.
