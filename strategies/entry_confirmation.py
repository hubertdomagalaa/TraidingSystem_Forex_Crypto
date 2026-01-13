"""
Entry Confirmation v2.0 - REQUIRED vs OPTIONAL conditions.

Zmiana z v1.0:
- Zamiast "4 z 7 warunków" → hierarchia REQUIRED + OPTIONAL
- REQUIRED: WSZYSTKIE muszą być spełnione
- OPTIONAL: Bonus do confidence, nie blokują

v2.0 - Refaktoryzacja z "magic number" na logiczną hierarchię
"""
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConditionPriority(Enum):
    """Priorytet warunku."""
    REQUIRED = "required"   # Musi być spełniony
    OPTIONAL = "optional"   # Bonus do confidence


@dataclass
class Condition:
    """Definicja pojedynczego warunku."""
    name: str
    priority: ConditionPriority
    check_fn: Callable[[Dict], bool]
    description: str = ""


@dataclass
class ConfirmationResultV2:
    """Wynik sprawdzenia potwierdzeń v2.0."""
    confirmed: bool
    direction: str  # 'LONG', 'SHORT', 'NONE'
    
    # Nowe pola
    required_met: List[str] = field(default_factory=list)
    required_failed: List[str] = field(default_factory=list)
    optional_met: List[str] = field(default_factory=list)
    optional_missed: List[str] = field(default_factory=list)
    
    # Confidence
    base_confidence: float = 0.5
    optional_bonus: float = 0.0
    final_confidence: float = 0.5
    
    # Block reason
    block_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Konwertuje do słownika."""
        return {
            "confirmed": self.confirmed,
            "direction": self.direction,
            "confidence": round(self.final_confidence, 3),
            "required_met": self.required_met,
            "required_failed": self.required_failed,
            "optional_met": self.optional_met,
            "optional_missed": self.optional_missed,
            "block_reason": self.block_reason,
        }


class EntryConfirmationV2:
    """
    Entry Confirmation v2.0 z podziałem REQUIRED vs OPTIONAL.
    
    Logika:
    1. Sprawdź WSZYSTKIE warunki REQUIRED
    2. Jeśli którykolwiek REQUIRED failed → NO ENTRY
    3. Sprawdź warunki OPTIONAL → bonus do confidence
    4. Final confidence = base + optional_bonus
    """
    
    def __init__(self, base_confidence: float = 0.5, optional_bonus_per_condition: float = 0.1):
        """
        Args:
            base_confidence: Bazowy confidence gdy wszystkie REQUIRED spełnione
            optional_bonus_per_condition: Bonus za każdy spełniony OPTIONAL
        """
        self.base_confidence = base_confidence
        self.optional_bonus = optional_bonus_per_condition
        
        # Definicje warunków per kierunek
        self._define_conditions()
    
    def _define_conditions(self):
        """Definiuje warunki dla LONG i SHORT."""
        
        # ==========================================
        # LONG CONDITIONS
        # ==========================================
        self.long_required = [
            Condition(
                name="session_ok",
                priority=ConditionPriority.REQUIRED,
                check_fn=lambda s: s.get('is_good_time', True),
                description="Trading session is open and not in avoid time",
            ),
            Condition(
                name="volatility_ok",
                priority=ConditionPriority.REQUIRED,
                check_fn=lambda s: s.get('vix', 20) <= 30,
                description="VIX is not extremely high",
            ),
            Condition(
                name="htf_not_bearish",
                priority=ConditionPriority.REQUIRED,
                check_fn=lambda s: s.get('trend_4h') != 'down',
                description="Higher timeframe (4H) is not bearish",
            ),
            Condition(
                name="price_location_ok",
                priority=ConditionPriority.REQUIRED,
                check_fn=lambda s: s.get('price', 0) > s.get('vwap', 0) or s.get('price', 0) > s.get('pivot_s1', 0),
                description="Price above VWAP or above S1 pivot",
            ),
        ]
        
        self.long_optional = [
            Condition(
                name="trend_1h_up",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('trend_1h') == 'up',
                description="1H trend is bullish",
            ),
            Condition(
                name="rsi_not_overbought",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('rsi', 50) < 70,
                description="RSI not overbought",
            ),
            Condition(
                name="adx_trend_present",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('adx', 20) > 20,
                description="ADX shows trend presence",
            ),
            Condition(
                name="above_pivot_pp",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('price', 0) > s.get('pivot_pp', 0),
                description="Price above pivot point",
            ),
            Condition(
                name="momentum_positive",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('macd_hist', 0) > 0,
                description="MACD histogram positive",
            ),
        ]
        
        # ==========================================
        # SHORT CONDITIONS
        # ==========================================
        self.short_required = [
            Condition(
                name="session_ok",
                priority=ConditionPriority.REQUIRED,
                check_fn=lambda s: s.get('is_good_time', True),
                description="Trading session is open",
            ),
            Condition(
                name="volatility_ok",
                priority=ConditionPriority.REQUIRED,
                check_fn=lambda s: s.get('vix', 20) <= 30,
                description="VIX is not extremely high",
            ),
            Condition(
                name="htf_not_bullish",
                priority=ConditionPriority.REQUIRED,
                check_fn=lambda s: s.get('trend_4h') != 'up',
                description="Higher timeframe (4H) is not bullish",
            ),
            Condition(
                name="price_location_ok",
                priority=ConditionPriority.REQUIRED,
                check_fn=lambda s: s.get('price', 0) < s.get('vwap', 0) or s.get('price', 0) < s.get('pivot_r1', float('inf')),
                description="Price below VWAP or below R1 pivot",
            ),
        ]
        
        self.short_optional = [
            Condition(
                name="trend_1h_down",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('trend_1h') == 'down',
                description="1H trend is bearish",
            ),
            Condition(
                name="rsi_not_oversold",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('rsi', 50) > 30,
                description="RSI not oversold",
            ),
            Condition(
                name="adx_trend_present",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('adx', 20) > 20,
                description="ADX shows trend presence",
            ),
            Condition(
                name="below_pivot_pp",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('price', 0) < s.get('pivot_pp', float('inf')),
                description="Price below pivot point",
            ),
            Condition(
                name="momentum_negative",
                priority=ConditionPriority.OPTIONAL,
                check_fn=lambda s: s.get('macd_hist', 0) < 0,
                description="MACD histogram negative",
            ),
        ]
    
    def check_long(self, signals: Dict) -> ConfirmationResultV2:
        """Sprawdza warunki dla LONG entry."""
        return self._check_direction("LONG", signals, self.long_required, self.long_optional)
    
    def check_short(self, signals: Dict) -> ConfirmationResultV2:
        """Sprawdza warunki dla SHORT entry."""
        return self._check_direction("SHORT", signals, self.short_required, self.short_optional)
    
    def check_best_direction(self, signals: Dict) -> ConfirmationResultV2:
        """Sprawdza oba kierunki i zwraca lepszy."""
        long_result = self.check_long(signals)
        short_result = self.check_short(signals)
        
        # Jeśli żaden nie jest confirmed
        if not long_result.confirmed and not short_result.confirmed:
            # Zwróć ten z mniejszą liczbą failed required
            if len(long_result.required_failed) <= len(short_result.required_failed):
                return long_result
            return short_result
        
        # Jeśli tylko jeden confirmed
        if long_result.confirmed and not short_result.confirmed:
            return long_result
        if short_result.confirmed and not long_result.confirmed:
            return short_result
        
        # Oba confirmed - wybierz z wyższym confidence
        if long_result.final_confidence >= short_result.final_confidence:
            return long_result
        return short_result
    
    def _check_direction(
        self,
        direction: str,
        signals: Dict,
        required: List[Condition],
        optional: List[Condition],
    ) -> ConfirmationResultV2:
        """Sprawdza warunki dla danego kierunku."""
        
        required_met = []
        required_failed = []
        optional_met = []
        optional_missed = []
        
        # Sprawdź REQUIRED
        for cond in required:
            try:
                if cond.check_fn(signals):
                    required_met.append(cond.name)
                else:
                    required_failed.append(cond.name)
            except Exception as e:
                logger.warning(f"Condition {cond.name} check failed: {e}")
                required_failed.append(cond.name)
        
        # Jeśli jakikolwiek REQUIRED failed → NO ENTRY
        if required_failed:
            return ConfirmationResultV2(
                confirmed=False,
                direction="NONE",
                required_met=required_met,
                required_failed=required_failed,
                optional_met=[],
                optional_missed=[c.name for c in optional],
                block_reason=f"Required condition failed: {required_failed[0]}",
            )
        
        # Sprawdź OPTIONAL
        for cond in optional:
            try:
                if cond.check_fn(signals):
                    optional_met.append(cond.name)
                else:
                    optional_missed.append(cond.name)
            except:
                optional_missed.append(cond.name)
        
        # Oblicz confidence
        optional_bonus = len(optional_met) * self.optional_bonus
        final_confidence = min(1.0, self.base_confidence + optional_bonus)
        
        return ConfirmationResultV2(
            confirmed=True,
            direction=direction,
            required_met=required_met,
            required_failed=[],
            optional_met=optional_met,
            optional_missed=optional_missed,
            base_confidence=self.base_confidence,
            optional_bonus=optional_bonus,
            final_confidence=final_confidence,
        )
    
    def get_conditions_summary(self, direction: str) -> Dict:
        """Zwraca podsumowanie warunków dla kierunku."""
        if direction.upper() == "LONG":
            required = self.long_required
            optional = self.long_optional
        else:
            required = self.short_required
            optional = self.short_optional
        
        return {
            "direction": direction.upper(),
            "required": [{"name": c.name, "description": c.description} for c in required],
            "optional": [{"name": c.name, "description": c.description} for c in optional],
        }


# Backward compatibility wrapper
class EntryConfirmation:
    """
    Wrapper dla backward compatibility z v1.0 API.
    Wewnętrznie używa EntryConfirmationV2.
    """
    
    def __init__(self, min_confirmations: int = 4):
        """
        Args:
            min_confirmations: Ignored in v2.0, kept for API compatibility
        """
        self._v2 = EntryConfirmationV2()
        logger.info("EntryConfirmation v2.0 initialized (REQUIRED vs OPTIONAL)")
    
    def check_entry(self, signals: Dict, preferred_direction: str = None) -> Dict:
        """
        Sprawdza warunki wejścia (backward compatible API).
        
        Args:
            signals: Dict z sygnałami
            preferred_direction: 'long', 'short', lub None
        
        Returns:
            Dict z wynikiem (backward compatible format)
        """
        # Mapuj nazwy sygnałów z v1 na v2
        mapped_signals = self._map_signals(signals)
        
        if preferred_direction == 'long':
            result = self._v2.check_long(mapped_signals)
        elif preferred_direction == 'short':
            result = self._v2.check_short(mapped_signals)
        else:
            result = self._v2.check_best_direction(mapped_signals)
        
        # Konwertuj do starego formatu
        return self._to_v1_format(result)
    
    def _map_signals(self, signals: Dict) -> Dict:
        """Mapuje sygnały z formatu v1 na v2."""
        return {
            'trend_1h': signals.get('trend_1h'),
            'trend_4h': signals.get('trend_4h'),
            'price': signals.get('price', 0),
            'vwap': signals.get('vwap', 0),
            'rsi': signals.get('rsi', 50),
            'adx': signals.get('adx', 20),
            'is_good_time': signals.get('is_good_time', True),
            'vix': signals.get('vix', 20),
            'pivot_pp': signals.get('pivots', {}).get('PP', 0) if isinstance(signals.get('pivots'), dict) else 0,
            'pivot_s1': signals.get('pivots', {}).get('S1', 0) if isinstance(signals.get('pivots'), dict) else 0,
            'pivot_r1': signals.get('pivots', {}).get('R1', float('inf')) if isinstance(signals.get('pivots'), dict) else float('inf'),
            'macd_hist': signals.get('macd_hist', 0),
        }
    
    def _to_v1_format(self, result: ConfirmationResultV2) -> Dict:
        """Konwertuje wynik v2 do formatu v1."""
        all_confirmations = result.required_met + result.optional_met
        all_missing = result.required_failed + result.optional_missed
        
        if result.confirmed:
            emoji = "🟢" if result.direction == 'LONG' else "🔴"
            action = f"{emoji} {result.direction} CONFIRMED"
        else:
            action = f"⏸️ WAIT - {result.block_reason}"
        
        return {
            'entry': result.confirmed,
            'direction': result.direction.lower() if result.direction != 'NONE' else 'none',
            'confidence': result.final_confidence,
            'achieved': len(all_confirmations),
            'required': len(result.required_met) + len(result.required_failed),
            'confirmations': all_confirmations,
            'missing': all_missing,
            'action': action,
            
            # Nowe pola v2
            'required_met': result.required_met,
            'required_failed': result.required_failed,
            'optional_met': result.optional_met,
            'optional_missed': result.optional_missed,
        }


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test nowego API
    confirmation = EntryConfirmationV2()
    
    signals = {
        'trend_1h': 'up',
        'trend_4h': 'up',
        'price': 4.35,
        'vwap': 4.33,
        'rsi': 55,
        'adx': 28,
        'is_good_time': True,
        'vix': 18,
        'pivot_pp': 4.34,
        'pivot_s1': 4.31,
        'macd_hist': 0.002,
    }
    
    print("=" * 60)
    print("ENTRY CONFIRMATION v2.0 TEST")
    print("=" * 60)
    
    result = confirmation.check_long(signals)
    
    print(f"\nDirection: {result.direction}")
    print(f"Confirmed: {result.confirmed}")
    print(f"Confidence: {result.final_confidence:.2f}")
    
    print(f"\n✅ Required Met: {result.required_met}")
    print(f"❌ Required Failed: {result.required_failed}")
    print(f"\n🟢 Optional Met: {result.optional_met}")
    print(f"⚪ Optional Missed: {result.optional_missed}")
    
    # Test backward compatibility
    print("\n" + "=" * 60)
    print("BACKWARD COMPATIBILITY TEST (v1 API)")
    print("=" * 60)
    
    old_api = EntryConfirmation(min_confirmations=4)
    old_result = old_api.check_entry({
        'trend_1h': 'up',
        'trend_4h': 'up',
        'price': 4.35,
        'vwap': 4.33,
        'rsi': 55,
        'is_good_time': True,
        'adx': 28,
    })
    
    print(f"\n{old_result['action']}")
    print(f"Confidence: {old_result['confidence']:.2f}")
