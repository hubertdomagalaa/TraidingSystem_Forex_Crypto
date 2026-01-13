"""
Telegram Bot do alertów tradingowych.
Wysyła powiadomienia o sygnałach przez Telegram.
"""
import os
import asyncio
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Sprawdź czy telegram dostępny
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot nie jest zainstalowany. Alerty Telegram niedostępne.")


class TelegramAlerts:
    """
    Wysyła alerty o sygnałach tradingowych przez Telegram.
    
    Setup:
    1. Utwórz bota przez @BotFather na Telegram
    2. Zapisz token w .env jako TELEGRAM_BOT_TOKEN
    3. Wyślij /start do swojego bota
    4. Pobierz chat_id i zapisz w .env jako TELEGRAM_CHAT_ID
    
    Jak znaleźć chat_id:
    - Wyślij wiadomość do bota
    - Odwiedź: https://api.telegram.org/bot<TOKEN>/getUpdates
    - Znajdź "chat":{"id": TWÓJ_CHAT_ID}
    """
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        self.bot = None
        self.enabled = False
        
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram niedostępny - brak biblioteki")
            return
        
        if self.token and self.chat_id:
            try:
                self.bot = Bot(self.token)
                self.enabled = True
                logger.info("Telegram alerts zainicjalizowany")
            except Exception as e:
                logger.error(f"Błąd inicjalizacji Telegram bota: {e}")
        else:
            logger.warning("Telegram: brak TELEGRAM_BOT_TOKEN lub TELEGRAM_CHAT_ID w .env")
    
    async def send_message_async(self, message: str) -> bool:
        """
        Wysyła wiadomość asynchronicznie.
        
        Args:
            message: Tekst wiadomości (obsługuje Markdown)
        
        Returns:
            True jeśli wysłano, False w przypadku błędu
        """
        if not self.enabled or not self.bot:
            logger.warning("Telegram nie jest włączony")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info("Wysłano wiadomość Telegram")
            return True
        
        except TelegramError as e:
            logger.error(f"Błąd wysyłania Telegram: {e}")
            return False
        
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd Telegram: {e}")
            return False
    
    def send_message(self, message: str) -> bool:
        """Synchroniczna wersja send_message."""
        return asyncio.run(self.send_message_async(message))
    
    async def send_signal_async(self, signal_data: Dict) -> bool:
        """
        Wysyła sformatowany alert o sygnale.
        
        Args:
            signal_data: Słownik z danymi sygnału
        """
        message = self._format_signal_message(signal_data)
        return await self.send_message_async(message)
    
    def send_signal(self, signal_data: Dict) -> bool:
        """Synchroniczna wersja send_signal."""
        return asyncio.run(self.send_signal_async(signal_data))
    
    def _format_signal_message(self, data: Dict) -> str:
        """
        Formatuje sygnał do czytelnej wiadomości.
        """
        action = data.get('action', 'HOLD')
        
        # Emoji dla akcji
        if action == 'BUY':
            action_emoji = '🟢'
        elif action == 'SELL':
            action_emoji = '🔴'
        else:
            action_emoji = '🟡'
        
        # Podstawowa wiadomość
        message = f"""
🚨 *NOWY SYGNAŁ TRADINGOWY*

{action_emoji} *Akcja:* {action}
📊 *Asset:* {data.get('asset', 'N/A')}
📈 *Score:* {data.get('score', 0):.4f}
💪 *Siła:* {data.get('strength', 0):.1f}%
🎯 *Confidence:* {data.get('confidence', 0):.1%}

"""

        # Dodaj szczegóły sygnałów jeśli dostępne
        details = data.get('details', [])
        if details:
            message += "*Źródła sygnałów:*\n"
            for d in details[:5]:  # Max 5 źródeł
                source = d.get('source', 'Unknown')
                signal = d.get('signal', 0)
                emoji = "🟢" if signal > 0 else "🔴" if signal < 0 else "⚪"
                message += f"  {emoji} {source}: {signal:.2f}\n"
            message += "\n"
        
        # Dodaj poziomy jeśli dostępne
        if 'stop_loss' in data:
            message += f"🛑 *Stop Loss:* {data['stop_loss']}\n"
        if 'take_profit' in data:
            message += f"🎯 *Take Profit:* {data['take_profit']}\n"
        
        # Dodaj kontekst rynkowy
        if 'market_context' in data:
            ctx = data['market_context']
            message += f"\n*Kontekst:*\n"
            message += f"  • VIX: {ctx.get('vix', 'N/A')}\n"
            message += f"  • Fear & Greed: {ctx.get('fear_greed', 'N/A')}\n"
            message += f"  • Regime: {ctx.get('regime', 'normal')}\n"
        
        # Timestamp
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Disclaimer
        message += "\n\n_⚠️ Nie jest poradą inwestycyjną_"
        
        return message
    
    def send_daily_summary(self, summary: Dict) -> bool:
        """
        Wysyła dzienne podsumowanie.
        
        Args:
            summary: Słownik z podsumowaniem dnia
        """
        message = f"""
📊 *DZIENNE PODSUMOWANIE*
_{datetime.now().strftime('%Y-%m-%d')}_

*Forex:*
  • EUR/PLN: {summary.get('eurpln_action', 'N/A')}
  • Score: {summary.get('eurpln_score', 0):.4f}

*Crypto:*
  • BTC: {summary.get('btc_action', 'N/A')}
  • Fear & Greed: {summary.get('fear_greed', 50)}

*Statystyki:*
  • Sygnały dzisiaj: {summary.get('signals_count', 0)}
  • VIX: {summary.get('vix', 'N/A')}
  • Regime: {summary.get('regime', 'normal')}

_Używaj AntiGravity dla pełnej analizy_
"""
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """
        Testuje połączenie z Telegram.
        
        Returns:
            True jeśli połączenie działa
        """
        if not self.enabled:
            return False
        
        try:
            message = f"🔔 *Test połączenia*\nTrading System działa!\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            return self.send_message(message)
        except:
            return False


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Załaduj .env
    from dotenv import load_dotenv
    load_dotenv()
    
    alerts = TelegramAlerts()
    
    if not alerts.enabled:
        print("❌ Telegram nie jest skonfigurowany")
        print("Ustaw TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_ID w .env")
    else:
        print("✅ Telegram skonfigurowany")
        
        # Test połączenia
        if alerts.test_connection():
            print("✅ Test wiadomości wysłany!")
        else:
            print("❌ Błąd wysyłania")
        
        # Przykładowy sygnał
        test_signal = {
            'action': 'BUY',
            'asset': 'EUR/PLN',
            'score': 0.65,
            'strength': 65.0,
            'confidence': 0.75,
            'details': [
                {'source': 'finbert', 'signal': 0.8},
                {'source': 'mean_reversion', 'signal': 0.5},
            ],
            'stop_loss': '4.3100',
            'take_profit': '4.3500',
            'market_context': {
                'vix': 18,
                'fear_greed': 42,
                'regime': 'normal',
            }
        }
        
        # alerts.send_signal(test_signal)
