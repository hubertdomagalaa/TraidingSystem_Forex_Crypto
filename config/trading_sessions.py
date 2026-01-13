"""
Sesje handlowe - optymalne godziny dla Forex i Crypto.
"""
from datetime import time, datetime
from typing import Dict, Tuple, List
from enum import Enum


class TradingSession(Enum):
    """Sesje handlowe."""
    ASIAN = "asian"
    LONDON = "london"
    NEW_YORK = "new_york"
    LONDON_NY_OVERLAP = "london_ny_overlap"


# ===== SESJE FOREX (CET / Warsaw Time) =====
FOREX_SESSIONS = {
    "asian": {
        "name": "Azja (Tokyo/Sydney)",
        "start": time(0, 0),
        "end": time(8, 0),
        "volatility": "low",
        "recommended": False,
        "pairs": ["USD/JPY", "AUD/USD"],
    },
    "london": {
        "name": "Londyn",
        "start": time(8, 0),
        "end": time(17, 0),
        "volatility": "high",
        "recommended": True,
        "pairs": ["EUR/USD", "GBP/USD", "EUR/PLN"],
    },
    "new_york": {
        "name": "Nowy Jork",
        "start": time(14, 0),
        "end": time(22, 0),
        "volatility": "high",
        "recommended": True,
        "pairs": ["EUR/USD", "USD/PLN"],
    },
    "london_ny_overlap": {
        "name": "🔥 BEST: London-NY Overlap",
        "start": time(14, 0),
        "end": time(17, 0),
        "volatility": "very_high",
        "recommended": True,  # NAJLEPSZY CZAS!
        "pairs": ["EUR/USD", "GBP/USD", "EUR/PLN", "USD/PLN"],
    },
}


# ===== SESJE CRYPTO (24/7 ale są lepsze godziny) =====
CRYPTO_SESSIONS = {
    "us_prime": {
        "name": "US Prime Time",
        "start": time(14, 0),
        "end": time(22, 0),
        "volatility": "high",
        "recommended": True,
    },
    "asia_prime": {
        "name": "Asia Prime Time",
        "start": time(0, 0),
        "end": time(8, 0),
        "volatility": "medium",
        "recommended": True,  # Dobre dla altcoinów
    },
    "europe": {
        "name": "Europe Hours",
        "start": time(8, 0),
        "end": time(17, 0),
        "volatility": "medium",
        "recommended": True,
    },
}


# ===== NAJLEPSZE DNI TYGODNIA =====
BEST_TRADING_DAYS = {
    "forex": {
        "best": ["tuesday", "wednesday", "thursday"],
        "good": ["monday", "friday"],
        "avoid": [],  # Poniedziałek rano i piątek po 16:00
    },
    "crypto": {
        "best": ["monday", "tuesday", "wednesday", "thursday"],
        "good": ["sunday", "friday"],
        "avoid": ["saturday"],  # Najniższa płynność
    },
}


# ===== CZEGO UNIKAĆ =====
AVOID_TRADING = {
    "forex": {
        "monday_first_hour": True,       # Luki weekendowe
        "friday_after_16": True,         # Przed weekendem
        "around_major_news_minutes": 30, # 30 min przed/po news
        "christmas_period": True,        # 20-31 grudnia
        "bank_holidays": True,           # Święta bankowe
    },
    "crypto": {
        "low_volume_weekends": True,     # Niedzielna noc / sobota
        "around_major_news_minutes": 15, # 15 min (crypto szybziej reaguje)
    },
}


class SessionAnalyzer:
    """
    Analizuje czy aktualny czas jest optymalny do handlu.
    """
    
    def __init__(self):
        pass
    
    def get_current_session(self, market: str = "forex") -> Dict:
        """
        Sprawdza aktualną sesję handlową.
        
        Returns:
            Dict z informacją o sesji i rekomendacją
        """
        now = datetime.now().time()
        weekday = datetime.now().strftime("%A").lower()
        
        sessions = FOREX_SESSIONS if market == "forex" else CRYPTO_SESSIONS
        
        active_sessions = []
        
        for session_id, session in sessions.items():
            if self._time_in_range(now, session["start"], session["end"]):
                active_sessions.append({
                    "id": session_id,
                    "name": session["name"],
                    "volatility": session["volatility"],
                    "recommended": session["recommended"],
                })
        
        # Sprawdź czy najlepsza sesja
        is_best_session = any(s["id"] == "london_ny_overlap" for s in active_sessions)
        
        # Sprawdź dzień
        day_rating = self._get_day_rating(weekday, market)
        
        # Sprawdź czy unikać
        should_avoid = self._check_avoid(now, weekday, market)
        
        return {
            "market": market,
            "current_time": now.strftime("%H:%M"),
            "weekday": weekday,
            "active_sessions": active_sessions,
            "is_best_session": is_best_session,
            "day_rating": day_rating,
            "should_avoid": should_avoid,
            "can_trade": len(active_sessions) > 0 and not should_avoid["avoid"],
            "recommendation": self._get_recommendation(active_sessions, day_rating, should_avoid),
        }
    
    def _time_in_range(self, now: time, start: time, end: time) -> bool:
        """Sprawdza czy czas jest w zakresie."""
        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end
    
    def _get_day_rating(self, weekday: str, market: str) -> str:
        """Ocena dnia tygodnia."""
        days = BEST_TRADING_DAYS.get(market, {})
        
        if weekday in days.get("best", []):
            return "best"
        elif weekday in days.get("good", []):
            return "good"
        elif weekday in days.get("avoid", []):
            return "avoid"
        else:
            return "neutral"
    
    def _check_avoid(self, now: time, weekday: str, market: str) -> Dict:
        """Sprawdza czy należy unikać tradingu."""
        avoid_rules = AVOID_TRADING.get(market, {})
        reasons = []
        
        # Poniedziałek rano
        if weekday == "monday" and now < time(9, 0) and avoid_rules.get("monday_first_hour"):
            reasons.append("Poniedziałek rano - możliwe luki weekendowe")
        
        # Piątek po 16
        if weekday == "friday" and now > time(16, 0) and avoid_rules.get("friday_after_16"):
            reasons.append("Piątek po 16:00 - zmniejszona płynność przed weekendem")
        
        return {
            "avoid": len(reasons) > 0,
            "reasons": reasons,
        }
    
    def _get_recommendation(self, sessions: List, day_rating: str, avoid: Dict) -> str:
        """Generuje rekomendację."""
        if avoid["avoid"]:
            return f"⚠️ UNIKAJ: {avoid['reasons'][0]}"
        
        if not sessions:
            return "😴 Poza godzinami handlowymi"
        
        best_session = any(s.get("id") == "london_ny_overlap" for s in sessions)
        
        if best_session and day_rating == "best":
            return "🔥 NAJLEPSZY CZAS! London-NY overlap + dobry dzień"
        elif best_session:
            return "✅ Bardzo dobry czas - London-NY overlap"
        elif day_rating == "best":
            return "✅ Dobry czas - optymalny dzień tygodnia"
        else:
            return "🟡 OK - można handlować"
    
    def is_good_time_to_trade(self, market: str = "forex") -> bool:
        """Prosta odpowiedź: czy teraz handlować?"""
        status = self.get_current_session(market)
        return status["can_trade"] and status["day_rating"] in ["best", "good", "neutral"]


# Przykład użycia
if __name__ == "__main__":
    analyzer = SessionAnalyzer()
    
    print("=" * 50)
    print("FOREX Session Analysis")
    print("=" * 50)
    forex_status = analyzer.get_current_session("forex")
    print(f"Time: {forex_status['current_time']} ({forex_status['weekday']})")
    print(f"Active sessions: {[s['name'] for s in forex_status['active_sessions']]}")
    print(f"Day rating: {forex_status['day_rating']}")
    print(f"Can trade: {forex_status['can_trade']}")
    print(f"Recommendation: {forex_status['recommendation']}")
    
    print("\n" + "=" * 50)
    print("CRYPTO Session Analysis")
    print("=" * 50)
    crypto_status = analyzer.get_current_session("crypto")
    print(f"Time: {crypto_status['current_time']} ({crypto_status['weekday']})")
    print(f"Active sessions: {[s['name'] for s in crypto_status['active_sessions']]}")
    print(f"Can trade: {crypto_status['can_trade']}")
    print(f"Recommendation: {crypto_status['recommendation']}")
