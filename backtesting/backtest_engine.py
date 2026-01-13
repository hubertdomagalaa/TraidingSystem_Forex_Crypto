"""
Silnik backtestingu dla Trading System.
Testuje strategie na danych historycznych i oblicza metryki wydajności.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    """Kierunek transakcji."""
    LONG = "long"
    SHORT = "short"


class ExitReason(Enum):
    """Powód zamknięcia pozycji."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    SIGNAL_REVERSAL = "signal_reversal"
    TIME_EXIT = "time_exit"
    END_OF_DATA = "end_of_data"


@dataclass
class Trade:
    """Reprezentuje pojedynczą transakcję."""
    entry_date: datetime
    exit_date: datetime
    direction: TradeDirection
    entry_price: float
    exit_price: float
    size: float  # Wartość pozycji w walucie bazowej
    pnl: float  # Profit/Loss w walucie
    pnl_pct: float  # Profit/Loss procentowo
    signal_score: float  # Score sygnału przy wejściu
    exit_reason: ExitReason
    
    @property
    def duration(self) -> timedelta:
        """Długość trwania transakcji."""
        return self.exit_date - self.entry_date
    
    @property
    def is_winner(self) -> bool:
        """Czy transakcja była zyskowna."""
        return self.pnl > 0


@dataclass
class BacktestResult:
    """Wyniki backtestingu."""
    # Podstawowe metryki
    total_return: float  # Całkowity zwrot %
    total_pnl: float  # Całkowity P&L w walucie
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float  # Maksymalny drawdown %
    
    # Statystyki transakcji
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    
    # Średnie
    avg_win: float
    avg_loss: float
    avg_win_pct: float
    avg_loss_pct: float
    avg_trade_duration: timedelta
    
    # Dodatkowe
    max_consecutive_wins: int
    max_consecutive_losses: int
    best_trade: float
    worst_trade: float
    
    # Dane
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    daily_returns: pd.Series = field(default_factory=pd.Series)
    
    # Metadane
    start_date: datetime = None
    end_date: datetime = None
    initial_capital: float = 10000
    final_capital: float = 10000


class BacktestEngine:
    """
    Silnik backtestingu.
    
    Symuluje handel na danych historycznych i oblicza metryki wydajności.
    
    Funkcje:
    - Symulacja long/short trades
    - Stop Loss i Take Profit
    - Position sizing
    - Obliczanie Sharpe, Sortino, Max Drawdown
    - Generowanie equity curve
    """
    
    def __init__(
        self,
        initial_capital: float = 10000,
        commission_pct: float = 0.001,  # 0.1% prowizji
        slippage_pct: float = 0.0005,   # 0.05% poślizgu
    ):
        """
        Args:
            initial_capital: Kapitał początkowy
            commission_pct: Prowizja jako % wartości transakcji
            slippage_pct: Poślizg cenowy jako %
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        
        # Stan wewnętrzny
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.current_capital = initial_capital
    
    def run(
        self,
        data: pd.DataFrame,
        signal_generator: Callable[[pd.DataFrame, int], Dict],
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04,
        position_size_pct: float = 0.1,
        max_holding_periods: int = None,
    ) -> BacktestResult:
        """
        Uruchamia backtest.
        
        Args:
            data: DataFrame z kolumnami: open, high, low, close, volume
                  Musi mieć DatetimeIndex
            signal_generator: Funkcja(df, current_index) -> {'signal': float, 'confidence': float}
                             signal > 0.3 = BUY, signal < -0.3 = SELL
            stop_loss_pct: Stop loss jako % ceny wejścia
            take_profit_pct: Take profit jako % ceny wejścia
            position_size_pct: Wielkość pozycji jako % kapitału
            max_holding_periods: Max okresów trzymania pozycji (None = bez limitu)
        
        Returns:
            BacktestResult z pełnymi metrykami
        """
        logger.info(f"Rozpoczynam backtest: {len(data)} okresów")
        
        # Reset stanu
        self.trades = []
        self.equity_curve = []
        self.current_capital = self.initial_capital
        
        # Standaryzuj nazwy kolumn
        data = data.copy()
        data.columns = data.columns.str.lower()
        
        # Zmienne stanu
        position = None  # Aktualna pozycja
        position_entry_idx = None
        
        # Główna pętla backtestingu
        for i in range(50, len(data)):  # Start od 50 dla wskaźników
            current_date = data.index[i]
            current_bar = data.iloc[i]
            
            # Zapisz equity
            self.equity_curve.append((current_date, self.current_capital))
            
            # Jeśli mamy pozycję - sprawdź exit
            if position is not None:
                exit_triggered, exit_reason, exit_price = self._check_exit(
                    position=position,
                    current_bar=current_bar,
                    data=data,
                    current_idx=i,
                    entry_idx=position_entry_idx,
                    stop_loss_pct=stop_loss_pct,
                    take_profit_pct=take_profit_pct,
                    max_holding_periods=max_holding_periods,
                    signal_generator=signal_generator,
                )
                
                if exit_triggered:
                    trade = self._close_position(
                        position=position,
                        exit_date=current_date,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                    )
                    self.trades.append(trade)
                    position = None
                    position_entry_idx = None
            
            # Jeśli nie mamy pozycji - sprawdź entry
            if position is None:
                signal = signal_generator(data.iloc[:i+1], i)
                
                if signal['signal'] > 0.3 and signal['confidence'] > 0.3:
                    # LONG entry
                    position = self._open_position(
                        direction=TradeDirection.LONG,
                        entry_date=current_date,
                        entry_price=current_bar['close'],
                        signal_score=signal['signal'],
                        position_size_pct=position_size_pct,
                    )
                    position_entry_idx = i
                
                elif signal['signal'] < -0.3 and signal['confidence'] > 0.3:
                    # SHORT entry
                    position = self._open_position(
                        direction=TradeDirection.SHORT,
                        entry_date=current_date,
                        entry_price=current_bar['close'],
                        signal_score=signal['signal'],
                        position_size_pct=position_size_pct,
                    )
                    position_entry_idx = i
        
        # Zamknij otwartą pozycję na końcu danych
        if position is not None:
            trade = self._close_position(
                position=position,
                exit_date=data.index[-1],
                exit_price=data.iloc[-1]['close'],
                exit_reason=ExitReason.END_OF_DATA,
            )
            self.trades.append(trade)
        
        # Oblicz metryki
        result = self._calculate_metrics(data)
        
        logger.info(f"Backtest zakończony: {result.total_trades} transakcji, "
                   f"Sharpe: {result.sharpe_ratio:.2f}, "
                   f"Return: {result.total_return:.2f}%")
        
        return result
    
    def _open_position(
        self,
        direction: TradeDirection,
        entry_date: datetime,
        entry_price: float,
        signal_score: float,
        position_size_pct: float,
    ) -> Dict:
        """Otwiera nową pozycję."""
        # Uwzględnij slippage
        if direction == TradeDirection.LONG:
            adjusted_price = entry_price * (1 + self.slippage_pct)
        else:
            adjusted_price = entry_price * (1 - self.slippage_pct)
        
        # Oblicz wielkość pozycji
        position_value = self.current_capital * position_size_pct
        
        # Odejmij prowizję
        commission = position_value * self.commission_pct
        self.current_capital -= commission
        
        return {
            'direction': direction,
            'entry_date': entry_date,
            'entry_price': adjusted_price,
            'signal_score': signal_score,
            'size': position_value,
        }
    
    def _close_position(
        self,
        position: Dict,
        exit_date: datetime,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> Trade:
        """Zamyka pozycję i tworzy Trade."""
        # Uwzględnij slippage
        if position['direction'] == TradeDirection.LONG:
            adjusted_exit = exit_price * (1 - self.slippage_pct)
        else:
            adjusted_exit = exit_price * (1 + self.slippage_pct)
        
        # Oblicz P&L
        if position['direction'] == TradeDirection.LONG:
            pnl_pct = (adjusted_exit - position['entry_price']) / position['entry_price']
        else:
            pnl_pct = (position['entry_price'] - adjusted_exit) / position['entry_price']
        
        pnl = position['size'] * pnl_pct
        
        # Odejmij prowizję
        commission = position['size'] * self.commission_pct
        pnl -= commission
        
        # Aktualizuj kapitał
        self.current_capital += pnl
        
        return Trade(
            entry_date=position['entry_date'],
            exit_date=exit_date,
            direction=position['direction'],
            entry_price=position['entry_price'],
            exit_price=adjusted_exit,
            size=position['size'],
            pnl=pnl,
            pnl_pct=pnl_pct * 100,  # W procentach
            signal_score=position['signal_score'],
            exit_reason=exit_reason,
        )
    
    def _check_exit(
        self,
        position: Dict,
        current_bar: pd.Series,
        data: pd.DataFrame,
        current_idx: int,
        entry_idx: int,
        stop_loss_pct: float,
        take_profit_pct: float,
        max_holding_periods: int,
        signal_generator: Callable,
    ) -> Tuple[bool, ExitReason, float]:
        """
        Sprawdza warunki wyjścia z pozycji.
        
        Returns:
            Tuple (czy_wyjść, powód, cena_wyjścia)
        """
        entry_price = position['entry_price']
        direction = position['direction']
        
        high = current_bar['high']
        low = current_bar['low']
        close = current_bar['close']
        
        # Stop Loss
        if direction == TradeDirection.LONG:
            sl_price = entry_price * (1 - stop_loss_pct)
            if low <= sl_price:
                return True, ExitReason.STOP_LOSS, sl_price
        else:
            sl_price = entry_price * (1 + stop_loss_pct)
            if high >= sl_price:
                return True, ExitReason.STOP_LOSS, sl_price
        
        # Take Profit
        if direction == TradeDirection.LONG:
            tp_price = entry_price * (1 + take_profit_pct)
            if high >= tp_price:
                return True, ExitReason.TAKE_PROFIT, tp_price
        else:
            tp_price = entry_price * (1 - take_profit_pct)
            if low <= tp_price:
                return True, ExitReason.TAKE_PROFIT, tp_price
        
        # Max holding period
        if max_holding_periods is not None:
            if current_idx - entry_idx >= max_holding_periods:
                return True, ExitReason.TIME_EXIT, close
        
        # Signal reversal
        signal = signal_generator(data.iloc[:current_idx+1], current_idx)
        if direction == TradeDirection.LONG and signal['signal'] < -0.3:
            return True, ExitReason.SIGNAL_REVERSAL, close
        elif direction == TradeDirection.SHORT and signal['signal'] > 0.3:
            return True, ExitReason.SIGNAL_REVERSAL, close
        
        return False, None, None
    
    def _calculate_metrics(self, data: pd.DataFrame) -> BacktestResult:
        """Oblicza wszystkie metryki z listy transakcji."""
        trades = self.trades
        
        if not trades:
            return BacktestResult(
                total_return=0, total_pnl=0, sharpe_ratio=0, sortino_ratio=0,
                max_drawdown=0, total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, profit_factor=0, avg_win=0, avg_loss=0,
                avg_win_pct=0, avg_loss_pct=0, avg_trade_duration=timedelta(0),
                max_consecutive_wins=0, max_consecutive_losses=0,
                best_trade=0, worst_trade=0,
                trades=[], equity_curve=pd.Series(),
                start_date=data.index[0], end_date=data.index[-1],
                initial_capital=self.initial_capital, final_capital=self.current_capital,
            )
        
        # Podstawowe statystyki
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]
        
        total_trades = len(trades)
        winning_trades = len(winners)
        losing_trades = len(losers)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L
        total_pnl = sum(t.pnl for t in trades)
        total_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        
        # Średnie
        avg_win = np.mean([t.pnl for t in winners]) if winners else 0
        avg_loss = np.mean([t.pnl for t in losers]) if losers else 0
        avg_win_pct = np.mean([t.pnl_pct for t in winners]) if winners else 0
        avg_loss_pct = np.mean([t.pnl_pct for t in losers]) if losers else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winners) if winners else 0
        gross_loss = abs(sum(t.pnl for t in losers)) if losers else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Duration
        avg_duration = np.mean([t.duration for t in trades]) if trades else timedelta(0)
        
        # Best/Worst
        best_trade = max(t.pnl_pct for t in trades) if trades else 0
        worst_trade = min(t.pnl_pct for t in trades) if trades else 0
        
        # Consecutive wins/losses
        max_cons_wins, max_cons_losses = self._calc_consecutive(trades)
        
        # Equity curve
        equity_df = pd.DataFrame(self.equity_curve, columns=['date', 'equity'])
        equity_df.set_index('date', inplace=True)
        equity_series = equity_df['equity']
        
        # Daily returns
        daily_returns = equity_series.pct_change().dropna()
        
        # Sharpe & Sortino
        sharpe = self._calc_sharpe(daily_returns)
        sortino = self._calc_sortino(daily_returns)
        
        # Max Drawdown
        max_dd = self._calc_max_drawdown(equity_series)
        
        return BacktestResult(
            total_return=total_return,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            avg_trade_duration=avg_duration,
            max_consecutive_wins=max_cons_wins,
            max_consecutive_losses=max_cons_losses,
            best_trade=best_trade,
            worst_trade=worst_trade,
            trades=trades,
            equity_curve=equity_series,
            daily_returns=daily_returns,
            start_date=data.index[0],
            end_date=data.index[-1],
            initial_capital=self.initial_capital,
            final_capital=self.current_capital,
        )
    
    def _calc_sharpe(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Oblicza Sharpe Ratio (annualized)."""
        if returns.empty or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        return np.sqrt(252) * excess_returns.mean() / returns.std()
    
    def _calc_sortino(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Oblicza Sortino Ratio (tylko downside volatility)."""
        if returns.empty:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        downside_returns = returns[returns < 0]
        
        if downside_returns.empty or downside_returns.std() == 0:
            return 0.0
        
        return np.sqrt(252) * excess_returns.mean() / downside_returns.std()
    
    def _calc_max_drawdown(self, equity: pd.Series) -> float:
        """Oblicza maksymalny drawdown w %."""
        if equity.empty:
            return 0.0
        
        peak = equity.expanding(min_periods=1).max()
        drawdown = (equity - peak) / peak
        return abs(drawdown.min()) * 100
    
    def _calc_consecutive(self, trades: List[Trade]) -> Tuple[int, int]:
        """Oblicza maksymalne serie wygranych/przegranych."""
        if not trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in trades:
            if trade.is_winner:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def generate_report(self, result: BacktestResult) -> str:
        """Generuje tekstowy raport z wynikami."""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    RAPORT BACKTESTINGU                       ║
║                  Trading Decision System                      ║
╠══════════════════════════════════════════════════════════════╣
║  Okres: {result.start_date.strftime('%Y-%m-%d')} - {result.end_date.strftime('%Y-%m-%d')}
║  Kapitał początkowy: {result.initial_capital:,.2f} PLN
║  Kapitał końcowy: {result.final_capital:,.2f} PLN
╠══════════════════════════════════════════════════════════════╣
║                      METRYKI GŁÓWNE                          ║
╠══════════════════════════════════════════════════════════════╣
║  Całkowity zwrot:       {result.total_return:+.2f}%
║  Całkowity P&L:         {result.total_pnl:+,.2f} PLN
║  Sharpe Ratio:          {result.sharpe_ratio:.2f}
║  Sortino Ratio:         {result.sortino_ratio:.2f}
║  Max Drawdown:          {result.max_drawdown:.2f}%
║  Profit Factor:         {result.profit_factor:.2f}
╠══════════════════════════════════════════════════════════════╣
║                   STATYSTYKI TRANSAKCJI                      ║
╠══════════════════════════════════════════════════════════════╣
║  Liczba transakcji:     {result.total_trades}
║  Wygrane:               {result.winning_trades} ({result.win_rate*100:.1f}%)
║  Przegrane:             {result.losing_trades}
║  Średnia wygrana:       {result.avg_win_pct:+.2f}%
║  Średnia przegrana:     {result.avg_loss_pct:.2f}%
║  Najlepsza transakcja:  {result.best_trade:+.2f}%
║  Najgorsza transakcja:  {result.worst_trade:.2f}%
║  Max wygranych z rzędu: {result.max_consecutive_wins}
║  Max przegranych z rzędu: {result.max_consecutive_losses}
╠══════════════════════════════════════════════════════════════╣
║                        OCENA                                 ║
╠══════════════════════════════════════════════════════════════╣
"""
        # Ocena
        if result.sharpe_ratio >= 1.5:
            rating = "⭐⭐⭐ EXCELLENT"
        elif result.sharpe_ratio >= 1.0:
            rating = "⭐⭐ GOOD"
        elif result.sharpe_ratio >= 0.5:
            rating = "⭐ ACCEPTABLE"
        else:
            rating = "❌ POOR - NIE UŻYWAJ!"
        
        report += f"║  {rating}\n"
        report += "╚══════════════════════════════════════════════════════════════╝"
        
        return report


# Przykład użycia
if __name__ == "__main__":
    import yfinance as yf
    import sys
    from pathlib import Path
    
    # Dodaj projekt do path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from models.technical import IndicatorEngine
    from strategies.forex import MeanReversionStrategy
    
    logging.basicConfig(level=logging.INFO)
    
    # Pobierz dane
    print("Pobieranie danych EUR/PLN...")
    ticker = yf.Ticker("EURPLN=X")
    data = ticker.history(period="2y")
    
    if data.empty:
        print("Brak danych!")
        exit(1)
    
    print(f"Pobrano {len(data)} dni danych")
    
    # Przygotuj dane
    engine = IndicatorEngine()
    data = engine.calculate_all(data)
    
    # Strategia
    strategy = MeanReversionStrategy()
    
    def signal_generator(df: pd.DataFrame, idx: int) -> Dict:
        return strategy.generate_signal(df['Close'], vix=20)
    
    # Backtest
    bt = BacktestEngine(initial_capital=10000)
    result = bt.run(
        data=data,
        signal_generator=signal_generator,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
    )
    
    # Raport
    print(bt.generate_report(result))
