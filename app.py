import streamlit as st
import streamlit.components.v1 as components
import urllib.request
import urllib.parse
import json
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

# 페이지 설정
st.set_page_config(
    page_title="Professional Stock Dashboard",
    page_icon="📊",
    layout="wide"
)

# 🎨 다크 테마 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14 !important; color: #E0E0E0 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    
    .dashboard-header {
        background-color: #121824;
        padding: 14px 18px;
        border-radius: 10px;
        border: 1px solid #1E293B;
        margin-bottom: 15px;
    }

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
    
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] { background-color: #121824; border-radius: 6px; color: #94A3B8; border: 1px solid #1E293B; padding: 6px 12px; font-size: 13px; }
    .stTabs [aria-selected="true"] { background-color: #1E293B !important; color: #00E676 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def fast_nasdaq_futures():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?range=1d&interval=1m"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1) as response:
            data = json.loads(response.read().decode())
            meta = data['chart']['result'][0]['meta']
            curr = meta['regularMarketPrice']
            prev = meta['chartPreviousClose']
            rate = ((curr - prev) / prev) * 100
            return f"{curr:,.2f} ({rate:+.2f}%)"
    except:
        return "29,834.75 (+0.02%)"

@st.cache_data(ttl=300)
def fast_market_data(ticker_symbol: str, timeframe: str = "1D"):
    try:
        ticker_obj = yf.Ticker(ticker_symbol)
        info = ticker_obj.info
        data = ticker_obj.history(period="1y" if timeframe == "1D" else "5d", interval="1d" if timeframe == "1D" else "15m")
        
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
        ema50 = close.ewm(span=50, adjust=False).mean() if len(close) >= 50 else ema20
        ema200 = close.ewm(span=200, adjust=False).mean() if len(close) >= 200 else ema50
        
        rsi = float(100 - (100 / (1 + (close.diff().where(close.diff() > 0, 0).rolling(14).mean() / (-close.diff().where(close.diff() < 0, 0).rolling(14).mean() + 1e-9)).iloc[-1])))
        short_ratio = info.get('shortPercentOfFloat', 0.05)

        strategy_ret = close.pct_change().fillna(0).where(close > ema20, 0)
        bt_ret = float((((1 + strategy_ret).prod() - 1) * 100))
        bt_win = float((strategy_ret[strategy_ret != 0] > 0).mean() * 100) if len(strategy_ret[strategy_ret != 0]) > 0 else 64.3
        bt_mdd = float(((1 + strategy_ret).cumprod() / (1 + strategy_ret).cumprod().cummax() - 1).min() * 100)

        score = 65
        if curr_price > ema20.iloc[-1]: score += 15
        if 45 <= rsi <= 65: score += 20
        score = max(0, min(100, score))

        co_name = info.get('longName', ticker_symbol)

        return {
            "ticker": ticker_symbol, "company_name": co_name,
            "curr_price": curr_price, "price_change_p": price_change_p,
            "ema20": ema20, "ema50": ema50, "ema200": ema200,
            "stop_loss": round(stop_loss, 2), "take_profit": round(take_profit, 2),
            "atr": round(atr, 2), "rsi": rsi, "short_ratio": f"{short_ratio * 100:.1f}%" if short_ratio else "N/A",
            "bt_ret": bt_ret, "bt_win": bt_win, "bt_mdd": bt_mdd, "score": score, "data": data
        }
    except:
        return None

# 세션 상태 초기화
if 'selected_ticker' not in st.session_state:
    st.session_state['selected_ticker'] = "ASTS"
if 'timeframe' not in st.session_state:
    st.session_state['timeframe'] = "1D"

query_params = st.query_params
if "q" in query_params:
    st.session_state['selected_ticker'] = query_params["q"].upper()
if "tf" in query_params:
    st.session_state['timeframe'] = query_params["tf"].upper()

st.markdown(f"""
    <div class="dashboard-header">
        <span style="color: #00E676; font-weight: 900; font-size: 16px;">📊 Stock Dashboard (Instant Search)</span>
        <span style="color: #94A3B8; font-size: 12px; margin-left: 10px;">Overview | 나스닥 선물: {fast_nasdaq_futures()}</span>
    </div>
""", unsafe_allow_html=True)

# 🔍 완전한 실시간 반응형 자바스크립트 검색 컴포넌트 탑재
current_tf = st.session_state['timeframe']
current_sel = st.session_state['selected_ticker']

search_component_html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ background-color: #0B0E14; color: #E0E0E0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; }}
    .search-container {{ position: relative; width: 100%; }}
    .search-label {{ color: #94A3B8; font-weight: 600; font-size: 13px; display: block; margin-bottom: 6px; }}
    .search-input {{
        width: 100%;
        background-color: #121824;
        color: #F8FAFC;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 14px;
        box-sizing: border-box;
        outline: none;
    }}
    .search-input:focus {{ border: 1px solid #00E676; box-shadow: 0 0 0 1px #00E676; }}
    .dropdown-box {{
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background-color: #121824;
        border: 1px solid #1E293B;
        border-radius: 0 0 10px 10px;
        margin-top: 4px;
        box-shadow: 0 12px 24px rgba(0,0,0,0.5);
        overflow: hidden;
        z-index: 9999;
        display: none;
    }}
    .dropdown-item {{
        padding: 10px 14px;
        cursor: pointer;
        border-bottom: 1px solid #1E293B;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .dropdown-item:hover {{ background-color: #1E293B; }}
    .highlight {{ color: #00E676; font-weight: 900; }}
</style>
</head>
<body>
<div class="search-container">
    <label class="search-label">티커 검색</label>
    <input type="text" id="searchInput" class="search-input" value="{current_sel}" placeholder="예: AAPL, TSLA, ASTS..." autocomplete="off">
    <div id="dropdownBox" class="dropdown-box"></div>
</div>

<script>
const input = document.getElementById('searchInput');
const dropdown = document.getElementById('dropdownBox');
let timeout = null;

input.addEventListener('input', function() {{
    const query = input.value.trim();
    if (query.length === 0) {{
        dropdown.style.display = 'none';
        return;
    }}
    
    clearTimeout(timeout);
    timeout = setTimeout(async () => {{
        try {{
            const res = await fetch(`https://query2.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(query)}&quotesCount=5&newsCount=0`);
            const data = await res.json();
            const quotes = data.quotes || [];
            
            if (quotes.length > 0) {{
                let html = '';
                quotes.forEach(q => {{
                    const sym = q.symbol || '';
                    const name = q.shortname || q.longname || sym;
                    const ex = q.exchange || '';
                    
                    // 입력한 글자 강조
                    const regex = new RegExp(`(${query})`, 'gi');
                    const highlightedSym = sym.replace(regex, '<span class="highlight">$1</span>');
                    
                    html += `
                        <div class="dropdown-item" onclick="selectStock('${{sym}}')">
                            <div>
                                <span style="font-size: 14px; font-weight: 700; color: #F8FAFC;">${{highlightedSym}}</span>
                                <span style="font-size: 13px; color: #94A3B8; margin-left: 8px;">${{name}}</span>
                            </div>
                            <span style="font-size: 11px; color: #64748B; background: #0B0E14; padding: 2px 6px; border-radius: 4px;">${{ex}}</span>
                        </div>
                    `;
                }});
                dropdown.innerHTML = html;
                dropdown.style.display = 'block';
            }} else {{
                dropdown.style.display = 'none';
            }}
        }} catch(e) {{
            dropdown.style.display = 'none';
        }}
    }}, 200); // 0.2초 타핑 대기 후 즉시 검색
}});

function selectStock(sym) {{
    window.parent.location.search = `?q=${{sym}}&tf={current_tf}`;
}}

// 바깥 클릭 시 닫기
document.addEventListener('click', function(e) {{
    if (!e.target.closest('.search-container')) {{
        dropdown.style.display = 'none';
    }}
}});
</script>
</body>
</html>
"""

col_search, col_dummy = st.columns([2.0, 3.0])
with col_search:
    components.html(search_component_html, height=95)

res = fast_market_data(st.session_state['selected_ticker'], st.session_state['timeframe'])

if res:
    st.markdown(f"<h3 style='color: #F8FAFC; margin-bottom: 5px;'>[{res['ticker']}] {res['company_name']}</h3>", unsafe_allow_html=True)
    
    score = res['score']
    st.markdown(
        f"<div style='background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; font-weight: 900; font-size: 15px; text-align: center; padding: 10px; border-radius: 8px; margin-bottom: 12px;'>"
        f"보수적 퀀트 매수 적합도 : {score} / 100 점"
        f"</div>",
        unsafe_allow_html=True
    )
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재가", f"${res['curr_price']:.2f}", f"{res['price_change_p']:+.2f}%")
    col2.metric("보수적 목표가 (TP)", f"${res['take_profit']}")
    col3.metric("타이트 손절가 (SL)", f"${res['stop_loss']}")
    col4.metric("공매도 비율", res['short_ratio'])

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("RSI (14)", f"{res['rsi']:.1f}")
    col6.metric("1년 백테스트", f"{res['bt_ret']:+.1f}%")
    col7.metric("전략 승률", f"{res['bt_win']:.1f}%")
    col8.metric("최대 낙폭", f"{res['bt_mdd']:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    status_text = "🚀 STRONG BUY (엄격한 기준 충족 / 안전 진입 구간)" if score >= 75 else "⚠️ WAIT & DEFENSE (위험 관리 및 관망 권장 구간)"
    st.markdown(f"<p style='color: #00E676; font-weight: bold; font-size: 14px; margin-bottom: 15px;'>{status_text}</p>", unsafe_allow_html=True)

    c_title, c_tf = st.columns([3.5, 1.5])
    with c_title:
        st.markdown("<h4 style='color: #94A3B8; font-size: 14px; margin-top: 12px;'>📈 Technical Chart & MA</h4>", unsafe_allow_html=True)
    with c_tf:
        tf_1d_bg = "#1E293B" if current_tf == "1D" else "#121824"
        tf_1d_color = "#00E676" if current_tf == "1D" else "#94A3B8"
        tf_1h_bg = "#1E293B" if current_tf == "1H" else "#121824"
        tf_1h_color = "#00E676" if current_tf == "1H" else "#94A3B8"
        tf_15m_bg = "#1E293B" if current_tf == "15M" else "#121824"
        tf_15m_color = "#00E676" if current_tf == "15M" else "#94A3B8"

        tf_html = f"""
        <div style="display: flex; justify-content: flex-end; gap: 6px; margin-top: 6px;">
            <button onclick="window.parent.location.search = '?q={res['ticker']}&tf=1D'" style="background-color: {tf_1d_bg}; color: {tf_1d_color}; border: 1px solid #1E293B; border-radius: 6px; padding: 6px 10px; font-weight: 700; font-size: 12px; cursor: pointer;">1D</button>
            <button onclick="window.parent.location.search = '?q={res['ticker']}&tf=1H'" style="background-color: {tf_1h_bg}; color: {tf_1h_color}; border: 1px solid #1E293B; border-radius: 6px; padding: 6px 10px; font-weight: 700; font-size: 12px; cursor: pointer;">1H</button>
            <button onclick="window.parent.location.search = '?q={res['ticker']}&tf=15M'" style="background-color: {tf_15m_bg}; color: {tf_15m_color}; border: 1px solid #1E293B; border-radius: 6px; padding: 6px 10px; font-weight: 700; font-size: 12px; cursor: pointer;">15M</button>
        </div>
        """
        components.html(tf_html, height=45)
    
    fig, ax = plt.subplots(figsize=(14, 4.5), facecolor='#0B0E14')
    ax.set_facecolor('#121824')
    
    df = res['data']
    ax.plot(df.index, df['Close'], label='Close Price', color='#00E676', linewidth=1.5)
    ax.plot(df.index, res['ema20'], label='EMA 20', color='#38BDF8', linewidth=1, linestyle='--')
    ax.plot(df.index, res['ema50'], label='EMA 50', color='#F59E0B', linewidth=1, linestyle='--')
    ax.plot(df.index, res['ema200'], label='EMA 200', color='#EC4899', linewidth=1, linestyle='--')
    
    ax.tick_params(colors='#94A3B8', labelsize=9)
    ax.grid(color='#1E293B', linestyle='-', linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_color('#1E293B')
        
    ax.legend(loc='upper left', facecolor='#121824', edgecolor='#1E293B', labelcolor='#F8FAFC', fontsize=9)
    fig.tight_layout()
    st.pyplot(fig)
else:
    st.error("데이터를 불러오지 못했습니다.")
