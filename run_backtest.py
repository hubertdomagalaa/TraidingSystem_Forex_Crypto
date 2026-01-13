"""
Skrypt uruchomieniowy do backtestingu.
Testuje strategię Mean Reversion na EUR/PLN.

Uruchomienie:
    python run_backtest.py
"""
import sys
from pathlib import Path

# Dodaj projekt do path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    print("\n" + "=" * 60)
    print("  BACKTESTING - Trading Decision System")
    print("  Test strategii Mean Reversion na EUR/PLN")
    print("=" * 60 + "\n")
    
    # Import komponentów
    try:
        import yfinance as yf
        from models.technical import IndicatorEngine
        from strategies.forex import MeanReversionStrategy
        from backtesting import BacktestEngine
        from risk_management import PositionSizer
    except ImportError as e:
        logger.error(f"Błąd importu: {e}")
        logger.error("Czy zainstalowałeś zależności? pip install -r requirements.txt")
        return
    
    # 1. Pobierz dane historyczne
    print("📊 Pobieranie danych EUR/PLN (2 lata)...")
    ticker = yf.Ticker("EURPLN=X")
    data = ticker.history(period="2y")
    
    if data.empty:
        logger.error("Nie udało się pobrać danych!")
        return
    
    print(f"   ✅ Pobrano {len(data)} dni danych")
    print(f"   📅 Okres: {data.index[0].strftime('%Y-%m-%d')} - {data.index[-1].strftime('%Y-%m-%d')}")
    
    # 2. Oblicz wskaźniki techniczne
    print("\n📈 Obliczanie wskaźników technicznych...")
    engine = IndicatorEngine()
    data = engine.calculate_all(data)
    print("   ✅ RSI, MACD, Bollinger, ATR, Z-score obliczone")
    
    # 3. Przygotuj strategię
    print("\n🎯 Konfiguracja strategii Mean Reversion...")
    strategy = MeanReversionStrategy(lookback=20)
    
    def signal_generator(df, idx):
        """Generator sygnałów dla backtestingu."""
        return strategy.generate_signal(df['close' if 'close' in df.columns else 'Close'], vix=20)
    
    # 4. Uruchom backtest
    print("\n🚀 Uruchamianie backtestingu...")
    print("   Stop Loss: 2%")
    print("   Take Profit: 4%")
    print("   Position Size: 10% kapitału")
    
    bt = BacktestEngine(
        initial_capital=10000,
        commission_pct=0.001,  # 0.1%
        slippage_pct=0.0005,   # 0.05%
    )
    
    result = bt.run(
        data=data,
        signal_generator=signal_generator,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        position_size_pct=0.1,
    )
    
    # 5. Wyświetl raport
    print("\n" + bt.generate_report(result))
    
    # 6. Dodatkowe informacje
    print("\n📋 Szczegóły ostatnich 5 transakcji:")
    print("-" * 60)
    
    for trade in result.trades[-5:]:
        direction = "🟢 LONG" if trade.direction.value == 'long' else "🔴 SHORT"
        pnl_emoji = "💰" if trade.is_winner else "💸"
        
        print(f"{direction} | {trade.entry_date.strftime('%Y-%m-%d')} → {trade.exit_date.strftime('%Y-%m-%d')}")
        print(f"   Entry: {trade.entry_price:.4f} | Exit: {trade.exit_price:.4f}")
        print(f"   {pnl_emoji} P&L: {trade.pnl_pct:+.2f}% | Reason: {trade.exit_reason.value}")
        print()
    
    # 7. Rekomendacja
    print("\n" + "=" * 60)
    print("  REKOMENDACJA")
    print("=" * 60)
    
    if result.sharpe_ratio >= 1.5 and result.max_drawdown <= 15:
        print("  ✅ Strategia ZALICZONA - możesz przejść do paper trading")
    elif result.sharpe_ratio >= 1.0:
        print("  🟡 Strategia AKCEPTOWALNA - rozważ optymalizację parametrów")
    else:
        print("  ❌ Strategia NIEZALICZONA - wymaga poprawy przed użyciem")
    
    print("\n  Następne kroki:")
    print("  1. Przetestuj na innych parach (EUR/USD, USD/PLN)")
    print("  2. Zoptymalizuj parametry (lookback, SL/TP)")
    print("  3. Uruchom paper trading przez min. 1 miesiąc")
    print("=" * 60 + "\n")
    
    return result


if __name__ == "__main__":
    result = main()
