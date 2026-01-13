"""
Position Sizing - określa wielkość pozycji bazując na różnych metodach.
"""
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Oblicza optymalną wielkość pozycji.
    
    Metody:
    - Fixed Percentage: Stały % kapitału na trade
    - Kelly Criterion: Optymalna wielkość bazowana na win rate
    - Volatility-Based: Bazowana na ATR (większa zmienność = mniejsza pozycja)
    - Risk-Based: Bazowana na odległości do stop loss
    """
    
    def __init__(self, default_risk_pct: float = 0.02):
        """
        Args:
            default_risk_pct: Domyślny % ryzyka na transakcję
        """
        self.default_risk_pct = default_risk_pct
    
    def fixed_percentage(
        self, 
        capital: float, 
        risk_pct: float = None
    ) -> float:
        """
        Stały procent kapitału.
        
        Najprostsza metoda - zawsze ryzykujesz ten sam % kapitału.
        
        Args:
            capital: Aktualny kapitał
            risk_pct: Procent do zaryzykowania (domyślnie 2%)
        
        Returns:
            Wartość pozycji
        """
        risk_pct = risk_pct or self.default_risk_pct
        return capital * risk_pct
    
    def kelly_criterion(
        self, 
        capital: float,
        win_rate: float, 
        avg_win: float, 
        avg_loss: float,
        fraction: float = 0.5
    ) -> float:
        """
        Kelly Criterion z fractional Kelly.
        
        Optymalna wielkość pozycji bazowana na historycznych wynikach.
        
        Formula:
        f* = (p * b - q) / b
        gdzie:
        - p = win rate
        - q = 1 - p (lose rate)
        - b = avg_win / avg_loss (odds)
        
        Używamy fractional Kelly (0.5 = pół-Kelly) dla bezpieczeństwa.
        
        Args:
            capital: Aktualny kapitał
            win_rate: Historyczny win rate (0-1)
            avg_win: Średnia wygrana
            avg_loss: Średnia przegrana (wartość dodatnia)
            fraction: Ułamek Kelly (0.5 = pół-Kelly zalecane)
        
        Returns:
            Wartość pozycji
        """
        if avg_loss == 0 or avg_loss == 0:
            logger.warning("Kelly: avg_loss = 0, używam fixed percentage")
            return self.fixed_percentage(capital)
        
        if win_rate <= 0 or win_rate >= 1:
            logger.warning(f"Kelly: nieprawidłowy win_rate ({win_rate})")
            return self.fixed_percentage(capital)
        
        # Oblicz odds (b)
        b = abs(avg_win / avg_loss)
        
        # Oblicz Kelly
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        
        # Zastosuj fractional i ogranicz
        kelly_fraction = max(0, min(kelly * fraction, 0.25))  # Max 25%
        
        position_value = capital * kelly_fraction
        
        logger.info(f"Kelly: {kelly:.2%} (fraction: {kelly_fraction:.2%})")
        
        return position_value
    
    def volatility_based(
        self,
        capital: float,
        atr: float,
        current_price: float,
        risk_per_trade: float = None,
        atr_multiplier: float = 2.0
    ) -> float:
        """
        Position sizing bazowany na zmienności (ATR).
        
        Logika: Większa zmienność = mniejsza pozycja
        
        Formula:
        position_value = (capital * risk_pct) / (ATR / price * multiplier)
        
        Args:
            capital: Aktualny kapitał
            atr: Average True Range
            current_price: Aktualna cena
            risk_per_trade: Ryzyko na transakcję (domyślnie 2%)
            atr_multiplier: Mnożnik ATR dla stop loss
        
        Returns:
            Wartość pozycji
        """
        risk_per_trade = risk_per_trade or self.default_risk_pct
        
        if atr <= 0 or current_price <= 0:
            logger.warning("Volatility sizing: ATR lub cena <= 0")
            return self.fixed_percentage(capital, risk_per_trade)
        
        # ATR jako % ceny
        atr_pct = atr / current_price
        
        # Stop loss distance (ATR * multiplier)
        sl_distance_pct = atr_pct * atr_multiplier
        
        # Wartość pozycji
        # Jeśli ryzykuję 2% kapitału i SL jest 4% od entry,
        # to mogę kupić za: 2% / 4% = 50% kapitału
        position_value = (capital * risk_per_trade) / sl_distance_pct
        
        # Limit do max 50% kapitału
        position_value = min(position_value, capital * 0.5)
        
        logger.debug(f"Volatility sizing: ATR={atr_pct:.2%}, SL={sl_distance_pct:.2%}, "
                    f"Position={position_value/capital:.2%} kapitału")
        
        return position_value
    
    def risk_based(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        risk_per_trade: float = None
    ) -> float:
        """
        Position sizing bazowany na odległości do stop loss.
        
        Używane gdy masz konkretny poziom SL.
        
        Args:
            capital: Aktualny kapitał
            entry_price: Cena wejścia
            stop_loss_price: Cena stop loss
            risk_per_trade: Ryzyko na transakcję
        
        Returns:
            Wartość pozycji
        """
        risk_per_trade = risk_per_trade or self.default_risk_pct
        
        # Odległość SL jako %
        sl_distance_pct = abs(entry_price - stop_loss_price) / entry_price
        
        if sl_distance_pct == 0:
            logger.warning("Risk-based sizing: SL distance = 0")
            return self.fixed_percentage(capital, risk_per_trade)
        
        # Wartość pozycji
        position_value = (capital * risk_per_trade) / sl_distance_pct
        
        # Limit
        position_value = min(position_value, capital * 0.5)
        
        return position_value
    
    def calculate(
        self,
        method: str,
        capital: float,
        **kwargs
    ) -> Dict:
        """
        Uniwersalna metoda obliczania pozycji.
        
        Args:
            method: 'fixed', 'kelly', 'volatility', 'risk'
            capital: Aktualny kapitał
            **kwargs: Dodatkowe argumenty dla metody
        
        Returns:
            Dict z position_value i metadanymi
        """
        methods = {
            'fixed': self.fixed_percentage,
            'kelly': self.kelly_criterion,
            'volatility': self.volatility_based,
            'risk': self.risk_based,
        }
        
        if method not in methods:
            logger.warning(f"Nieznana metoda: {method}, używam fixed")
            method = 'fixed'
        
        position_value = methods[method](capital, **kwargs)
        
        return {
            'method': method,
            'position_value': position_value,
            'position_pct': position_value / capital,
            'capital': capital,
        }


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    sizer = PositionSizer(default_risk_pct=0.02)
    capital = 10000
    
    print("Position Sizing Examples")
    print("=" * 50)
    
    # Fixed
    fixed = sizer.fixed_percentage(capital, 0.02)
    print(f"\n1. Fixed 2%: {fixed:.2f} PLN ({fixed/capital:.1%} kapitału)")
    
    # Kelly
    kelly = sizer.kelly_criterion(
        capital=capital,
        win_rate=0.55,
        avg_win=100,
        avg_loss=80,
        fraction=0.5
    )
    print(f"2. Kelly (55% WR, 1.25 RR): {kelly:.2f} PLN ({kelly/capital:.1%} kapitału)")
    
    # Volatility
    vol = sizer.volatility_based(
        capital=capital,
        atr=0.05,
        current_price=4.35,  # EUR/PLN
        risk_per_trade=0.02,
    )
    print(f"3. Volatility (ATR=0.05): {vol:.2f} PLN ({vol/capital:.1%} kapitału)")
    
    # Risk-based
    risk = sizer.risk_based(
        capital=capital,
        entry_price=4.35,
        stop_loss_price=4.30,  # SL 5 groszy
        risk_per_trade=0.02,
    )
    print(f"4. Risk-based (SL 5gr): {risk:.2f} PLN ({risk/capital:.1%} kapitału)")
