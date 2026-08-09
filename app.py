import streamlit as st
import streamlit.components.v1 as components
import urllib.request
import urllib.parse
import json
import base64
from datetime import datetime
import pandas as pd
from streamlit_searchbox import st_searchbox

# 페이지 기본 설정
st.set_page_config(
    page_title="TAURUS LAB",
    page_icon="⚡",
    layout="wide"
)

# ⚡ [핵심] 로고 이미지를 메모리에 단 1회만 인코딩하여 저장
@st.cache_data(show_spinner=False)
def get_cached_logo_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
            ext = path.split('.')[-1].lower()
            mime_type = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return ""

# 🎨 다크 테마 인라인 CSS (렌더링 차단 방지)
st.markdown("""<style>
.stApp { background-color: #0B0E14 !important; color: #E0E0E0 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
div[data-testid="stMetric"] {
    background-color: #121824 !important;
    border: 1px solid #1E293B !important;
    padding: 12px !important;
    border-radius: 8px !important;
    min-height: 85px !important;
}
div[data-testid="stMetric"] label { color: #94A3B8 !important; font-size: 11px !important; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #F8FAFC !important; font-size: 16px !important; font-weight: 800 !important; }
</style>""", unsafe_allow_html=True)

class QuantEngine:
    # ⚡ 타임아웃을 0.8초로 제한하여 네트워크 지연 즉시 차단
    @staticmethod
    def fetch_api_chart(symbol: str, range_str: str = "1y", interval_str: str = "1d"):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={range_str}&interval={interval_str}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=0.8) as response:
                res = json.loads(response.read().decode('utf-8'))
                result = res['chart']['result'][0]
                timestamps = result.get('timestamp', [])
                quote = result['indicators']['quote'][0]
                
                df = pd.DataFrame({
                    'Close': quote.get('close', []),
                    'High': quote.get('high', []),
                    'Low': quote.get('low', []),
                    'Volume': quote.get('volume', [])
                }, index=pd.to_datetime(timestamps, unit='s'))
                return df.dropna()
        except:
            return pd.DataFrame()

    @staticmethod
    def search_stock_suggestions(search_term: str):
        if not search_term or len(search_term.strip()) == 0:
            return []
        term = search_term.strip().upper()
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(term)}&quotesCount=8&newsCount=0"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=0.8) as response:
                data = json.loads(response.read().decode('utf-8'))
                quotes = data.get('quotes', [])
                suggestions = []
                for q in quotes:
                    if q.get('quoteType') == 'EQUITY':
                        symbol = q.get('symbol')
                        name = q.get('shortname', symbol)
                        suggestions.append((f"{symbol} | {name}", symbol))
                return suggestions
        except:
            return []

    @staticmethod
    @st.cache_data(ttl=120, show_spinner=False)
    def get_market_overview_data():
        tickers = {"NQ": "NQ=F", "ES": "ES=F", "USDKRW": "USDKRW=X", "VIX": "^VIX", "TNX": "^TNX", "BTC": "BTC-USD"}
        results = {}
        for key, sym in tickers.items():
            df = QuantEngine.fetch_api_chart(sym, range_str="5d", interval_str="1d")
            if not df.empty and len(df) >= 2:
                curr = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2])
                chg_p = ((curr - prev) / prev) * 100
                results[key] = (curr, chg_p)

        defaults = {"NQ": (19850.25, 0.15), "ES": (5540.50, 0.08), "USDKRW": (1378.50, -0.22), "VIX": (15.20, -1.50), "TNX": (3.94, -0.05), "BTC": (60850.00, 1.25)}
        for k, v in defaults.items():
            if k not in results: results[k] = v
        return results

    @staticmethod
    @st.cache_data(ttl=180, show_spinner=False)
    def fetch_market_data(ticker_symbol: str, timeframe: str = "1D"):
        try:
            range_str = "1y" if timeframe == "1D" else "5d"
            interval_str = "1d" if timeframe == "1D" else ("1h" if timeframe == "1H" else "15m")
            
            data = QuantEngine.fetch_api_chart(ticker_symbol, range_str, interval_str)
            if data.empty: return None

            close = data['Close']
            high = data['High']
            low = data['Low']
            
            curr_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2] if len(close) > 1 else close.iloc[-1])
            price_change_p = ((curr_price - prev_price) / prev_price) * 100
            
            atr = float((high.tail(14) - low.tail(14)).mean())
            stop_loss = curr_price - (atr * 1.5) 
            take_profit = curr_price + (atr * 2.5)

            ema20 = close.ewm(span=20, adjust=False).mean()
            diff = close.diff()
            gain = diff.where(diff > 0, 0).rolling(14).mean()
            loss = (-diff.where(diff < 0, 0)).rolling(14).mean() + 1e-9
            rsi = float(100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1]))))

            score = 50
            if curr_price > ema20.iloc[-1]: score += 25
            if 45 <= rsi <= 65: score += 25
            score = max(0, min(100, score))

            return {
                "ticker": ticker_symbol, "curr_price": curr_price, "price_change_p": price_change_p,
                "ema20": ema20, "stop_loss": round(stop_loss, 2), "take_profit": round(take_profit, 2),
                "rsi": rsi, "score": score, "data": data
            }
        except:
            return None

# Session State 관리
if 'selected_ticker' not in st.session_state: st.session_state['selected_ticker'] = "ASTS"
if 'timeframe' not in st.session_state: st.session_state['timeframe'] = "1D"

query_params = st.query_params
if "q" in query_params: st.session_state['selected_ticker'] = query_params["q"].upper()

# ── [메인 로고 영역] ──
col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
with col_b2:
    main_logo = get_cached_logo_base64("taurusfinal.png")
    if main_logo:
        st.markdown(f'<div style="text-align: center; margin-bottom: 15px;"><img src="{main_logo}" style="max-width: 220px; width: 100%; height: auto;"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background: #121824; border: 1px solid #FF2A2A; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 15px;"><h2 style="color: #FF2A2A; margin: 0; font-size: 24px;">TAURUS LAB</h2></div>', unsafe_allow_html=True)

# ── [Market Overview] ──
market_data = QuantEngine.get_market_overview_data()
nq_val, nq_chg = market_data["NQ"]
es_val, es_chg = market_data["ES"]
usd_val, usd_chg = market_data["USDKRW"]
vix_val, vix_chg = market_data["VIX"]

st.markdown(f"""
<div style="background-color:#121824; border:1px solid #1E293B; border-radius:6px; padding:8px 16px; font-size:12px; display:flex; justify-content:space-between; color:#94A3B8; margin-bottom:15px;">
    <div>나스닥 선물: <b style="color:#F8FAFC;">{nq_val:,.1f}</b> <span style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({nq_chg:+.2f}%)</span></div>
    <div>S&P 500: <b style="color:#F8FAFC;">{es_val:,.1f}</b> <span style="color:{'#00E676' if es_chg>=0 else '#EF4444'};">({es_chg:+.2f}%)</span></div>
    <div>원/달러: <b style="color:#F8FAFC;">₩{usd_val:,.1f}</b> <span style="color:{'#00E676' if usd_chg>=0 else '#EF4444'};">({usd_chg:+.2f}%)</span></div>
    <div>VIX: <b style="color:#F8FAFC;">{vix_val:,.1f}</b> <span style="color:{'#EF4444' if vix_chg>=0 else '#00E676'};">({vix_chg:+.2f}%)</span></div>
</div>
""", unsafe_allow_html=True)

# ── [검색창] ──
col_search, _ = st.columns([2.0, 3.0])
with col_search:
    selected_ticker_result = st_searchbox(
        QuantEngine.search_stock_suggestions,
        placeholder="예: AAPL, TSLA, AMZN...",
        key="stock_autocomplete_search",
    )
    if selected_ticker_result and selected_ticker_result != st.session_state['selected_ticker']:
        st.session_state['selected_ticker'] = selected_ticker_result.upper()
        st.query_params["q"] = selected_ticker_result.upper()
        st.rerun()

res = QuantEngine.fetch_market_data(st.session_state['selected_ticker'], st.session_state['timeframe'])

if res:
    st.markdown(f"<h3 style='color: #F8FAFC; margin: 5px 0;'>[{res['ticker']}]</h3>", unsafe_allow_html=True)
    
    score = res['score']
    box_bg = "#00E676" if score >= 70 else ("#F59E0B" if score >= 40 else "#EF4444")
    
    st.markdown(f"<div style='background: {box_bg}; color: #000; font-weight: 800; font-size: 14px; text-align: center; padding: 6px; border-radius: 6px; margin-bottom: 10px;'>"
                f"매수적합도 : {score} / 100 점</div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재가", f"${res['curr_price']:.2f}", f"{res['price_change_p']:+.2f}%")
    col2.metric("목표가 (TP)", f"${res['take_profit']}")
    col3.metric("손절가 (SL)", f"${res['stop_loss']}")
    col4.metric("RSI (14)", f"{res['rsi']:.1f}")

    # ⚡ [초고속] 경량화된 SVG 차트 (JS 외부 다운로드 0초)
    st.markdown("<h4 style='color: #94A3B8; font-size: 13px; margin-top: 10px;'>📈 Technical Trend (Real-time)</h4>", unsafe_allow_html=True)
    
    chart_df = res['data']['Close'].tail(40)
    min_val, max_val = chart_df.min(), chart_df.max()
    val_range = (max_val - min_val) if max_val != min_val else 1
    
    points = []
    width, height = 800, 150
    for i, val in enumerate(chart_df):
        x = (i / (len(chart_df) - 1)) * width
        y = height - ((val - min_val) / val_range) * (height - 20) - 10
        points.append(f"{x:.1f},{y:.1f}")
    
    polyline_str = " ".join(points)
    
    svg_chart = f"""
    <div style="background-color:#121824; border:1px solid #1E293B; border-radius:8px; padding:10px; width:100%;">
        <svg viewBox="0 0 {width} {height}" style="width:100%; height:160px;">
            <polyline fill="none" stroke="#00E676" stroke-width="2.5" points="{polyline_str}" />
        </svg>
    </div>
    """
    st.markdown(svg_chart, unsafe_allow_html=True)
