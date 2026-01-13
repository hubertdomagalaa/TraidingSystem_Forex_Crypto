# 🗺️ Decision Point Map - Trading System v1.0

## Cel

Dokumentacja wszystkich punktów decyzyjnych przed refaktoryzacją do v2.0.

---

## 📍 PUNKTY DECYZYJNE

### 1. SessionAnalyzer.can_trade()
**Lokalizacja**: `config/trading_sessions.py:220`
**Typ**: GATE (blokujący)
**Logika**:
```python
can_trade = len(active_sessions) > 0 and not should_avoid['avoid']
```
**Wejścia**: current_time, weekday
**Wyjścia**: bool

---

### 2. VIXCollector.get_current()
**Lokalizacja**: `data/collectors/vix_collector.py`
**Typ**: GATE (blokujący)
**Logika**:
```python
can_trade = vix_value <= max_vix (30)
```
**Wejścia**: external VIX data
**Wyjścia**: dict with value, regime, can_trade

---

### 3. ConflictResolver.resolve()
**Lokalizacja**: `aggregator/conflict_resolver.py:66`
**Typ**: MODIFIER
**Logika**:
```python
1. Detect regime (high_vol, low_vol, news, normal)
2. Check if trading allowed (VIX < 30)
3. Apply weight multipliers per regime
```
**Wejścia**: signals[], vix, news_within_1h
**Wyjścia**: (adjusted_signals, regime, trading_allowed)

---

### 4. SignalAggregator.aggregate() ⚠️ DO USUNIĘCIA
**Lokalizacja**: `aggregator/signal_aggregator.py:26`
**Typ**: VOTER (linear weighted average)
**Logika**:
```python
final_score = Σ(signal × weight × confidence) / Σ(weight)

if final_score > 0.3: action = BUY
elif final_score < -0.3: action = SELL
else: action = HOLD
```
**Wejścia**: signals[] (from FinBERT, CryptoBERT, Technical, etc.)
**Wyjścia**: dict with action, score, confidence
**⚠️ PROBLEM**: Linear voting - do zastąpienia przez DecisionEngine

---

### 5. MultiTimeframeAnalyzer.get_mtf_signal()
**Lokalizacja**: `models/technical/multi_timeframe.py:83`
**Typ**: MODIFIER
**Logika**:
```python
- Perfect alignment (3 TF) → multiplier = 1.3
- Good alignment (2 TF) → multiplier = 1.1
- Conflict → multiplier = 0.3
- Mixed → multiplier = 0.7
```
**Wejścia**: data_1h, data_4h, data_1d, signal_1h
**Wyjścia**: adjusted_signal, alignment, advice

---

### 6. EntryConfirmation.check_entry() ⚠️ DO MODYFIKACJI
**Lokalizacja**: `strategies/entry_confirmation.py:206`
**Typ**: GATE (4/7 required)
**Logika**:
```python
# Sprawdza 7 warunków dla LONG/SHORT
# Wymaga minimum 4 potwierdzeń
confirmed = achieved >= min_confirmations (4)
```
**Wejścia**: signals dict (trend, vwap, rsi, sentiment, etc.)
**Wyjścia**: entry, direction, confidence
**⚠️ PROBLEM**: Wszystkie warunki równoważne - do zmiany na REQUIRED vs OPTIONAL

---

### 7. PositionSizer.calculate()
**Lokalizacja**: `risk_management/position_sizer.py:194`
**Typ**: CALCULATOR
**Logika**:
```python
# Metody: fixed, kelly, volatility, risk-based
position_value = method(capital, **params)
```
**Wejścia**: capital, method, ATR/SL params
**Wyjścia**: position_value, position_pct

---

### 8. StopLossCalculator.atr_based()
**Lokalizacja**: `risk_management/stop_loss.py:71`
**Typ**: CALCULATOR
**Logika**:
```python
sl_distance = atr * sl_multiplier (1.2 for forex)
tp_distance = atr * tp_multiplier (2.4 for forex)
```
**Wejścia**: entry_price, atr, direction, multipliers
**Wyjścia**: stop_loss, take_profit, risk_reward

---

### 9. FinBERT/CryptoBERT/PolishBERT.analyze()
**Lokalizacja**: `models/huggingface/*.py`
**Typ**: SIGNAL GENERATOR (sentiment)
**Logika**:
```python
result = model(text)
signal = score if positive else -score if negative else 0
```
**Wejścia**: text (news, tweets)
**Wyjścia**: signal (-1 to +1), confidence, label
**⚠️ PROBLEM**: Używane jako voter - do zmiany na context/gate

---

### 10. IndicatorEngine.generate_combined_signal()
**Lokalizacja**: `models/technical/indicator_engine.py:253`
**Typ**: SIGNAL GENERATOR (technical)
**Logika**:
```python
# Agreguje RSI, MACD, Bollinger
final_signal = sum(s['signal'] * s['confidence']) / total_confidence
```
**Wejścia**: DataFrame with OHLCV
**Wyjścia**: signal, confidence, indicators dict

---

## 📊 KLASYFIKACJA

### CORE LOGIC (krytyczne dla decyzji)
1. SessionAnalyzer.can_trade() ✅ KEEP
2. VIX check ✅ KEEP
3. MTF alignment ✅ KEEP
4. EntryConfirmation ⚠️ MODIFY (REQUIRED vs OPTIONAL)

### SUPPORT LOGIC (modyfikatory)
5. ConflictResolver ⚠️ MERGE into DecisionEngine
6. SignalAggregator ❌ REPLACE with DecisionEngine
7. PositionSizer ✅ KEEP (add sentiment modifier)
8. StopLossCalculator ⚠️ MODIFY (add structure-based)

### SIGNAL SOURCES
9. FinBERT/CryptoBERT/PolishBERT ⚠️ CHANGE ROLE (gate, not voter)
10. IndicatorEngine ✅ KEEP (simplify indicators)

---

## 🔄 FLOW DIAGRAM (current v1.0)

```
                    ┌─────────────────┐
                    │ SessionAnalyzer │
                    │   can_trade()   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  VIX Collector  │
                    │   check VIX     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌───────────┐  ┌───────────┐
        │FinBERT   │  │ Technical │  │   MTF     │
        │CryptoBERT│  │ Indicators│  │ Analyzer  │
        │PolishBERT│  │           │  │           │
        └────┬─────┘  └─────┬─────┘  └─────┬─────┘
             │              │              │
             └──────────────┴──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ConflictResolver │ ← Regime detection
                    │   resolve()     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │SignalAggregator │ ← LINEAR VOTING ❌
                    │  aggregate()    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │EntryConfirmation│ ← 4/7 counting ⚠️
                    │  check_entry()  │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌───────────┐  ┌───────────┐
        │ Position │  │ Stop Loss │  │ Output    │
        │ Sizer    │  │Calculator │  │ JSON      │
        └──────────┘  └───────────┘  └───────────┘
```

---

## ✅ SUMMARY

| Komponent | Status | Akcja |
|-----------|--------|-------|
| SessionAnalyzer | ✅ OK | Keep |
| VIX Check | ✅ OK | Keep |
| Sentiment Models | ⚠️ | Change to gate/filter |
| SignalAggregator | ❌ | Replace with DecisionEngine |
| ConflictResolver | ⚠️ | Merge into DecisionEngine |
| EntryConfirmation | ⚠️ | REQUIRED vs OPTIONAL |
| MTF Analyzer | ✅ OK | Keep |
| Position Sizer | ✅ OK | Add modifiers |
| Stop Loss | ⚠️ | Add structure-based |
