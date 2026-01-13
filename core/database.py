"""
Database module for signal persistence.
Uses SQLite for simplicity.
"""
from datetime import datetime
from typing import List, Optional
import logging

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class Signal(Base):
    """Stored trading signal."""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset = Column(String(20), nullable=False)
    market = Column(String(10), nullable=False)  # forex, crypto
    direction = Column(String(10), nullable=False)  # LONG, SHORT, HOLD
    confidence = Column(Float, default=0.0)
    entry = Column(Float, default=0.0)
    stop_loss = Column(Float, default=0.0)
    take_profit = Column(Float, default=0.0)
    risk_reward = Column(Float, default=0.0)
    sentiment = Column(Float, default=0.0)
    vix = Column(Float, default=0.0)
    session_name = Column(String(50), nullable=True)
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'asset': self.asset,
            'market': self.market,
            'direction': self.direction,
            'confidence': self.confidence,
            'entry': self.entry,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_reward': self.risk_reward,
            'sentiment': self.sentiment,
            'vix': self.vix,
            'session': self.session_name,
            'confirmed': self.confirmed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SignalRepository:
    """Repository for storing and retrieving signals."""
    
    def __init__(self, db_path: str = 'sqlite:///trading_signals.db'):
        self.engine = create_engine(db_path, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Signal database initialized: {db_path}")
    
    def save(self, signal_data: dict) -> int:
        """Save a new signal to database."""
        session = self.Session()
        try:
            signal = Signal(
                asset=signal_data.get('asset', ''),
                market=signal_data.get('market', 'forex'),
                direction=signal_data.get('direction', 'HOLD'),
                confidence=signal_data.get('confidence', 0.0),
                entry=signal_data.get('entry', 0.0),
                stop_loss=signal_data.get('stop_loss', 0.0),
                take_profit=signal_data.get('take_profit', 0.0),
                risk_reward=signal_data.get('risk_reward', 0.0),
                sentiment=signal_data.get('sentiment', 0.0),
                vix=signal_data.get('vix', 0.0),
                session_name=signal_data.get('session', ''),
                confirmed=signal_data.get('confirmed', False),
            )
            session.add(signal)
            session.commit()
            signal_id = signal.id
            logger.info(f"Signal saved: ID={signal_id}, {signal.asset} {signal.direction}")
            return signal_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving signal: {e}")
            raise
        finally:
            session.close()
    
    def get_history(self, asset: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Get signal history."""
        session = self.Session()
        try:
            query = session.query(Signal).order_by(Signal.created_at.desc())
            if asset:
                query = query.filter(Signal.asset == asset)
            signals = query.limit(limit).all()
            return [s.to_dict() for s in signals]
        finally:
            session.close()
    
    def get_stats(self, days: int = 30) -> dict:
        """Get signal statistics for the last N days."""
        session = self.Session()
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            signals = session.query(Signal).filter(Signal.created_at >= cutoff).all()
            
            if not signals:
                return {'total': 0, 'long': 0, 'short': 0, 'hold': 0}
            
            return {
                'total': len(signals),
                'long': len([s for s in signals if s.direction == 'LONG']),
                'short': len([s for s in signals if s.direction == 'SHORT']),
                'hold': len([s for s in signals if s.direction == 'HOLD']),
                'avg_confidence': sum(s.confidence for s in signals) / len(signals),
                'confirmed_count': len([s for s in signals if s.confirmed]),
            }
        finally:
            session.close()


# Singleton instance
_repo: Optional[SignalRepository] = None


def get_signal_repository() -> SignalRepository:
    """Get or create SignalRepository singleton."""
    global _repo
    if _repo is None:
        _repo = SignalRepository()
    return _repo


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    repo = SignalRepository()
    
    # Test save
    test_signal = {
        'asset': 'EUR/PLN',
        'market': 'forex',
        'direction': 'LONG',
        'confidence': 75.5,
        'entry': 4.35,
        'stop_loss': 4.32,
        'take_profit': 4.42,
        'risk_reward': 2.3,
        'sentiment': 0.45,
        'vix': 18.5,
        'session': 'LONDON',
        'confirmed': True,
    }
    
    signal_id = repo.save(test_signal)
    print(f"Saved signal ID: {signal_id}")
    
    # Test history
    history = repo.get_history(limit=5)
    print(f"\nRecent signals: {len(history)}")
    for h in history:
        print(f"  {h['created_at']}: {h['asset']} {h['direction']} ({h['confidence']:.1f}%)")
    
    # Test stats
    stats = repo.get_stats()
    print(f"\nStats: {stats}")
