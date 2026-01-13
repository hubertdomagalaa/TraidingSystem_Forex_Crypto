"""
Drawdown Monitor - monitoruje drawdown i blokuje trading gdy przekroczony.
"""
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class DailyStats:
    """Statystyki dzienne."""
    date: date
    starting_equity: float
    ending_equity: float
    pnl: float
    pnl_pct: float
    trades_count: int
    wins: int
    losses: int


class DrawdownMonitor:
    """
    Monitoruje drawdown i blokuje trading gdy limity przekroczone.
    
    Limity:
    - Daily drawdown (np. max 5% straty dziennie)
    - Total drawdown (np. max 15% od peak equity)
    - Consecutive losses (np. max 5 strat z rzędu)
    
    Gdy limit przekroczony → STOP TRADING!
    """
    
    def __init__(
        self,
        initial_equity: float = 10000,
        max_daily_drawdown_pct: float = 0.05,      # 5% max dzienna strata
        max_total_drawdown_pct: float = 0.15,      # 15% max całkowita strata
        max_consecutive_losses: int = 5,           # 5 strat z rzędu = stop
        cooldown_hours: int = 24,                  # Czas cooldown po przekroczeniu
    ):
        """
        Args:
            initial_equity: Kapitał początkowy
            max_daily_drawdown_pct: Max dzienny drawdown
            max_total_drawdown_pct: Max całkowity drawdown od peak
            max_consecutive_losses: Max strat z rzędu
            cooldown_hours: Czas cooldown po limicie
        """
        self.initial_equity = initial_equity
        self.max_daily_dd_pct = max_daily_drawdown_pct
        self.max_total_dd_pct = max_total_drawdown_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_hours = cooldown_hours
        
        # Stan
        self.current_equity = initial_equity
        self.peak_equity = initial_equity
        self.day_start_equity = initial_equity
        
        # Tracking
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.trades_today = 0
        self.pnl_today = 0
        
        # Historia
        self.daily_stats: List[DailyStats] = []
        self.last_reset_date = date.today()
        
        # Blokada
        self.trading_blocked = False
        self.block_reason = ""
        self.block_until: Optional[datetime] = None
    
    def record_trade(self, pnl: float, is_winner: bool = None) -> Dict:
        """
        Zapisuje wynik transakcji i sprawdza limity.
        
        Args:
            pnl: Profit/Loss z transakcji
            is_winner: Czy wygrana (auto-detect jeśli None)
        
        Returns:
            Dict ze statusem i informacjami
        """
        # Auto-detect winner
        if is_winner is None:
            is_winner = pnl > 0
        
        # Aktualizuj equity
        self.current_equity += pnl
        self.peak_equity = max(self.peak_equity, self.current_equity)
        
        # Daily stats
        self.trades_today += 1
        self.pnl_today += pnl
        
        # Consecutive
        if is_winner:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Reset dzienny jeśli nowy dzień
        self._check_new_day()
        
        # Sprawdź limity
        status = self._check_limits()
        
        logger.info(
            f"Trade recorded: PnL={pnl:+.2f}, "
            f"Equity={self.current_equity:.2f}, "
            f"Consecutive={self.consecutive_losses}L/{self.consecutive_wins}W"
        )
        
        return status
    
    def can_trade(self) -> bool:
        """
        Sprawdza czy można handlować.
        
        Returns:
            True jeśli trading dozwolony
        """
        # Reset dzienny check
        self._check_new_day()
        
        # Sprawdź cooldown
        if self.block_until and datetime.now() < self.block_until:
            return False
        elif self.block_until and datetime.now() >= self.block_until:
            self._clear_block()
        
        # Sprawdź limity
        status = self._check_limits()
        
        return not self.trading_blocked
    
    def get_status(self) -> Dict:
        """Zwraca aktualny status."""
        daily_dd = self._calc_daily_drawdown()
        total_dd = self._calc_total_drawdown()
        
        return {
            'can_trade': self.can_trade(),
            'blocked': self.trading_blocked,
            'block_reason': self.block_reason,
            'block_until': self.block_until.isoformat() if self.block_until else None,
            
            'current_equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'initial_equity': self.initial_equity,
            
            'daily_drawdown_pct': daily_dd,
            'daily_dd_limit': self.max_daily_dd_pct,
            'daily_dd_remaining': self.max_daily_dd_pct - daily_dd,
            
            'total_drawdown_pct': total_dd,
            'total_dd_limit': self.max_total_dd_pct,
            'total_dd_remaining': self.max_total_dd_pct - total_dd,
            
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_losses': self.max_consecutive_losses,
            
            'trades_today': self.trades_today,
            'pnl_today': self.pnl_today,
        }
    
    def _check_limits(self) -> Dict:
        """Sprawdza wszystkie limity."""
        daily_dd = self._calc_daily_drawdown()
        total_dd = self._calc_total_drawdown()
        
        # Daily drawdown
        if daily_dd >= self.max_daily_dd_pct:
            self._block_trading(
                f"Daily drawdown limit reached: {daily_dd:.1%} >= {self.max_daily_dd_pct:.1%}"
            )
        
        # Total drawdown
        elif total_dd >= self.max_total_dd_pct:
            self._block_trading(
                f"Total drawdown limit reached: {total_dd:.1%} >= {self.max_total_dd_pct:.1%}",
                hours=self.cooldown_hours * 2  # Dłuższy cooldown
            )
        
        # Consecutive losses
        elif self.consecutive_losses >= self.max_consecutive_losses:
            self._block_trading(
                f"Consecutive losses limit: {self.consecutive_losses} >= {self.max_consecutive_losses}"
            )
        
        return self.get_status()
    
    def _calc_daily_drawdown(self) -> float:
        """Oblicza dzienny drawdown (od początku dnia)."""
        if self.day_start_equity == 0:
            return 0
        return max(0, (self.day_start_equity - self.current_equity) / self.day_start_equity)
    
    def _calc_total_drawdown(self) -> float:
        """Oblicza całkowity drawdown (od peak)."""
        if self.peak_equity == 0:
            return 0
        return max(0, (self.peak_equity - self.current_equity) / self.peak_equity)
    
    def _block_trading(self, reason: str, hours: int = None):
        """Blokuje trading."""
        hours = hours or self.cooldown_hours
        
        self.trading_blocked = True
        self.block_reason = reason
        self.block_until = datetime.now().replace(
            hour=datetime.now().hour + hours
        )
        
        logger.warning(f"🚫 TRADING BLOCKED: {reason}")
        logger.warning(f"   Block until: {self.block_until}")
    
    def _clear_block(self):
        """Usuwa blokadę."""
        self.trading_blocked = False
        self.block_reason = ""
        self.block_until = None
        
        logger.info("✅ Trading block cleared")
    
    def _check_new_day(self):
        """Sprawdza czy nowy dzień i resetuje daily stats."""
        today = date.today()
        
        if today > self.last_reset_date:
            # Zapisz statystyki poprzedniego dnia
            if self.trades_today > 0:
                daily_stat = DailyStats(
                    date=self.last_reset_date,
                    starting_equity=self.day_start_equity,
                    ending_equity=self.current_equity,
                    pnl=self.pnl_today,
                    pnl_pct=self.pnl_today / self.day_start_equity if self.day_start_equity > 0 else 0,
                    trades_count=self.trades_today,
                    wins=0,  # TODO: track this
                    losses=0,
                )
                self.daily_stats.append(daily_stat)
            
            # Reset
            self.day_start_equity = self.current_equity
            self.trades_today = 0
            self.pnl_today = 0
            self.last_reset_date = today
            
            # Clear daily block (ale nie total dd block)
            if self.trading_blocked and "Daily" in self.block_reason:
                self._clear_block()
    
    def force_unblock(self):
        """Wymusza odblokowanie (użyj ostrożnie!)."""
        logger.warning("⚠️ Force unblock - use with caution!")
        self._clear_block()
    
    def update_equity(self, new_equity: float):
        """Aktualizuje equity bez trade'a."""
        self.current_equity = new_equity
        self.peak_equity = max(self.peak_equity, new_equity)


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    monitor = DrawdownMonitor(
        initial_equity=10000,
        max_daily_drawdown_pct=0.05,
        max_total_drawdown_pct=0.15,
        max_consecutive_losses=3,
    )
    
    print("Drawdown Monitor Demo")
    print("=" * 50)
    
    # Symulacja transakcji
    trades = [
        100,   # Win
        -50,   # Loss
        150,   # Win  
        -200,  # Loss
        -150,  # Loss
        -100,  # Loss - powinno zablokować!
    ]
    
    for i, pnl in enumerate(trades, 1):
        print(f"\n--- Trade {i}: PnL = {pnl:+} ---")
        status = monitor.record_trade(pnl)
        
        print(f"Equity: {status['current_equity']:.2f}")
        print(f"Daily DD: {status['daily_drawdown_pct']:.2%}")
        print(f"Total DD: {status['total_drawdown_pct']:.2%}")
        print(f"Consecutive losses: {status['consecutive_losses']}")
        print(f"Can trade: {status['can_trade']}")
        
        if status['blocked']:
            print(f"🚫 BLOCKED: {status['block_reason']}")
            break
