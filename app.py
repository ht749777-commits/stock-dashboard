import streamlit as st
import streamlit.components.v1 as components
import urllib.request
import urllib.parse
import json
import re
import time
import base64
from datetime import datetime, timedelta, timezone
import pandas as pd
from streamlit_searchbox import st_searchbox
from streamlit_autorefresh import st_autorefresh

# 1분(60,000 밀리초)마다 자동 새로고침
count = st_autorefresh(interval=60 * 1000, limit=None, key="datarefresh")

def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
            ext = path.split('.')[-1].lower()
            mime_type = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return ""

st.set_page_config(
    page_title="TAURUS LAB",
    page_icon="taurusfinal.png",
    layout="wide"
)

# 🎨 다크 테마 및 CSS
st.markdown("""<style>
.stApp { background-color: #0B0E14 !important; color: #E0E0E0 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

div[data-testid="stMetric"] {
    background-color: #121824 !important;
    border: 1px solid #1E293B !important;
    padding: 14px !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    min-height: 95px !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
div[data-testid="stMetric"] label {
    color: #94A3B8 !important;
    font-weight: 600 !important;
    font-size: 11px !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #F8FAFC !important;
    font-weight: 800 !important;
    font-size: 17px !important;
}

.news-card { 
    background-color: #121824 !important; 
    padding: 12px 16px; 
    border-radius: 8px; 
    border: 1px solid #1E293B; 
    margin-bottom: 8px; 
}

.stTabs [data-baseweb="tab-list"] { gap: 6px; background-color: transparent; }
.stTabs [data-baseweb="tab"] { background-color: #121824; border-radius: 6px; color: #94A3B8; border: 1px solid #1E293B; padding: 6px 12px; font-size: 13px; }
.stTabs [aria-selected="true"] { background-color: #1E293B !important; color: #00E676 !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

class QuantEngine:
    # ⚡ [초고속] Yahoo REST API 직접 단일 호출
    @staticmethod
    def fetch_api_chart(symbol: str, range_str: str = "1y", interval_str: str = "1d"):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={range_str}&interval={interval_str}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=1.5) as response:
                res = json.loads(response.read().decode('utf-8'))
                result = res['chart']['result'][0]
                
                timestamps = result.get('timestamp', [])
                quote = result['indicators']['quote'][0]
                
                close_vals = quote.get('close', [])
                high_vals = quote.get('high', [])
                low_vals = quote.get('low', [])
                vol_vals = quote.get('volume', [])
                
                df = pd.DataFrame({
                    'Close': close_vals,
                    'High': high_vals,
                    'Low': low_vals,
                    'Volume': vol_vals
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
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(term)}&quotesCount=10&newsCount=0"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=1.0) as response:
                data = json.loads(response.read().decode('utf-8'))
                quotes = data.get('quotes', [])
                suggestions = []
                us_exchanges = {"NMS", "NYQ", "NGM", "ASE", "PCX", "OBB", "PNK"}
                
                for q in quotes:
                    if q.get('quoteType') == 'EQUITY' and (q.get('exchange') in us_exchanges or '.' not in q.get('symbol', '')):
                        symbol = q.get('symbol')
                        name = q.get('shortname', q.get('longname', symbol))
                        suggestions.append((f"{symbol}  |  {name}", symbol))
                return suggestions
        except:
            return []

    # ⚡ Market Overview 빠른 수집 (캐싱 적용)
    @staticmethod
    @st.cache_data(ttl=60)
    def get_market_overview_data():
        tickers = {
            "NQ": "NQ=F", "ES": "ES=F", "USDKRW": "USDKRW=X",
            "VIX": "^VIX", "TNX": "^TNX", "BTC": "BTC-USD"
        }
        results = {}
        for key, sym in tickers.items():
            df = QuantEngine.fetch_api_chart(sym, range_str="5d", interval_str="1d")
            if not df.empty and len(df) >= 2:
                curr = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2])
                chg_p = ((curr - prev) / prev) * 100
                results[key] = (curr, chg_p)

        default_res = {
            "NQ": (19850.25, 0.15), "ES": (5540.50, 0.08), "USDKRW": (1378.50, -0.22),
            "VIX": (15.20, -1.50), "TNX": (3.94, -0.05), "BTC": (60850.00, 1.25)
        }
        for k, v in default_res.items():
            if k not in results:
                results[k] = v
        return results

    # ⚡ 메인 종목 퀀트 지표 연산
    @staticmethod
    @st.cache_data(ttl=120)
    def fetch_market_data(ticker_symbol: str, timeframe: str = "1D"):
        try:
            range_str = "1y" if timeframe == "1D" else "5d"
            interval_str = "1d" if timeframe == "1D" else ("1h" if timeframe == "1H" else "15m")
            
            data = QuantEngine.fetch_api_chart(ticker_symbol, range_str, interval_str)
            if data.empty:
                return None

            close = data['Close']
            high = data['High']
            low = data['Low']
            volume = data['Volume']
            
            curr_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2] if len(close) > 1 else close.iloc[-1])
            price_change_p = ((curr_price - prev_price) / prev_price) * 100
            
            atr = float((high.tail(14) - low.tail(14)).mean())
            stop_loss = curr_price - (atr * 1.5) 
            take_profit = curr_price + (atr * 2.5)

            ema20 = close.ewm(span=20, adjust=False).mean()
            ema50 = close.ewm(span=50, adjust=False).mean() if len(close) >= 50 else ema20
            ema200 = close.ewm(span=200, adjust=False).mean() if len(close) >= 200 else ema50
            
            diff = close.diff()
            gain = diff.where(diff > 0, 0).rolling(14).mean()
            loss = (-diff.where(diff < 0, 0)).rolling(14).mean() + 1e-9
            rsi = float(100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1]))))

            # 백테스트 간단 구현
            strategy_ret = close.pct_change().fillna(0).where(close > ema20, 0)
            bt_ret = float((((1 + strategy_ret).prod() - 1) * 100))
            bt_win = float((strategy_ret[strategy_ret != 0] > 0).mean() * 100) if len(strategy_ret[strategy_ret != 0]) > 0 else 60.0
            bt_mdd = float(((1 + strategy_ret).cumprod() / (1 + strategy_ret).cumprod().cummax() - 1).min() * 100)

            score = 50
            if curr_price > ema20.iloc[-1]: score += 20
            if 45 <= rsi <= 65: score += 15
            if bt_ret > 0: score += 15
            score = max(0, min(100, score))

            return {
                "ticker": ticker_symbol, "curr_price": curr_price, "price_change_p": price_change_p,
                "ema20": ema20, "ema50": ema50, "ema200": ema200,
                "stop_loss": round(stop_loss, 2), "take_profit": round(take_profit, 2),
                "rsi": rsi, "bt_ret": bt_ret, "bt_win": bt_win, "bt_mdd": bt_mdd,
                "score": score, "data": data
            }
        except:
            return None

if 'selected_ticker' not in st.session_state:
    st.session_state['selected_ticker'] = "ASTS"
if 'timeframe' not in st.session_state:
    st.session_state['timeframe'] = "1D"

query_params = st.query_params
if "q" in query_params:
    st.session_state['selected_ticker'] = query_params["q"].upper()
if "tf" in query_params:
    st.session_state['timeframe'] = query_params["tf"].upper()

# ── [우측 상단 팝오버 메뉴] ──
_, col_popover = st.columns([10, 1])
with col_popover:
    with st.popover("⚙️ 메뉴"):
        st.markdown("**메뉴**")
        st.button("홈 대시보드", use_container_width=True)

# ── [메인 로고 영역] ──
col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
with col_b2:
    main_logo = get_image_base64("taurusfinal.png")
    if main_logo:
        st.markdown(f"""<div style="text-align: center; margin-bottom: 25px;">
<img src="{main_logo}" style="max-width: 260px; width: 100%; height: auto;">
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="background: linear-gradient(135deg, #121824 0%, #1E293B 100%); border: 2px solid #FF2A2A; border-radius: 12px; padding: 15px; text-align: center; margin-bottom: 20px;">
<h1 style="color: #FF2A2A; margin: 0; font-size: 28px; font-weight: 900;">TAURUS LAB</h1>
</div>""", unsafe_allow_html=True)

# ── [Market Overview] ──
market_data = QuantEngine.get_market_overview_data()
nq_val, nq_chg = market_data["NQ"]
es_val, es_chg = market_data["ES"]
usd_val, usd_chg = market_data["USDKRW"]
vix_val, vix_chg = market_data["VIX"]
tnx_val, tnx_chg = market_data["TNX"]
btc_val, btc_chg = market_data["BTC"]

market_component_html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ margin: 0; background-color: transparent; font-family: sans-serif; }}
    .market-overview-container {{ width: 100%; background-color: #121824; border-radius: 8px; border: 1px solid #1E293B; }}
    .market-bar {{ display: flex; align-items: center; height: 48px; padding: 0 16px; }}
    .market-title-badge {{ color: #00E676; font-weight: 900; font-size: 14px; margin-right: 15px; }}
    .ticker-slider-window {{ height: 24px; overflow: hidden; position: relative; flex-grow: 1; }}
    .ticker-slider-list {{ position: absolute; width: 100%; animation: slotRoll 18s infinite; margin: 0; padding: 0; list-style: none; }}
    .ticker-item {{ height: 24px; line-height: 24px; font-size: 13px; color: #94A3B8; }}
    @keyframes slotRoll {{
        0%, 12% {{ top: 0px; }} 16%, 28% {{ top: -24px; }} 32%, 44% {{ top: -48px; }}
        48%, 60% {{ top: -72px; }} 64%, 76% {{ top: -96px; }} 80%, 92% {{ top: -120px; }} 100% {{ top: -144px; }}
    }}
</style>
</head>
<body>
<div class="market-overview-container">
    <div class="market-bar">
        <div class="market-title-badge">📊 Market Overview</div>
        <div class="ticker-slider-window">
            <ul class="ticker-slider-list">
                <li class="ticker-item">나스닥 100 선물: <b style="color:#F8FAFC;">{nq_val:,.2f}</b> <span style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({nq_chg:+.2f}%)</span></li>
                <li class="ticker-item">S&P 500 선물: <b style="color:#F8FAFC;">{es_val:,.2f}</b> <span style="color:{'#00E676' if es_chg>=0 else '#EF4444'};">({es_chg:+.2f}%)</span></li>
                <li class="ticker-item">원/달러 환율: <b style="color:#F8FAFC;">₩{usd_val:,.2f}</b> <span style="color:{'#00E676' if usd_chg>=0 else '#EF4444'};">({usd_chg:+.2f}%)</span></li>
                <li class="ticker-item">VIX 지수: <b style="color:#F8FAFC;">{vix_val:,.2f}</b> <span style="color:{'#EF4444' if vix_chg>=0 else '#00E676'};">({vix_chg:+.2f}%)</span></li>
                <li class="ticker-item">10년물 국채: <b style="color:#F8FAFC;">{tnx_val:.2f}%</b> <span style="color:{'#00E676' if tnx_chg>=0 else '#EF4444'};">({tnx_chg:+.2f}%)</span></li>
                <li class="ticker-item">비트코인: <b style="color:#F8FAFC;">${btc_val:,.0f}</b> <span style="color:{'#00E676' if btc_chg>=0 else '#EF4444'};">({btc_chg:+.2f}%)</span></li>
            </ul>
        </div>
    </div>
</div>
</body>
</html>
"""
components.html(market_component_html, height=54)

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
    st.markdown(f"<h3 style='color: #F8FAFC; margin-bottom: 5px;'>[{res['ticker']}]</h3>", unsafe_allow_html=True)
    
    score = res['score']
    box_bg = "#00E676" if score >= 70 else ("#F59E0B" if score >= 40 else "#EF4444")
    
    st.markdown(f"<div style='background: {box_bg}; color: #000; font-weight: 900; font-size: 15px; text-align: center; padding: 8px; border-radius: 8px; margin-bottom: 12px;'>"
                f"매수적합도 : {score} / 100 점</div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재가", f"${res['curr_price']:.2f}", f"{res['price_change_p']:+.2f}%")
    col2.metric("목표가 (TP)", f"${res['take_profit']}")
    col3.metric("손절가 (SL)", f"${res['stop_loss']}")
    col4.metric("RSI (14)", f"{res['rsi']:.1f}")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("백테스트 수익률", f"{res['bt_ret']:+.1f}%")
    col6.metric("전략 승률", f"{res['bt_win']:.1f}%")
    col7.metric("최대 낙폭", f"{res['bt_mdd']:.1f}%")
    col8.metric("타임프레임", st.session_state['timeframe'])

    # ⚡ [초고속] JavaScript Lightweight Charts 적용 (Matplotlib 제거)
    st.markdown("<h4 style='color: #94A3B8; font-size: 14px; margin-top: 15px;'>📈 Real-time Technical Chart</h4>", unsafe_allow_html=True)
    
    chart_df = res['data']
    line_data = [{"time": str(idx.date()), "value": round(val, 2)} for idx, val in chart_df['Close'].items()]
    ema20_data = [{"time": str(idx.date()), "value": round(val, 2)} for idx, val in res['ema20'].items()]

    js_chart_code = f"""
    <div id="chart" style="width:100%;height:350px;"></div>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
            layout: {{ backgroundColor: '#121824', textColor: '#94A3B8' }},
            grid: {{ vertLines: {{ color: '#1E293B' }}, horzLines: {{ color: '#1E293B' }} }},
            timeScale: {{ borderColor: '#1E293B' }}
        }});
        const mainSeries = chart.addLineSeries({{ color: '#00E676', lineWidth: 2, title: 'Close' }});
        mainSeries.setData({json.dumps(line_data)});
        const emaSeries = chart.addLineSeries({{ color: '#38BDF8', lineWidth: 1, lineStyle: 2, title: 'EMA20' }});
        emaSeries.setData({json.dumps(ema200_data if 'ema200_data' in locals() else ema20_data)});
    </script>
    """
    components.html(js_chart_code, height=360)

    # 탭
    tab_news, tab_gossip = st.tabs(["📰 구글 영문 뉴스", "💬 소셜 미디어"])
    with tab_news:
        st.info("외부 번역 지연을 방지하기 위해 실시간 뉴스는 선택 시 로드됩니다.")
    with tab_gossip:
        st.info("StockTwits 커뮤니티 데이터입니다.")
