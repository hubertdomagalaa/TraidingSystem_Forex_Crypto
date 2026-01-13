"""
Tests for Stop Loss Calculator.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from risk_management import StopLossCalculator


class TestStopLossCalculator:
    """Test suite for StopLossCalculator class."""
    
    def setup_method(self):
        self.calc = StopLossCalculator()
    
    def test_atr_based_long_position(self):
        """Test ATR-based stop loss for LONG position."""
        result = self.calc.atr_based(
            entry_price=100.0,
            atr=2.0,
            direction='long',
            sl_multiplier=1.5,
            tp_multiplier=3.0
        )
        
        # For LONG: SL = entry - (ATR * multiplier)
        expected_sl = 100.0 - (2.0 * 1.5)  # 97.0
        expected_tp = 100.0 + (2.0 * 3.0)  # 106.0
        
        assert result['stop_loss'] == pytest.approx(expected_sl, abs=0.01)
        assert result['take_profit'] == pytest.approx(expected_tp, abs=0.01)
        assert result['risk_reward'] == pytest.approx(2.0, abs=0.1)
    
    def test_atr_based_short_position(self):
        """Test ATR-based stop loss for SHORT position."""
        result = self.calc.atr_based(
            entry_price=100.0,
            atr=2.0,
            direction='short',
            sl_multiplier=1.5,
            tp_multiplier=3.0
        )
        
        # For SHORT: SL = entry + (ATR * multiplier)
        expected_sl = 100.0 + (2.0 * 1.5)  # 103.0
        expected_tp = 100.0 - (2.0 * 3.0)  # 94.0
        
        assert result['stop_loss'] == pytest.approx(expected_sl, abs=0.01)
        assert result['take_profit'] == pytest.approx(expected_tp, abs=0.01)
    
    def test_risk_reward_calculation(self):
        """Test risk/reward ratio calculation."""
        result = self.calc.atr_based(
            entry_price=50.0,
            atr=1.0,
            direction='long',
            sl_multiplier=1.0,  # Risk = 1 ATR
            tp_multiplier=2.0   # Reward = 2 ATR
        )
        
        # R:R should be 2:1
        assert result['risk_reward'] == pytest.approx(2.0, abs=0.1)
    
    def test_forex_typical_values(self):
        """Test with typical Forex values (EUR/PLN)."""
        result = self.calc.atr_based(
            entry_price=4.35,
            atr=0.02,  # Typical ATR for EUR/PLN
            direction='long',
            sl_multiplier=1.2,
            tp_multiplier=2.4
        )
        
        assert result['stop_loss'] < result['entry']
        assert result['take_profit'] > result['entry']
        assert result['stop_loss'] == pytest.approx(4.326, abs=0.001)
        assert result['take_profit'] == pytest.approx(4.398, abs=0.001)


class TestStopLossEdgeCases:
    """Edge case tests for StopLossCalculator."""
    
    def setup_method(self):
        self.calc = StopLossCalculator()
    
    def test_zero_atr(self):
        """Test handling of zero ATR (should still work)."""
        result = self.calc.atr_based(
            entry_price=100.0,
            atr=0.0,
            direction='long',
            sl_multiplier=1.5,
            tp_multiplier=3.0
        )
        
        # With zero ATR, SL/TP should equal entry
        assert result['stop_loss'] == result['entry']
        assert result['take_profit'] == result['entry']
    
    def test_high_volatility_crypto(self):
        """Test with high volatility crypto values."""
        result = self.calc.atr_based(
            entry_price=45000.0,  # BTC
            atr=1500.0,  # High ATR
            direction='long',
            sl_multiplier=1.5,
            tp_multiplier=3.0
        )
        
        expected_sl = 45000.0 - (1500.0 * 1.5)  # 42750
        expected_tp = 45000.0 + (1500.0 * 3.0)  # 49500
        
        assert result['stop_loss'] == pytest.approx(expected_sl, abs=1.0)
        assert result['take_profit'] == pytest.approx(expected_tp, abs=1.0)
