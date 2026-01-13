"""
Decision Engine - hierarchiczny decision tree zamiast linear voting.

Kluczowa zmiana w v2.0:
- Każdy krok może ZABLOKOWAĆ trade (nie tylko "obniżyć score")
- Sentiment = gate, nie voter
- Horizon określa parametry SL/TP

Flow:
1. Can trade? (session, VIX) → BLOKUJĄCY
2. Market regime? (ADX) → BLOKUJĄCY dla "chaos"
3. Higher TF bias? → OGRANICZAJĄCY (allowed direction)
4. Sentiment gate → OGRANICZAJĄCY
5. Entry conditions → REQUIRED + OPTIONAL
6. Risk check → BLOKUJĄCY
→ ONLY THEN: trade

v2.0 - Refaktoryzacja z linear voting
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

# Importy z nowych modułów
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.sentiment_context import SentimentContext, SentimentRegime
from core.horizon_detector import TradingHorizon, HorizonDetector, HorizonContext

logger = logging.getLogger(__name__)


class DecisionAction(Enum):
    """Możliwe akcje decyzyjne."""
    LONG = "LONG"
    SHORT = "SHORT"
    HOLD = "HOLD"       # Nie handluj, ale możesz obserwować
    STOP = "STOP"       # Nie handluj, sytuacja niebezpieczna
    ERROR = "ERROR"     # Błąd w danych


class BlockReason(Enum):
    """Powody blokady trade'u."""
    SESSION_CLOSED = "Outside trading session"
    VIX_TOO_HIGH = "VIX too high (>30)"
    MARKET_CHAOS = "Market chaos (ADX<15 with high volatility)"
    SENTIMENT_CONFLICT = "Strong sentiment conflict"
    CRITICAL_CONDITIONS_NOT_MET = "Critical entry conditions not met"
    RISK_TOO_HIGH = "Risk parameters exceeded"
    NO_CLEAR_DIRECTION = "No clear direction from signals"
    DATA_ERROR = "Invalid or missing data"


@dataclass
class DecisionResult:
    """Wynik decyzji z pełnym reasoning."""
    action: DecisionAction
    confidence: float           # 0.0 - 1.0
    horizon: Optional[TradingHorizon] = None
    
    # Trade params (jeśli action == LONG/SHORT)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_modifier: float = 1.0
    
    # Reasoning
    block_reason: Optional[BlockReason] = None
    confirmations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    decision_path: List[str] = field(default_factory=list)
    
    # Context
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_trade(self) -> bool:
        """Czy to jest sygnał do otwarcia pozycji."""
        return self.action in [DecisionAction.LONG, DecisionAction.SHORT]
    
    def to_dict(self) -> Dict:
        """Konwertuje do słownika dla JSON output."""
        return {
            "action": self.action.value,
            "confidence": round(self.confidence, 3),
            "horizon": self.horizon.value if self.horizon else None,
            "is_trade": self.is_trade(),
            
            "trade": {
                "entry": self.entry_price,
                "stop_loss": self.stop_loss,
                "take_profit": self.take_profit,
                "position_modifier": self.position_modifier,
            } if self.is_trade() else None,
            
            "reasoning": {
                "block_reason": self.block_reason.value if self.block_reason else None,
                "confirmations": self.confirmations,
                "warnings": self.warnings,
                "decision_path": self.decision_path,
            },
            
            "timestamp": self.timestamp.isoformat(),
        }


class DecisionEngine:
    """
    Hierarchiczny decision engine.
    
    Każdy krok w drzewie może:
    - ALLOW (przejdź dalej)
    - RESTRICT (ogranicz allowed_direction lub position_size)  
    - BLOCK (zatrzymaj, nie handluj)
    """
    
    # Progi
    VIX_MAX = 30
    VIX_HIGH = 25
    ADX_CHAOS_THRESHOLD = 15
    CONFIDENCE_MIN = 0.4
    
    def __init__(self):
        self.horizon_detector = HorizonDetector()
    
    def decide(
        self,
        session: Dict,
        vix: Dict,
        sentiment: SentimentContext,
        mtf_analysis: Dict,
        indicators: Dict,
        current_price: float,
    ) -> DecisionResult:
        """
        Główna metoda decyzyjna.
        
        Args:
            session: Wynik z SessionAnalyzer.get_current_session()
            vix: Wynik z VIXCollector.get_current()
            sentiment: SentimentContext z SentimentAggregator
            mtf_analysis: Wynik z MultiTimeframeAnalyzer
            indicators: Dict z wskaźnikami (adx, rsi, vwap, pivots, atr)
            current_price: Aktualna cena
        
        Returns:
            DecisionResult
        """
        decision_path = []
        warnings = []
        
        # ========================================
        # KROK 1: CAN TRADE? (BLOKUJĄCY)
        # ========================================
        decision_path.append("Step 1: Checking if can trade")
        
        if not session.get('can_trade', False):
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=0.0,
                block_reason=BlockReason.SESSION_CLOSED,
                decision_path=decision_path + [f"BLOCKED: {session.get('recommendation', 'Session closed')}"],
            )
        
        vix_value = vix.get('value', 20)
        if vix_value > self.VIX_MAX:
            return DecisionResult(
                action=DecisionAction.STOP,
                confidence=0.0,
                block_reason=BlockReason.VIX_TOO_HIGH,
                decision_path=decision_path + [f"BLOCKED: VIX = {vix_value} > {self.VIX_MAX}"],
            )
        
        if vix_value > self.VIX_HIGH:
            warnings.append(f"VIX elevated ({vix_value}) - reduced position size recommended")
        
        decision_path.append(f"PASS: Session OK, VIX = {vix_value}")
        
        # ========================================
        # KROK 2: MARKET REGIME (BLOKUJĄCY dla chaos)
        # ========================================
        decision_path.append("Step 2: Checking market regime")
        
        adx = indicators.get('adx', {}).get('value', 20) if isinstance(indicators.get('adx'), dict) else indicators.get('adx', 20)
        volatility = indicators.get('atr', 0) / current_price if current_price > 0 else 0
        
        # Chaos = niski ADX + wysoka zmienność
        if adx < self.ADX_CHAOS_THRESHOLD and volatility > 0.025:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=0.0,
                block_reason=BlockReason.MARKET_CHAOS,
                decision_path=decision_path + [f"BLOCKED: Chaos (ADX={adx:.1f}, vol={volatility:.2%})"],
            )
        
        # Określ reżim
        if adx < 20:
            regime = "ranging"
        elif adx < 40:
            regime = "trending"
        else:
            regime = "strong_trend"
        
        decision_path.append(f"PASS: Regime = {regime} (ADX = {adx:.1f})")
        
        # ========================================
        # KROK 3: HIGHER TF BIAS (OGRANICZAJĄCY)
        # ========================================
        decision_path.append("Step 3: Checking MTF alignment")
        
        allowed_directions = self._get_allowed_directions(mtf_analysis)
        
        if not allowed_directions:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=0.0,
                block_reason=BlockReason.NO_CLEAR_DIRECTION,
                decision_path=decision_path + ["BLOCKED: No clear MTF direction"],
            )
        
        if mtf_analysis.get('conflict', False):
            warnings.append("MTF conflict detected - reduced confidence")
        
        decision_path.append(f"PASS: Allowed directions = {allowed_directions}")
        
        # ========================================
        # KROK 4: SENTIMENT GATE (OGRANICZAJĄCY)
        # ========================================
        decision_path.append("Step 4: Checking sentiment gate")
        
        position_modifier = sentiment.get_position_modifier()
        
        # Sprawdź czy sentiment blokuje któryś kierunek
        filtered_directions = []
        for direction in allowed_directions:
            if sentiment.allows_direction(direction):
                filtered_directions.append(direction)
            else:
                conflict = sentiment.get_conflict_severity(direction)
                if conflict == "severe":
                    decision_path.append(f"Sentiment BLOCKS {direction} (severe conflict)")
                else:
                    warnings.append(f"Sentiment warns against {direction} ({conflict} conflict)")
                    # Mild/moderate nie blokuje, ale zmniejsza size
                    filtered_directions.append(direction)
                    position_modifier *= 0.7
        
        if not filtered_directions:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=0.0,
                block_reason=BlockReason.SENTIMENT_CONFLICT,
                decision_path=decision_path + ["BLOCKED: All directions blocked by sentiment"],
            )
        
        # Sentiment regime modyfikuje position
        if sentiment.regime == SentimentRegime.PANIC:
            position_modifier *= 0.5
            warnings.append("Panic regime - 50% position reduction")
        
        decision_path.append(f"PASS: Filtered directions = {filtered_directions}, modifier = {position_modifier:.2f}")
        
        # ========================================
        # KROK 5: ENTRY CONDITIONS (REQUIRED + OPTIONAL)
        # ========================================
        decision_path.append("Step 5: Checking entry conditions")
        
        # Wybierz kierunek z najlepszymi warunkami
        best_direction, confirmations, optional_score = self._check_entry_conditions(
            filtered_directions, indicators, mtf_analysis, current_price
        )
        
        if best_direction is None:
            return DecisionResult(
                action=DecisionAction.HOLD,
                confidence=0.0,
                block_reason=BlockReason.CRITICAL_CONDITIONS_NOT_MET,
                decision_path=decision_path + ["BLOCKED: Critical conditions not met"],
            )
        
        decision_path.append(f"PASS: {best_direction} with {len(confirmations)} confirmations")
        
        # ========================================
        # KROK 6: DETECT HORIZON
        # ========================================
        decision_path.append("Step 6: Detecting horizon")
        
        horizon = self.horizon_detector.detect(
            volatility=volatility,
            catalyst_type="technical",  # TODO: detect from news
            trend_strength=mtf_analysis.get('trends', {}).get('1h', {}).get('strength', 0.5),
            adx=adx,
            sentiment_regime=sentiment.regime.value,
        )
        
        horizon_config = self.horizon_detector.get_config(horizon)
        
        decision_path.append(f"PASS: Horizon = {horizon.value}")
        
        # ========================================
        # KROK 7: CALCULATE SL/TP
        # ========================================
        decision_path.append("Step 7: Calculating SL/TP")
        
        atr = indicators.get('atr', current_price * 0.01)
        pivots = indicators.get('pivots', {})
        
        sl_multiplier = horizon_config.get_sl_multiplier(
            "high" if vix_value > self.VIX_HIGH else "normal"
        )
        rr_ratio = horizon_config.get_rr_ratio(
            mtf_analysis.get('trends', {}).get('1h', {}).get('strength', 0.5)
        )
        
        sl_distance = atr * sl_multiplier
        tp_distance = sl_distance * rr_ratio
        
        if best_direction == "LONG":
            # Structure-based SL: użyj pivot S1 jeśli bliżej
            structure_sl = pivots.get('S1', 0)
            if structure_sl > 0:
                structure_distance = current_price - structure_sl
                sl_distance = max(sl_distance, structure_distance * 1.01)  # 1% buffer
            
            stop_loss = current_price - sl_distance
            take_profit = current_price + tp_distance
        else:
            # SHORT
            structure_sl = pivots.get('R1', 0)
            if structure_sl > 0:
                structure_distance = structure_sl - current_price
                sl_distance = max(sl_distance, structure_distance * 1.01)
            
            stop_loss = current_price + sl_distance
            take_profit = current_price - tp_distance
        
        decision_path.append(f"CALCULATED: SL={stop_loss:.5f}, TP={take_profit:.5f}")
        
        # ========================================
        # FINALNA DECYZJA
        # ========================================
        
        # Oblicz confidence
        base_confidence = 0.5
        confidence = base_confidence + (optional_score * 0.3)
        
        # Modyfikuj przez MTF alignment
        alignment = mtf_analysis.get('alignment', 'mixed')
        if alignment == 'perfect_bullish' or alignment == 'perfect_bearish':
            confidence *= 1.2
        elif alignment == 'conflict':
            confidence *= 0.7
        
        confidence = min(1.0, confidence)
        
        return DecisionResult(
            action=DecisionAction[best_direction],
            confidence=confidence,
            horizon=horizon,
            entry_price=current_price,
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            position_modifier=position_modifier,
            confirmations=confirmations,
            warnings=warnings,
            decision_path=decision_path,
        )
    
    def _get_allowed_directions(self, mtf_analysis: Dict) -> List[str]:
        """Określa dozwolone kierunki na podstawie MTF."""
        trends = mtf_analysis.get('trends', {})
        
        # Policz bullish/bearish na wyższych TF
        bullish = 0
        bearish = 0
        
        for tf in ['4h', '1d']:
            trend = trends.get(tf, {})
            direction = trend.get('direction', 'sideways')
            strength = trend.get('strength', 0)
            
            if direction == 'up' and strength > 0.3:
                bullish += 1
            elif direction == 'down' and strength > 0.3:
                bearish += 1
        
        # Logika:
        # - Jeśli oba wyższe TF bullish → tylko LONG
        # - Jeśli oba bearish → tylko SHORT
        # - Jeśli mieszane → oba dozwolone (z ostrzeżeniem)
        
        if bullish == 2:
            return ["LONG"]
        elif bearish == 2:
            return ["SHORT"]
        elif bullish > bearish:
            return ["LONG", "SHORT"]  # Preferuj LONG
        elif bearish > bullish:
            return ["SHORT", "LONG"]  # Preferuj SHORT
        else:
            return ["LONG", "SHORT"]  # Oba OK
    
    def _check_entry_conditions(
        self,
        allowed_directions: List[str],
        indicators: Dict,
        mtf_analysis: Dict,
        current_price: float,
    ) -> Tuple[Optional[str], List[str], float]:
        """
        Sprawdza warunki wejścia dla każdego kierunku.
        
        Returns:
            (best_direction, confirmations, optional_score)
        """
        # CRITICAL CONDITIONS (wszystkie muszą być spełnione)
        CRITICAL = {
            "LONG": [
                ("vwap_ok", lambda: current_price > indicators.get('vwap', current_price)),
                ("trend_1h_ok", lambda: mtf_analysis.get('trends', {}).get('1h', {}).get('direction') != 'down'),
            ],
            "SHORT": [
                ("vwap_ok", lambda: current_price < indicators.get('vwap', current_price)),
                ("trend_1h_ok", lambda: mtf_analysis.get('trends', {}).get('1h', {}).get('direction') != 'up'),
            ],
        }
        
        # OPTIONAL CONDITIONS (bonus)
        OPTIONAL = {
            "LONG": [
                ("rsi_not_overbought", lambda: indicators.get('rsi', 50) < 70),
                ("adx_trend", lambda: (indicators.get('adx', {}).get('value', 20) if isinstance(indicators.get('adx'), dict) else indicators.get('adx', 20)) > 20),
                ("above_pivot_pp", lambda: current_price > indicators.get('pivots', {}).get('PP', 0)),
            ],
            "SHORT": [
                ("rsi_not_oversold", lambda: indicators.get('rsi', 50) > 30),
                ("adx_trend", lambda: (indicators.get('adx', {}).get('value', 20) if isinstance(indicators.get('adx'), dict) else indicators.get('adx', 20)) > 20),
                ("below_pivot_pp", lambda: current_price < indicators.get('pivots', {}).get('PP', float('inf'))),
            ],
        }
        
        best_direction = None
        best_score = -1
        best_confirmations = []
        
        for direction in allowed_directions:
            # Sprawdź critical
            critical_pass = True
            for name, check in CRITICAL.get(direction, []):
                try:
                    if not check():
                        critical_pass = False
                        break
                except:
                    critical_pass = False
                    break
            
            if not critical_pass:
                continue
            
            # Sprawdź optional
            confirmations = []
            optional_passed = 0
            for name, check in OPTIONAL.get(direction, []):
                try:
                    if check():
                        confirmations.append(name)
                        optional_passed += 1
                except:
                    pass
            
            optional_score = optional_passed / len(OPTIONAL.get(direction, [1]))
            
            if optional_score > best_score:
                best_score = optional_score
                best_direction = direction
                best_confirmations = confirmations
        
        return best_direction, best_confirmations, best_score


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from models.sentiment_context import SentimentAggregator, SentimentSource
    
    # Przygotuj dane testowe
    session = {
        "can_trade": True,
        "recommendation": "✅ OK - można handlować",
    }
    
    vix = {
        "value": 18.5,
        "regime": "normal",
    }
    
    # Sentiment
    agg = SentimentAggregator()
    agg.add_signal(SentimentSource.FOREX_NEWS, 0.4, 0.7)
    sentiment = agg.get_context()
    
    # MTF
    mtf_analysis = {
        "trends": {
            "1h": {"direction": "up", "strength": 0.6},
            "4h": {"direction": "up", "strength": 0.4},
            "1d": {"direction": "sideways", "strength": 0.2},
        },
        "alignment": "good_bullish",
        "conflict": False,
    }
    
    # Indicators
    indicators = {
        "rsi": 55,
        "adx": {"value": 28, "plus_di": 25, "minus_di": 18},
        "vwap": 4.330,
        "atr": 0.02,
        "pivots": {"PP": 4.340, "R1": 4.365, "S1": 4.315},
    }
    
    current_price = 4.350
    
    # Decyzja
    engine = DecisionEngine()
    result = engine.decide(
        session=session,
        vix=vix,
        sentiment=sentiment,
        mtf_analysis=mtf_analysis,
        indicators=indicators,
        current_price=current_price,
    )
    
    print("=" * 60)
    print("DECISION ENGINE RESULT")
    print("=" * 60)
    print(f"Action: {result.action.value}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Horizon: {result.horizon.value if result.horizon else 'N/A'}")
    
    if result.is_trade():
        print(f"\nTrade:")
        print(f"  Entry: {result.entry_price}")
        print(f"  SL: {result.stop_loss}")
        print(f"  TP: {result.take_profit}")
        print(f"  Position Modifier: {result.position_modifier:.2f}")
    
    print(f"\nConfirmations: {result.confirmations}")
    print(f"Warnings: {result.warnings}")
    
    print(f"\nDecision Path:")
    for step in result.decision_path:
        print(f"  → {step}")
