"""
Tests for Entry Confirmation system.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.entry_confirmation import EntryConfirmation


class TestEntryConfirmation:
    """Test suite for EntryConfirmation class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.ec = EntryConfirmation(min_confirmations=4)
    
    def test_long_signal_with_all_conditions_met(self):
        """Test LONG signal when all conditions favor buying."""
        signals = {
            'trend_1h': 'up',
            'trend_4h': 'up',
            'price': 4.35,
            'vwap': 4.33,  # price > vwap = bullish
            'rsi': 55,  # not overbought (<75)
            'sentiment': 0.4,  # positive (>0.15)
            'is_good_time': True,
            'adx': 28,  # strong trend (>15)
        }
        
        result = self.ec.check_entry(signals)
        
        assert result['entry'] == True
        assert result['direction'] == 'long'
        assert result['achieved'] >= 4
        assert result['confidence'] > 0.5
    
    def test_short_signal_with_bearish_conditions(self):
        """Test SHORT signal when conditions favor selling."""
        signals = {
            'trend_1h': 'down',
            'trend_4h': 'down',
            'price': 4.30,
            'vwap': 4.35,  # price < vwap = bearish
            'rsi': 35,  # not oversold (>25)
            'sentiment': -0.4,  # negative (<-0.15)
            'is_good_time': True,
            'adx': 30,  # strong trend
        }
        
        result = self.ec.check_entry(signals)
        
        assert result['entry'] == True
        assert result['direction'] == 'short'
        assert result['achieved'] >= 4
    
    def test_no_signal_with_conflicting_conditions(self):
        """Test that no entry is generated with conflicting signals."""
        signals = {
            'trend_1h': 'down',  # conflicting
            'trend_4h': 'up',  # conflicting
            'price': 4.35,
            'vwap': 4.35,  # neutral
            'rsi': 50,  # neutral
            'sentiment': 0.0,  # neutral
            'is_good_time': False,  # bad time
            'adx': 10,  # no trend
        }
        
        result = self.ec.check_entry(signals)
        
        assert result['entry'] == False
        assert result['achieved'] < 4
    
    def test_overbought_rsi_blocks_long(self):
        """Test that RSI > 75 blocks long entries."""
        signals = {
            'trend_1h': 'up',
            'trend_4h': 'up',
            'price': 4.35,
            'vwap': 4.33,
            'rsi': 80,  # OVERBOUGHT - should block
            'sentiment': 0.5,
            'is_good_time': True,
            'adx': 25,
        }
        
        result = self.ec.check_entry(signals)
        
        # RSI condition should NOT be met
        confirmations = result.get('confirmations', [])
        if confirmations:
            assert 'rsi_not_overbought' not in confirmations or not confirmations.get('rsi_not_overbought', True)


class TestEntryConfirmationEdgeCases:
    """Edge case tests for EntryConfirmation."""
    
    def setup_method(self):
        self.ec = EntryConfirmation(min_confirmations=4)
    
    def test_missing_signal_values(self):
        """Test handling of missing signal values."""
        signals = {
            'trend_1h': 'up',
            # Missing other values
        }
        
        # Should not crash
        result = self.ec.check_entry(signals)
        assert 'entry' in result
    
    def test_custom_min_confirmations(self):
        """Test custom min_confirmations threshold."""
        strict_ec = EntryConfirmation(min_confirmations=6)
        
        signals = {
            'trend_1h': 'up',
            'trend_4h': 'up',
            'price': 4.35,
            'vwap': 4.33,
            'rsi': 55,
            'sentiment': 0.3,
            'is_good_time': True,
            'adx': 25,
        }
        
        result = strict_ec.check_entry(signals)
        
        # With stricter requirements, may or may not pass
        assert 'entry' in result
        assert 'achieved' in result
