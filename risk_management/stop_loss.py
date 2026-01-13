"""
Stop Loss Calculator - różne metody obliczania stop loss.
"""
import pandas as pd
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class StopLossCalculator:
    """
    Oblicza poziomy stop loss i take profit.
    
    Metody:
    - Fixed Percentage: Stały % od ceny wejścia
    - ATR-Based: Bazowany na Average True Range
    - Support/Resistance: Bazowany na poziomach technicznych
    - Trailing Stop: Dynamiczny trailing stop
    """
    
    def __init__(self, default_sl_pct: float = 0.02, default_rr_ratio: float = 2.0):
        """
        Args:
            default_sl_pct: Domyślny stop loss jako % (2%)
            default_rr_ratio: Domyślny risk/reward ratio dla TP
        """
        self.default_sl_pct = default_sl_pct
        self.default_rr_ratio = default_rr_ratio
    
    def fixed_percentage(
        self,
        entry_price: float,
        direction: str,  # 'long' lub 'short'
        sl_pct: float = None,
        tp_pct: float = None,
    ) -> Dict:
        """
        Stop loss i take profit jako stały % od ceny wejścia.
        
        Args:
            entry_price: Cena wejścia
            direction: 'long' lub 'short'
            sl_pct: Stop loss jako % (domyślnie 2%)
            tp_pct: Take profit jako % (domyślnie SL * RR ratio)
        
        Returns:
            Dict z cenami SL i TP
        """
        sl_pct = sl_pct or self.default_sl_pct
        tp_pct = tp_pct or (sl_pct * self.default_rr_ratio)
        
        if direction.lower() == 'long':
            stop_loss = entry_price * (1 - sl_pct)
            take_profit = entry_price * (1 + tp_pct)
        else:
            stop_loss = entry_price * (1 + sl_pct)
            take_profit = entry_price * (1 - tp_pct)
        
        return {
            'entry_price': entry_price,
            'direction': direction,
            'stop_loss': round(stop_loss, 5),
            'take_profit': round(take_profit, 5),
            'sl_pct': sl_pct,
            'tp_pct': tp_pct,
            'risk_reward': tp_pct / sl_pct,
            'method': 'fixed_percentage',
        }
    
    def atr_based(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        sl_multiplier: float = 1.5,
        tp_multiplier: float = 3.0,
    ) -> Dict:
        """
        Stop loss bazowany na ATR.
        
        Zalety:
        - Dostosowuje się do zmienności rynku
        - Większa zmienność = szerszy SL (mniej whipsaws)
        
        Args:
            entry_price: Cena wejścia
            atr: Average True Range
            direction: 'long' lub 'short'
            sl_multiplier: SL = ATR * multiplier (typowo 1.5-2.0)
            tp_multiplier: TP = ATR * multiplier (typowo 2.0-3.0)
        
        Returns:
            Dict z cenami SL i TP
        """
        sl_distance = atr * sl_multiplier
        tp_distance = atr * tp_multiplier
        
        if direction.lower() == 'long':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        sl_pct = sl_distance / entry_price
        tp_pct = tp_distance / entry_price
        
        return {
            'entry_price': entry_price,
            'direction': direction,
            'stop_loss': round(stop_loss, 5),
            'take_profit': round(take_profit, 5),
            'sl_pct': sl_pct,
            'tp_pct': tp_pct,
            'atr': atr,
            'sl_multiplier': sl_multiplier,
            'tp_multiplier': tp_multiplier,
            'risk_reward': tp_multiplier / sl_multiplier,
            'method': 'atr_based',
        }
    
    def adaptive_sl(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        horizon: str,
        pivots: Dict = None,
        vix: float = 20,
        trend_strength: float = 0.5,
    ) -> Dict:
        """
        Adaptive Stop Loss v2.0.
        
        Łączy ATR-based i structure-based, używa MAX dla bezpieczeństwa.
        Automatycznie dostosowuje mnożniki do horyzontu i warunków.
        
        Args:
            entry_price: Cena wejścia
            atr: Average True Range
            direction: 'long' lub 'short'
            horizon: 'DAILY', 'WEEKLY', 'MONTHLY'
            pivots: Dict z Pivot Points (opcjonalne, dla structure-based)
            vix: Wartość VIX (dla dostosowania mnożników)
            trend_strength: Siła trendu 0-1 (dla R:R ratio)
        
        Returns:
            Dict z adaptacyjnym SL/TP
        """
        # Mnożniki bazowe per horyzont
        HORIZON_SL_MULTIPLIERS = {
            "DAILY": (0.8, 1.2),
            "WEEKLY": (1.2, 1.8),
            "MONTHLY": (2.0, 2.5),
        }
        
        HORIZON_RR_RATIOS = {
            "DAILY": (1.0, 1.8),
            "WEEKLY": (1.5, 2.5),
            "MONTHLY": (2.0, 3.0),
        }
        
        horizon = horizon.upper()
        min_mult, max_mult = HORIZON_SL_MULTIPLIERS.get(horizon, (1.0, 1.5))
        min_rr, max_rr = HORIZON_RR_RATIOS.get(horizon, (1.5, 2.0))
        
        # Dostosuj do VIX (wysokie VIX = szerszy SL)
        if vix > 25:
            sl_multiplier = max_mult
        elif vix < 15:
            sl_multiplier = min_mult
        else:
            sl_multiplier = (min_mult + max_mult) / 2
        
        # Dostosuj R:R do trend_strength
        rr_ratio = min_rr + (max_rr - min_rr) * trend_strength
        
        # ATR-based SL
        atr_sl_distance = atr * sl_multiplier
        
        # Structure-based SL (z pivot points)
        structure_sl_distance = 0
        structure_level = None
        
        if pivots:
            if direction.lower() == 'long':
                # Dla LONG: SL pod S1 lub PP
                s1 = pivots.get('S1', 0)
                pp = pivots.get('PP', 0)
                
                if s1 > 0 and s1 < entry_price:
                    structure_sl_distance = (entry_price - s1) * 1.01  # 1% buffer
                    structure_level = 'S1'
                elif pp > 0 and pp < entry_price:
                    structure_sl_distance = (entry_price - pp) * 1.01
                    structure_level = 'PP'
            else:
                # Dla SHORT: SL nad R1 lub PP
                r1 = pivots.get('R1', float('inf'))
                pp = pivots.get('PP', float('inf'))
                
                if r1 < float('inf') and r1 > entry_price:
                    structure_sl_distance = (r1 - entry_price) * 1.01
                    structure_level = 'R1'
                elif pp < float('inf') and pp > entry_price:
                    structure_sl_distance = (pp - entry_price) * 1.01
                    structure_level = 'PP'
        
        # Użyj MAX (szerszy = bezpieczniejszy)
        if structure_sl_distance > 0:
            final_sl_distance = max(atr_sl_distance, structure_sl_distance)
            method_used = 'structure' if structure_sl_distance >= atr_sl_distance else 'atr'
        else:
            final_sl_distance = atr_sl_distance
            method_used = 'atr'
        
        # Oblicz TP
        tp_distance = final_sl_distance * rr_ratio
        
        # Finalne ceny
        if direction.lower() == 'long':
            stop_loss = entry_price - final_sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + final_sl_distance
            take_profit = entry_price - tp_distance
        
        sl_pct = final_sl_distance / entry_price
        tp_pct = tp_distance / entry_price
        
        return {
            'entry_price': entry_price,
            'direction': direction,
            'stop_loss': round(stop_loss, 5),
            'take_profit': round(take_profit, 5),
            'sl_pct': round(sl_pct, 4),
            'tp_pct': round(tp_pct, 4),
            'risk_reward': round(rr_ratio, 2),
            
            # Metadane adaptive
            'method': 'adaptive',
            'method_used': method_used,
            'horizon': horizon,
            
            # Szczegóły
            'atr_sl_distance': round(atr_sl_distance, 5),
            'structure_sl_distance': round(structure_sl_distance, 5) if structure_sl_distance else None,
            'structure_level': structure_level,
            'sl_multiplier': round(sl_multiplier, 2),
            'vix': vix,
        }
    
    def trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        highest_price: float,  # Dla long
        lowest_price: float,   # Dla short
        direction: str,
        trail_pct: float = 0.02,
    ) -> Dict:
        """
        Trailing stop - podąża za ceną.
        
        Dla LONG: SL = highest_price * (1 - trail_pct)
        Dla SHORT: SL = lowest_price * (1 + trail_pct)
        
        Args:
            entry_price: Cena wejścia
            current_price: Aktualna cena
            highest_price: Najwyższa cena od wejścia (long)
            lowest_price: Najniższa cena od wejścia (short)
            direction: 'long' lub 'short'
            trail_pct: Trailing distance jako %
        
        Returns:
            Dict z aktualnym trailing stop
        """
        if direction.lower() == 'long':
            trailing_stop = highest_price * (1 - trail_pct)
            # SL nie może być niżej niż initial SL
            initial_sl = entry_price * (1 - trail_pct)
            trailing_stop = max(trailing_stop, initial_sl)
            
            # Czy SL triggered?
            triggered = current_price <= trailing_stop
            
        else:
            trailing_stop = lowest_price * (1 + trail_pct)
            initial_sl = entry_price * (1 + trail_pct)
            trailing_stop = min(trailing_stop, initial_sl)
            
            triggered = current_price >= trailing_stop
        
        return {
            'entry_price': entry_price,
            'current_price': current_price,
            'direction': direction,
            'trailing_stop': round(trailing_stop, 5),
            'trail_pct': trail_pct,
            'triggered': triggered,
            'method': 'trailing_stop',
        }
    
    def chandelier_exit(
        self,
        entry_price: float,
        highest_high: float,
        lowest_low: float,
        atr: float,
        direction: str,
        multiplier: float = 3.0,
    ) -> Dict:
        """
        Chandelier Exit - trailing stop bazowany na ATR.
        
        Dla LONG: SL = Highest High - ATR * multiplier
        Dla SHORT: SL = Lowest Low + ATR * multiplier
        
        Lepszy niż zwykły trailing bo dostosowuje się do zmienności.
        """
        if direction.lower() == 'long':
            stop_loss = highest_high - (atr * multiplier)
        else:
            stop_loss = lowest_low + (atr * multiplier)
        
        return {
            'entry_price': entry_price,
            'direction': direction,
            'stop_loss': round(stop_loss, 5),
            'atr': atr,
            'multiplier': multiplier,
            'method': 'chandelier_exit',
        }
    
    def support_resistance_based(
        self,
        entry_price: float,
        direction: str,
        support_level: float,
        resistance_level: float,
        buffer_pct: float = 0.001,  # 0.1% buffer
    ) -> Dict:
        """
        Stop loss bazowany na poziomach wsparcia/oporu.
        
        Dla LONG: SL tuż pod wsparciem
        Dla SHORT: SL tuż nad oporem
        
        Args:
            entry_price: Cena wejścia
            direction: 'long' lub 'short'
            support_level: Poziom wsparcia
            resistance_level: Poziom oporu
            buffer_pct: Buffer pod/nad poziomem
        
        Returns:
            Dict z cenami SL i TP
        """
        if direction.lower() == 'long':
            stop_loss = support_level * (1 - buffer_pct)
            take_profit = resistance_level * (1 - buffer_pct)
        else:
            stop_loss = resistance_level * (1 + buffer_pct)
            take_profit = support_level * (1 + buffer_pct)
        
        sl_pct = abs(entry_price - stop_loss) / entry_price
        tp_pct = abs(take_profit - entry_price) / entry_price
        
        return {
            'entry_price': entry_price,
            'direction': direction,
            'stop_loss': round(stop_loss, 5),
            'take_profit': round(take_profit, 5),
            'support': support_level,
            'resistance': resistance_level,
            'sl_pct': sl_pct,
            'tp_pct': tp_pct,
            'risk_reward': tp_pct / sl_pct if sl_pct > 0 else 0,
            'method': 'support_resistance',
        }
    
    def calculate_breakeven_price(
        self,
        entry_price: float,
        position_size: float,
        commission_pct: float = 0.001,
        direction: str = 'long',
    ) -> float:
        """
        Oblicza cenę breakeven (po prowizjach).
        
        Returns:
            Cena przy której nie ma ani zysku ani straty
        """
        total_commission = 2 * commission_pct  # Entry + exit
        
        if direction.lower() == 'long':
            return entry_price * (1 + total_commission)
        else:
            return entry_price * (1 - total_commission)


# Przykład użycia
if __name__ == "__main__":
    calc = StopLossCalculator(default_sl_pct=0.02, default_rr_ratio=2.0)
    
    entry = 4.35  # EUR/PLN
    atr = 0.02
    
    print("Stop Loss Calculator Examples")
    print("=" * 50)
    
    # Fixed
    fixed = calc.fixed_percentage(entry, 'long', sl_pct=0.02)
    print(f"\n1. Fixed 2%:")
    print(f"   Entry: {fixed['entry_price']}")
    print(f"   SL: {fixed['stop_loss']} (-{fixed['sl_pct']:.2%})")
    print(f"   TP: {fixed['take_profit']} (+{fixed['tp_pct']:.2%})")
    print(f"   R:R = 1:{fixed['risk_reward']:.1f}")
    
    # ATR-based
    atr_sl = calc.atr_based(entry, atr, 'long', sl_multiplier=1.5, tp_multiplier=3.0)
    print(f"\n2. ATR-based (ATR={atr}):")
    print(f"   SL: {atr_sl['stop_loss']} (-{atr_sl['sl_pct']:.2%})")
    print(f"   TP: {atr_sl['take_profit']} (+{atr_sl['tp_pct']:.2%})")
    print(f"   R:R = 1:{atr_sl['risk_reward']:.1f}")
    
    # Trailing
    trail = calc.trailing_stop(
        entry_price=entry,
        current_price=4.40,
        highest_price=4.42,
        lowest_price=4.35,
        direction='long',
        trail_pct=0.02
    )
    print(f"\n3. Trailing Stop (entry={entry}, highest={4.42}):")
    print(f"   Trailing SL: {trail['trailing_stop']}")
    print(f"   Triggered: {trail['triggered']}")
