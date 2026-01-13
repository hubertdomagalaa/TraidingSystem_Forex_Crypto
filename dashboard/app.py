"""
Streamlit Dashboard dla Trading Decision System.
Uruchomienie: streamlit run dashboard/app.py
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Dodaj root projektu do ścieżki
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Page config
st.set_page_config(
    page_title="Trading Decision System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .signal-buy {
        color: #4CAF50;
        font-weight: bold;
    }
    .signal-sell {
        color: #F44336;
        font-weight: bold;
    }
    .signal-hold {
        color: #FF9800;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


def load_system():
    """Ładuje komponenty systemu."""
    try:
        from data.collectors import ForexCollector, CryptoCollector
        from social_tracking import FearGreedIndex
        from models.technical import IndicatorEngine
        from strategies import MeanReversionStrategy, MomentumSentimentStrategy
        from aggregator import SignalAggregator, ConflictResolver
        from output import JSONExporter
        
        return {
            'forex_collector': ForexCollector(),
            'crypto_collector': CryptoCollector(),
            'fear_greed': FearGreedIndex(),
            'indicator_engine': IndicatorEngine(),
            'mean_reversion': MeanReversionStrategy(),
            'momentum_sentiment': MomentumSentimentStrategy(),
            'aggregator': SignalAggregator(),
            'conflict_resolver': ConflictResolver(),
            'exporter': JSONExporter(),
        }
    except Exception as e:
        st.error(f"Błąd ładowania systemu: {e}")
        return None


def get_signal_color(action: str) -> str:
    """Zwraca kolor dla akcji."""
    colors = {
        'BUY': '🟢',
        'SELL': '🔴',
        'HOLD': '🟡',
    }
    return colors.get(action.upper(), '⚪')


def main():
    # Header
    st.markdown('<h1 class="main-header">📊 Trading Decision System</h1>', unsafe_allow_html=True)
    st.markdown("*System Wspomagania Decyzji Tradingowych - Forex & Crypto*")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Ustawienia")
        
        st.subheader("Kontekst Rynkowy")
        vix = st.slider("VIX (Zmienność)", 10, 50, 20, help="Wartość indeksu VIX")
        
        # Fear & Greed auto-fetch
        if st.button("🔄 Pobierz Fear & Greed"):
            with st.spinner("Pobieranie..."):
                try:
                    from social_tracking import FearGreedIndex
                    fng = FearGreedIndex()
                    result = fng.get_current()
                    st.session_state['fear_greed'] = result['value']
                    st.success(f"Pobrano: {result['value']} ({result['classification']})")
                except Exception as e:
                    st.error(f"Błąd: {e}")
        
        fear_greed = st.slider(
            "Fear & Greed Index", 
            0, 100, 
            st.session_state.get('fear_greed', 50),
            help="0=Extreme Fear, 100=Extreme Greed"
        )
        
        st.markdown("---")
        
        st.subheader("Filtrowanie Newsów")
        news_window = st.checkbox("Ważne newsy w ciągu 1h", value=False)
        
        st.markdown("---")
        
        st.subheader("💡 Interpretacja")
        st.markdown("""
        - **VIX > 25**: Wysoka zmienność
        - **VIX < 15**: Niska zmienność
        - **F&G < 25**: Extreme Fear (BUY?)
        - **F&G > 75**: Extreme Greed (SELL?)
        """)
    
    # Main content - Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Forex", "🪙 Crypto", "🎯 Sygnały", "📤 Export JSON"])
    
    # ============ TAB 1: FOREX ============
    with tab1:
        st.header("📈 Segment Forex")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("EUR/PLN")
            
            try:
                from data.collectors import ForexCollector
                collector = ForexCollector()
                
                price = collector.get_current_price("EUR/PLN")
                returns = collector.calculate_returns("EUR/PLN")
                
                if price:
                    st.metric(
                        label="Aktualna cena",
                        value=f"{price:.4f}",
                        delta=f"{returns.get('1d', 0):.2f}% (1d)" if returns else None
                    )
                else:
                    st.warning("Nie udało się pobrać ceny")
                
                # Wskaźniki techniczne
                st.markdown("**Wskaźniki techniczne:**")
                data = collector.get_historical_data("EUR/PLN", days=60)
                
                if data is not None:
                    from models.technical import IndicatorEngine
                    engine = IndicatorEngine()
                    data_with_indicators = engine.calculate_all(data)
                    
                    last = data_with_indicators.iloc[-1]
                    
                    ind_col1, ind_col2, ind_col3 = st.columns(3)
                    with ind_col1:
                        rsi = last.get('rsi', 0)
                        st.metric("RSI", f"{rsi:.1f}")
                    with ind_col2:
                        zscore = last.get('zscore', 0)
                        st.metric("Z-Score", f"{zscore:.2f}")
                    with ind_col3:
                        atr = last.get('atr', 0)
                        st.metric("ATR", f"{atr:.4f}")
                    
                    # Mean Reversion Signal
                    st.markdown("**Mean Reversion Strategy:**")
                    from strategies import MeanReversionStrategy
                    mr_strategy = MeanReversionStrategy()
                    mr_signal = mr_strategy.generate_signal(data['Close'], vix=vix, news_within_1h=news_window)
                    
                    signal_emoji = get_signal_color('BUY' if mr_signal['signal'] > 0.3 else 'SELL' if mr_signal['signal'] < -0.3 else 'HOLD')
                    st.markdown(f"{signal_emoji} Signal: **{mr_signal['signal']:.4f}** | Confidence: {mr_signal['confidence']:.2f}")
                    st.caption(mr_signal['reason'])
            
            except Exception as e:
                st.error(f"Błąd: {e}")
        
        with col2:
            st.subheader("EUR/USD")
            
            try:
                price = collector.get_current_price("EUR/USD")
                returns = collector.calculate_returns("EUR/USD")
                
                if price:
                    st.metric(
                        label="Aktualna cena",
                        value=f"{price:.4f}",
                        delta=f"{returns.get('1d', 0):.2f}% (1d)" if returns else None
                    )
            except:
                st.info("Dane niedostępne")
    
    # ============ TAB 2: CRYPTO ============
    with tab2:
        st.header("🪙 Segment Crypto")
        
        # Fear & Greed display
        st.subheader("📊 Fear & Greed Index")
        
        fng_col1, fng_col2, fng_col3 = st.columns(3)
        with fng_col1:
            st.metric("Wartość", fear_greed)
        with fng_col2:
            if fear_greed < 25:
                classification = "Extreme Fear"
            elif fear_greed < 45:
                classification = "Fear"
            elif fear_greed < 55:
                classification = "Neutral"
            elif fear_greed < 75:
                classification = "Greed"
            else:
                classification = "Extreme Greed"
            st.metric("Klasyfikacja", classification)
        with fng_col3:
            if fear_greed < 25:
                signal = "🟢 BUY Signal"
            elif fear_greed > 75:
                signal = "🔴 SELL Signal"
            else:
                signal = "⚪ Neutral"
            st.metric("Sygnał", signal)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("BTC/USDT")
            try:
                from data.collectors import CryptoCollector
                crypto_collector = CryptoCollector()
                
                btc_price = crypto_collector.get_current_price("BTC/USDT")
                btc_stats = crypto_collector.get_24h_stats("BTC/USDT")
                
                if btc_price:
                    st.metric(
                        label="Aktualna cena",
                        value=f"${btc_price:,.2f}",
                        delta=f"{btc_stats.get('change_24h', 0):.2f}% (24h)" if btc_stats else None
                    )
            except Exception as e:
                st.warning(f"Dane BTC niedostępne: {e}")
        
        with col2:
            st.subheader("ETH/USDT")
            try:
                eth_price = crypto_collector.get_current_price("ETH/USDT")
                eth_stats = crypto_collector.get_24h_stats("ETH/USDT")
                
                if eth_price:
                    st.metric(
                        label="Aktualna cena",
                        value=f"${eth_price:,.2f}",
                        delta=f"{eth_stats.get('change_24h', 0):.2f}% (24h)" if eth_stats else None
                    )
            except Exception as e:
                st.warning(f"Dane ETH niedostępne: {e}")
    
    # ============ TAB 3: SIGNALS ============
    with tab3:
        st.header("🎯 Zagregowane Sygnały")
        
        st.info("💡 Wprowadź newsy do analizy sentiment lub kliknij 'Analizuj bez newsów'")
        
        # News input
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📰 Newsy Forex (EN)")
            forex_news = st.text_area(
                "Wklej newsy finansowe (jeden na linię):",
                height=150,
                placeholder="ECB signals higher rates...\nEuro strengthens...",
                key="forex_news"
            )
        
        with col2:
            st.subheader("💬 Newsy Crypto (EN)")
            crypto_news = st.text_area(
                "Wklej newsy crypto (jeden na linię):",
                height=150,
                placeholder="Bitcoin breaks resistance...\nBullish momentum...",
                key="crypto_news"
            )
        
        if st.button("🚀 Analizuj Sygnały", type="primary"):
            with st.spinner("Analizowanie..."):
                st.markdown("---")
                st.subheader("📊 Wyniki Analizy")
                
                # Tu dodaj logikę analizy
                st.info("Implementacja w toku - użyj main.py do pełnej analizy")
    
    # ============ TAB 4: EXPORT ============
    with tab4:
        st.header("📤 Export JSON dla AntiGravity")
        
        st.markdown("""
        ### Jak używać:
        1. Kliknij **Generuj JSON**
        2. Skopiuj wygenerowany JSON
        3. Wklej do **Google AntiGravity** (Claude)
        4. Otrzymaj finalną analizę i rekomendację
        """)
        
        if st.button("📋 Generuj JSON", type="primary"):
            try:
                from output import JSONExporter
                exporter = JSONExporter()
                
                # Przykładowe dane (w produkcji - pobrane z systemu)
                forex_signals = {
                    'action': 'HOLD',
                    'score': 0.15,
                    'confidence': 0.15,
                    'strength': 15.0,
                    'details': []
                }
                
                crypto_signals = {
                    'action': 'HOLD',
                    'score': 0.0,
                    'confidence': 0.0,
                    'strength': 0.0,
                    'details': []
                }
                
                market_context = {
                    'vix': vix,
                    'fear_greed': fear_greed,
                    'regime': 'normal' if vix < 25 else 'high_volatility',
                    'trading_allowed': vix < 30,
                }
                
                json_output = exporter.export_for_llm(
                    forex_signals, 
                    crypto_signals, 
                    market_context
                )
                
                st.code(json_output, language="markdown")
                
                st.success("✅ JSON wygenerowany! Skopiuj powyższy tekst i wklej do AntiGravity.")
                
            except Exception as e:
                st.error(f"Błąd generowania JSON: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"*Trading Decision System v1.0 | "
        f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"⚠️ Not financial advice*"
    )


if __name__ == "__main__":
    main()
