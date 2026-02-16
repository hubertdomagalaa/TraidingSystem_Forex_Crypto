"""
Regression tests for DrawdownMonitor runtime behavior.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from risk_management.drawdown_monitor import DrawdownMonitor


class TestDrawdownMonitor:
    def test_can_trade_and_get_status_do_not_recurse(self):
        monitor = DrawdownMonitor(initial_equity=10000)

        # Should not raise recursion errors.
        assert monitor.can_trade() is True
        status = monitor.get_status()

        assert isinstance(status, dict)
        assert status["can_trade"] is True
        assert status["blocked"] is False

    def test_block_uses_timedelta_and_expires_cleanly(self):
        monitor = DrawdownMonitor(initial_equity=10000, cooldown_hours=1)
        monitor._block_trading("test block", hours=1)  # internal helper used intentionally

        assert monitor.block_until is not None
        assert monitor.block_until > datetime.now()

        # Simulate expired cooldown and ensure monitor unlocks.
        monitor.block_until = datetime.now() - timedelta(minutes=1)
        assert monitor.can_trade() is True
        assert monitor.trading_blocked is False
