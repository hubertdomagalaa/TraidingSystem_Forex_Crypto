# 📊 Trading Decision System - Pełna Dokumentacja Techniczna

## 🎯 Cel Dokumentu

Ten dokument zawiera **szczegółowy opis systemu wspomagania decyzji tradingowych**, który został zbudowany do analizy rynków Forex i Kryptowalut. Proszę o **krytyczną ocenę** tego systemu pod kątem:

1. **Sensowności podejścia** - czy architektura i logika mają sens?
2. **Potencjału zarobkowego** - czy taki system ma szanse generować zyski?
3. **Słabych punktów** - gdzie są ryzyka i co można poprawić?
4. **Zgodności z praktyką rynkową** - czy to jest zgodne z tym, jak działają profesjonalni traderzy?

---

## 📋 Spis Treści

1. [Przegląd Systemu](#przegląd-systemu)
2. [Architektura i Moduły](#architektura-i-moduły)
3. [Modele ML do Analizy Sentymentu](#modele-ml-do-analizy-sentymentu)
4. [Wskaźniki Techniczne](#wskaźniki-techniczne)
5. [Analiza Multi-Timeframe (MTF)](#analiza-multi-timeframe-mtf)
6. [System Potwierdzeń Wejścia](#system-potwierdzeń-wejścia)
7. [Agregacja Sygnałów](#agregacja-sygnałów)
8. [Zarządzanie Ryzykiem](#zarządzanie-ryzykiem)
9. [Analiza Sesji Handlowych](#analiza-sesji-handlowych)
10. [Przepływ Danych i Decyzji](#przepływ-danych-i-decyzji)
11. [Przykładowy Wynik Analizy](#przykładowy-wynik-analizy)
12. [Pytania do Oceny](#pytania-do-oceny)

---

## 🔍 Przegląd Systemu

### Co to jest?

System **Trading Decision System** to wielomodelowy framework do generowania **rekomendacji tradingowych** (NIE automatycznych transakcji) dla:
- **Forex**: EUR/PLN, EUR/USD, USD/PLN
- **Kryptowaluty**: BTC, ETH

### Kluczowe Założenia

1. **SYSTEM NIE HANDLUJE AUTOMATYCZNIE** - generuje rekomendacje, które użytkownik realizuje ręcznie na XTB (Forex) i Bybit (Crypto)
2. **Tryb Short-Term** - day trading / swing trading (1 godzina do 5 dni)
3. **Multi-model approach** - łączy analizę sentymentu z analizą techniczną
4. **Risk-first** - zarządzanie ryzykiem jest priorytetem

### Główny Workflow

```
1. Sprawdź sesję handlową (czy to dobry czas na handel?)
2. Pobierz dane rynkowe (ceny, VIX, Fear & Greed Index)
3. Analizuj sentyment newsów (FinBERT, CryptoBERT, Polish BERT)
4. Oblicz wskaźniki techniczne (RSI, MACD, VWAP, ADX, Pivot Points)
5. Wykonaj analizę multi-timeframe
6. Sprawdź potwierdzenia wejścia (min. 4 z 7 warunków)
7. Jeśli potwierdzono → oblicz SL/TP bazując na ATR
8. Wygeneruj rekomendację w JSON
9. Użytkownik wkleja JSON do LLM (Claude/ChatGPT) → dostaje finalną rekomendację
```

---

## 🏗️ Architektura i Moduły

### Struktura Katalogów

```
TradingSystem/
├── config/                # Konfiguracja systemu
│   ├── short_term_config.py   # Ustawienia day/swing trading
│   ├── trading_sessions.py    # Definicje sesji handlowych
│   ├── model_weights.py       # Wagi modeli ML
│   └── settings.py            # Główne ustawienia
├── data/                  # Pobieranie danych
│   └── collectors/
│       ├── forex_collector.py     # Dane Forex (yfinance)
│       ├── crypto_collector.py    # Dane Crypto (ccxt/Bybit API)
│       ├── vix_collector.py       # Indeks VIX
│       └── news_collector.py      # Newsy finansowe
├── models/                # Modele analizy
│   ├── huggingface/       # Modele ML sentymentu
│   │   ├── finbert_sentiment.py    # FinBERT dla newsów EN
│   │   ├── crypto_bert.py          # CryptoBERT dla crypto
│   │   └── polish_bert.py          # Polish BERT dla newsów PL
│   ├── technical/         # Wskaźniki techniczne
│   │   ├── indicator_engine.py     # RSI, MACD, Bollinger, ATR
│   │   ├── intraday_indicators.py  # VWAP, Pivots, ADX, ORB
│   │   └── multi_timeframe.py      # Analiza MTF
│   └── ensemble/          # Meta-model
├── strategies/            # Strategie wejścia
│   ├── entry_confirmation.py  # System potwierdzeń
│   ├── forex/             # Strategie Forex
│   └── crypto/            # Strategie Crypto
├── aggregator/            # Agregacja sygnałów
│   ├── signal_aggregator.py   # Weighted voting
│   └── conflict_resolver.py   # Rozwiązywanie konfliktów
├── risk_management/       # Zarządzanie ryzykiem
│   ├── position_sizer.py      # Rozmiar pozycji
│   ├── stop_loss.py           # Kalkulacja SL/TP
│   └── drawdown_monitor.py    # Monitoring strat
├── output/                # Export wyników
├── dashboard/             # Streamlit UI
├── alerts/                # Telegram, email
└── backtesting/           # Testowanie strategii
```

---

## 🤖 Modele ML do Analizy Sentymentu

### 1. FinBERT (ProsusAI/finbert)

**Cel**: Analiza sentymentu newsów finansowych w języku angielskim

**Dane wejściowe**:
- Komunikaty ECB, Fed
- Earnings reports
- Newsy makroekonomiczne

**Działanie**:
```python
# FinBERT z Hugging Face
from transformers import pipeline

model = pipeline("sentiment-analysis", model="ProsusAI/finbert")
result = model("ECB signals prolonged higher interest rates")
# Wynik: {'label': 'positive', 'score': 0.85}

# Konwersja na sygnał tradingowy:
# positive → signal = +score (0 do +1)
# negative → signal = -score (0 do -1)
# neutral → signal = 0
```

**Waga w systemie**: 0.20 (20%)

---

### 2. CryptoBERT (ElKulako/cryptobert)

**Cel**: Analiza sentymentu postów o kryptowalutach (Twitter, Reddit)

**Dane wejściowe**:
- Tweety o BTC/ETH
- Posty na Reddit
- Crypto news

**Specyfika**:
- Rozumie crypto slang ("to the moon", "HODL", "bearish")
- **DAMPENING FACTOR = 0.8** - tłumi overreaction modelu

```python
# CryptoBERT z dampening
raw_score = model(text)['score']  # np. 0.95
dampened_score = raw_score * 0.8  # = 0.76

# Dlaczego dampening?
# CryptoBERT jest bardzo reaktywny na emocjonalny język,
# więc moderujemy jego sygnały aby uniknąć fałszywych alarmów
```

**Waga w systemie**: 0.20 (20%)

---

### 3. Polish BERT (mrm8488/bert-base-polish-cased-sentiment)

**Cel**: Analiza newsów w języku polskim (NBP, PAP, bankier.pl)

**Dane wejściowe**:
- Komunikaty NBP
- Newsy PAP
- Polskie portale finansowe

**Uwaga**: Nie jest stricte finansowy, ale dobrze działa na ogólny sentiment

**Waga w systemie**: 0.10 (10%) - niższa waga, pomocniczy sygnał

---

### Podsumowanie Wag Modeli

| Model | Waga | Rynek | Język |
|-------|------|-------|-------|
| FinBERT | 0.20 | Forex | EN |
| Polish BERT | 0.10 | Forex | PL |
| CryptoBERT | 0.20 | Crypto | EN |
| Technical | 0.35 | Oba | - |
| Mean Reversion | 0.15 | Oba | - |

---

## 📈 Wskaźniki Techniczne

### Parametry dla Short-Term Trading

System używa **szybszych parametrów** niż standardowe dla day/swing trading:

| Wskaźnik | Standard | Short-Term | Uzasadnienie |
|----------|----------|------------|--------------|
| RSI Period | 14 | **7** | Szybsza reakcja na zmiany |
| RSI Overbought | 70 | **75** | Więcej miejsca na momentum |
| RSI Oversold | 30 | **25** | Więcej miejsca na momentum |
| MACD Fast | 12 | **8** | Szybsze crossovery |
| MACD Slow | 26 | **17** | Szybsze crossovery |
| Bollinger Period | 20 | **10** | Węższe bands |
| ATR Period | 14 | **10** | Krótszy lookback |

### Wskaźniki Intraday

#### VWAP (Volume Weighted Average Price)
```python
VWAP = suma(cena_typowa * volume) / suma(volume)
cena_typowa = (high + low + close) / 3

# Interpretacja:
# Cena > VWAP = bullish bias (kupujący silniejsi)
# Cena < VWAP = bearish bias (sprzedający silniejsi)
```

#### Pivot Points (Classic)
```python
PP = (High + Low + Close) / 3    # Pivot główny
R1 = 2 * PP - Low                # Opór 1
R2 = PP + (High - Low)           # Opór 2
S1 = 2 * PP - High               # Wsparcie 1
S2 = PP - (High - Low)           # Wsparcie 2

# Użycie:
# - Entry points (odbicie od S1/R1)
# - Take profit levels
# - Stop loss placement
```

#### ADX (Average Directional Index)
```python
# Mierzy SIŁĘ trendu, nie kierunek!

ADX < 20:  Brak trendu (range)     → Strategia: Mean Reversion
ADX 20-40: Rozwijający się trend   → Strategia: Momentum
ADX > 40:  Silny trend             → Strategia: Trend Following
```

#### Opening Range Breakout (ORB)
```python
# Opening Range = High/Low z pierwszych 3 świec sesji

if current_price > OR_high:
    signal = "LONG BREAKOUT"
    target = OR_high + (OR_high - OR_low)  # 1R target
    stop = OR_mid
elif current_price < OR_low:
    signal = "SHORT BREAKOUT"
else:
    signal = "WAIT - in range"
```

---

## 🕐 Analiza Multi-Timeframe (MTF)

### Zasada

**Handluj zgodnie z trendem wyższego timeframe'u!**

| Timeframe | Rola |
|-----------|------|
| 1D (Daily) | Kontekst makro |
| 4H | Potwierdzenie trendu |
| 1H | Entry/Exit |

### Logika

```python
# Analiza trendu bazuje na EMA20 i EMA50
def analyze_trend(df):
    ema20 = df['close'].ewm(span=20).mean()
    ema50 = df['close'].ewm(span=50).mean()
    
    if price > ema20 > ema50:
        return "UP" (strong uptrend)
    elif price < ema20 < ema50:
        return "DOWN" (strong downtrend)
    else:
        return "SIDEWAYS"

# Alignment check
Daily: UP + 4H: UP + 1H signal: BUY → 🟢 PERFECT BULLISH (multiplier = 1.3x)
Daily: UP + 4H: DOWN + 1H signal: BUY → ⚠️ CONFLICT (multiplier = 0.3x)
```

### Tabela Multiplierów

| Alignment | Multiplier | Confidence |
|-----------|------------|------------|
| Perfect (3 TF zgodne) | 1.3x | 90% |
| Good (2 TF zgodne) | 1.1x | 70% |
| Conflict | 0.3x | 30% |
| Mixed/Sideways | 0.7x | 50% |

---

## ✅ System Potwierdzeń Wejścia

### Filozofia

**NIE wchodzę na pojedynczy sygnał!** Wymagam minimum **4 z 7 potwierdzeń**.

### Lista Potwierdzeń dla LONG

| # | Warunek | Opis |
|---|---------|------|
| 1 | trend_1h_up | 1H trend bullish |
| 2 | trend_4h_aligned | 4H nie jest bearish |
| 3 | price_above_vwap | Cena > VWAP |
| 4 | rsi_not_overbought | RSI < 70 |
| 5 | sentiment_positive | Sentiment > 0.15 |
| 6 | not_in_avoid_time | Nie w złym czasie |
| 7 | adx_ok | ADX > 15 (jest trend) |

### Lista Potwierdzeń dla SHORT

| # | Warunek | Opis |
|---|---------|------|
| 1 | trend_1h_down | 1H trend bearish |
| 2 | trend_4h_aligned | 4H nie jest bullish |
| 3 | price_below_vwap | Cena < VWAP |
| 4 | rsi_not_oversold | RSI > 30 |
| 5 | sentiment_negative | Sentiment < -0.15 |
| 6 | not_in_avoid_time | Nie w złym czasie |
| 7 | adx_ok | ADX > 15 |

### Przykład

```python
Signals:
- trend_1h: 'up'         ✅
- trend_4h: 'up'         ✅
- price: 4.35            
- vwap: 4.33             ✅ (cena > VWAP)
- rsi: 55                ✅ (< 70)
- sentiment: 0.4         ✅ (> 0.15)
- is_good_time: True     ✅
- adx: 28                ✅ (> 15)

Result: 7/7 confirmations → 🟢 LONG CONFIRMED (confidence: 100%)
```

---

## 🔄 Agregacja Sygnałów

### Metoda: Weighted Voting

```python
final_score = Σ(signal × weight × confidence) / Σ(weight)

# Przykład:
signals = [
    {'signal': 0.7, 'confidence': 0.85, 'model': 'finbert', 'weight': 0.20},
    {'signal': 0.5, 'confidence': 0.75, 'model': 'polish_bert', 'weight': 0.10},
    {'signal': -0.3, 'confidence': 0.60, 'strategy': 'mean_reversion', 'weight': 0.15},
    {'signal': 0.4, 'confidence': 0.70, 'strategy': 'technical', 'weight': 0.35},
]

# final_score = (0.7*0.85*0.20 + 0.5*0.75*0.10 + ...) / (0.20 + 0.10 + ...)
```

### Progi Decyzyjne

```python
if final_score > 0.25:     # Niższy próg dla short-term
    action = "BUY"
elif final_score < -0.25:
    action = "SELL"
else:
    action = "HOLD"
```

### Dynamiczne Dostosowanie Wag (Reżim Rynku)

| Reżim | Warunek | Modyfikacje Wag |
|-------|---------|-----------------|
| Trending | ADX > 25 | momentum × 1.5, mean_reversion × 0.3 |
| Ranging | ADX < 20 | mean_reversion × 1.5, momentum × 0.7 |
| High Vol | VIX > 25 | technical × 0.5, momentum × 1.3 |
| News Window | 1h od newsów | sentiment × 2.0, technical × 0.5 |

### Conflict Resolver

```python
# Warunki blokady:
if VIX > 30:
    return "STOP TRADING - VIX too high"

# Rozwiązywanie konfliktów:
if bullish_count >= 2 and signal < 0:  # Short przeciw trendowi
    signal *= 0.3  # Drastycznie redukuj siłę sygnału
    warning = "⚠️ CONFLICT - sygnał przeciwny do trendu!"
```

---

## 💰 Zarządzanie Ryzykiem

### Stop Loss / Take Profit

#### Metoda ATR-Based (Preferowana)

```python
# Ustawienia Short-Term:
forex_sl_multiplier = 1.2   # SL = 1.2 × ATR
forex_tp_multiplier = 2.4   # TP = 2.4 × ATR (R:R = 1:2)

crypto_sl_multiplier = 1.5  # Większa zmienność crypto
crypto_tp_multiplier = 3.0  # R:R = 1:2

# Przykład (EUR/PLN):
entry = 4.35
atr = 0.02
direction = "long"

stop_loss = 4.35 - (0.02 * 1.2) = 4.326
take_profit = 4.35 + (0.02 * 2.4) = 4.398
risk_reward = 2.0
```

#### Trailing Stop
```python
use_trailing = True
trailing_activation = 1%  # Aktywuj po 1% profit
trailing_distance = 0.5%  # Trail 0.5% za ceną
```

### Position Sizing

#### Metoda 1: Fixed Percentage
```python
position_value = capital × 0.02  # 2% kapitału na trade
```

#### Metoda 2: Volatility-Based
```python
# Większa zmienność = mniejsza pozycja
sl_distance_pct = (atr / price) × atr_multiplier
position_value = (capital × risk_pct) / sl_distance_pct
```

#### Metoda 3: Kelly Criterion (z fractional)
```python
# Optymalna wielkość bazowana na win rate
kelly = (win_rate × odds - (1 - win_rate)) / odds
# Używamy 0.5 Kelly dla bezpieczeństwa
position = capital × (kelly × 0.5)
```

### Limity Ryzyka

| Limit | Wartość |
|-------|---------|
| Max dzienny strata | 3% kapitału |
| Max trade'ów/dzień | 5 |
| Max czas pozycji | 72h (3 dni) |
| Friday close | Zamknij Forex przed weekendem |
| Min R:R ratio | 1.5:1 |

---

## 🕐 Analiza Sesji Handlowych

### Sesje Forex (czas warszawski - CET)

| Sesja | Godziny | Zmienność | Rekomendacja |
|-------|---------|-----------|--------------|
| Azja (Tokyo) | 00:00-08:00 | Niska | ❌ Nie handluj |
| Londyn | 08:00-17:00 | Wysoka | ✅ Dobra |
| Nowy Jork | 14:00-22:00 | Wysoka | ✅ Dobra |
| **London-NY Overlap** | **14:00-17:00** | **Bardzo wysoka** | **🔥 NAJLEPSZA** |

### Najlepsze Dni Tygodnia

| Rynek | Najlepsze | Dobre | Unikaj |
|-------|-----------|-------|--------|
| Forex | Wt, Śr, Czw | Pon, Pt | Pon rano, Pt po 16:00 |
| Crypto | Pon-Czw | Nd, Pt | Sobota |

### Czego Unikać

1. **Poniedziałek rano** - luki weekendowe
2. **Piątek po 16:00** - niska płynność przed weekendem
3. **30 min przed/po ważnych newsach** (Forex)
4. **Okres świąteczny** (20-31 grudnia)

---

## 📊 Przepływ Danych i Decyzji

```
┌─────────────────┐
│  SessionAnalyzer │  ← Sprawdź czy dobry czas
└────────┬────────┘
         │
         ▼ can_trade?
┌─────────────────┐
│  VIX Collector   │  ← Sprawdź zmienność
└────────┬────────┘
         │
         ▼ VIX < 30?
┌─────────────────────────────────────────────┐
│           DATA COLLECTORS                     │
│ ┌──────────┐ ┌────────────┐ ┌────────────┐  │
│ │ Forex    │ │ Crypto     │ │ News       │  │
│ │ Collector│ │ Collector  │ │ Collector  │  │
│ └────┬─────┘ └─────┬──────┘ └─────┬──────┘  │
└──────┼─────────────┼──────────────┼──────────┘
       │             │              │
       ▼             ▼              ▼
┌─────────────────────────────────────────────┐
│           ANALYSIS LAYER                      │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│ │ FinBERT    │ │ Technical  │ │ MTF        ││
│ │ CryptoBERT │ │ Indicators │ │ Analyzer   ││
│ │ Polish BERT│ │ (RSI,MACD) │ │ (1H/4H/1D) ││
│ └─────┬──────┘ └─────┬──────┘ └──────┬─────┘│
└───────┼──────────────┼───────────────┼───────┘
        │              │               │
        ▼              ▼               ▼
┌─────────────────────────────────────────────┐
│         SIGNAL AGGREGATION                   │
│ ┌────────────────────────────────────────┐  │
│ │        Conflict Resolver                │  │
│ │ (regime detection, weight adjustment)  │  │
│ └───────────────┬────────────────────────┘  │
│                 ▼                            │
│ ┌────────────────────────────────────────┐  │
│ │        Signal Aggregator                │  │
│ │   final = Σ(signal × weight × conf)    │  │
│ └───────────────┬────────────────────────┘  │
└─────────────────┼────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         ENTRY CONFIRMATION                   │
│   Check 7 conditions, require 4+            │
└─────────────────┬───────────────────────────┘
                  │
                  ▼ confirmed?
┌─────────────────────────────────────────────┐
│         RISK MANAGEMENT                      │
│   Calculate SL/TP (ATR-based)               │
│   Calculate Position Size                   │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         OUTPUT: JSON                         │
│   → LLM (Claude/ChatGPT) review             │
│   → Final human decision                    │
└─────────────────────────────────────────────┘
```

---

## 📝 Przykładowy Wynik Analizy

```json
{
  "pair": "EUR/PLN",
  "market": "forex",
  "timestamp": "2026-01-12T23:30:00",
  "action": "LONG",
  
  "session": {
    "current_time": "23:30",
    "weekday": "monday",
    "active_sessions": ["new_york"],
    "can_trade": true,
    "recommendation": "✅ OK - można handlować"
  },
  
  "vix": {
    "value": 18.5,
    "regime": "normal",
    "can_trade": true
  },
  
  "current_price": 4.3500,
  
  "indicators": {
    "rsi": 55.2,
    "vwap": 4.3300,
    "adx": 28.5,
    "pivots": {
      "PP": 4.3400,
      "R1": 4.3650,
      "S1": 4.3150
    }
  },
  
  "trends": {
    "1h": {"direction": "up", "strength": 0.65},
    "4h": {"direction": "up", "strength": 0.45},
    "1d": {"direction": "sideways", "strength": 0.20}
  },
  
  "confirmation": {
    "entry": true,
    "direction": "long",
    "achieved": 6,
    "required": 4,
    "confidence": 0.857,
    "confirmations": [
      "trend_1h_up",
      "trend_4h_aligned",
      "price_above_vwap",
      "rsi_not_overbought",
      "sentiment_positive",
      "adx_ok"
    ],
    "missing": ["not_in_avoid_time"]
  },
  
  "trade": {
    "direction": "long",
    "entry": 4.3500,
    "stop_loss": 4.3260,
    "take_profit": 4.3980,
    "risk_reward": 2.0
  },
  
  "reason": "Entry confirmed with 6/4 signals. Strong MTF alignment."
}
```

---

## ❓ Pytania do Oceny

### 1. Sensowność Podejścia

- Czy łączenie modeli sentymentu z analizą techniczną ma sens?
- Czy multi-timeframe analysis jest poprawnie zaimplementowany?
- Czy system potwierdzeń (4/7) jest wystarczająco selektywny?

### 2. Potencjał Zarobkowy

- Jakie są szanse że taki system będzie profitable?
- Jakie win rate i R:R są realistyczne?
- Czy day/swing trading dla retail tradera ma sens vs. position trading?

### 3. Ryzyka i Słabości

- Gdzie widzisz "słabe ogniwa" w tym systemie?
- Jakie ryzyka nie są adresowane?
- Co może sprawić że system przestanie działać?

### 4. Sugestie Ulepszeń

- Co dodałbyś do tego systemu?
- Co usunąłbyś lub uprościł?
- Jak zmieniłbyś wagi modeli?

### 5. Praktyczne Pytania

- Czy dampening CryptoBERT o 0.8 to dobry pomysł?
- Czy ATR-based SL z 1.2× multiplier jest wystarczająco szeroki?
- Czy R:R 1:2 jest realistyczny dla short-term trading?

---

## 🔧 Szczegóły Techniczne

### Stack Technologiczny

- **Python 3.10+**
- **Hugging Face Transformers** (modele ML)
- **yfinance** (dane Forex)
- **ccxt / Bybit API** (dane Crypto)
- **pandas / numpy** (analiza danych)
- **Streamlit** (dashboard)

### Wymagania Sprzętowe

- RAM: min. 8GB (modele ML)
- GPU: opcjonalnie (CUDA dla szybszej inferencji)
- Internet: wymagany do pobierania danych i modeli

---

## 📌 Podsumowanie

**Trading Decision System** to modularny, wielomodelowy system do generowania rekomendacji tradingowych, który:

1. **Łączy ML i analizę techniczną** - wykorzystuje FinBERT, CryptoBERT i Polish BERT do analizy sentymentu oraz klasyczne wskaźniki techniczne
2. **Wymaga wielokrotnego potwierdzenia** - minimum 4 z 7 warunków przed wejściem
3. **Dostosowuje się do reżimu rynku** - dynamicznie modyfikuje wagi w zależności od VIX, ADX i kontekstu newsowego
4. **Priorytetyzuje risk management** - ATR-based SL/TP, position sizing, daily limits
5. **NIE handluje automatycznie** - generuje rekomendacje dla człowieka

---

*Dokument wygenerowany: 2026-01-12*
*Wersja: 1.0*
