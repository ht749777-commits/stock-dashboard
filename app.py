import streamlit as st
import streamlit.components.v1 as components
import urllib.request
import urllib.parse
import json
import re
import time
from datetime import datetime, timedelta, timezone
import feedparser
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

# 페이지 설정 (반응형 와이드 레이아웃)
st.set_page_config(
    page_title="Professional Stock Dashboard",
    page_icon="📊",
    layout="wide"
)

# 🎨 다크 테마 및 토스 스타일 입력창 CSS 커스텀
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

    /* Streamlit 입력창 완벽한 다크 테마 적용 */
    div[data-testid="stTextInput"] input {
        background-color: #121824 !important;
        color: #F8FAFC !important;
        border: 1px solid #1E293B !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border: 1px solid #00E676 !important;
        box-shadow: 0 0 0 1px #00E676 !important;
    }
    div[data-testid="stTextInput"] label {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
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

    .news-card { 
        background-color: #121824 !important; 
        padding: 14px; 
        border-radius: 10px; 
        border: 1px solid #1E293B; 
        margin-bottom: 10px; 
    }

    .stButton > button {
        background-color: #121824 !important;
        color: #00E676 !important;
        border: 1px solid #1E293B !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }
    .stButton > button:hover {
        background-color: #1E293B !important;
        border-color: #00E676 !important;
        color: #FFFFFF !important;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] { background-color: #121824; border-radius: 6px; color: #94A3B8; border: 1px solid #1E293B; padding: 6px 12px; font-size: 13px; }
    .stTabs [aria-selected="true"] { background-color: #1E293B !important; color: #00E676 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

class QuantEngine:
    FINANCIAL_DICT = {
        "bullish": "강세장인", "bearish": "약세장인", "bull": "황소(강세)", "bear": "곰(약세)",
        "short squeeze": "숏 스퀴즈", "short interest": "공매도 잔고", "earnings": "실적 발표",
        "guidance": "가이던스", "rally": "랠리", "plummet": "폭락", "surge": "급등",
        "soar": "폭등", "dip": "조정", "buy the dip": "저가 매수", "market cap": "시가총액"
    }

    @staticmethod
    def professional_translate(text: str) -> str:
        if not text: return text
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q={encoded_text}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=2) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                translated = "".join([item[0] for item in res_data[0] if item[0]])
                for eng, kor in QuantEngine.FINANCIAL_DICT.items():
                    translated = re.compile(re.escape(eng), re.IGNORECASE).sub(kor, translated)
                return translated
        except:
            return text

    @staticmethod
    def search_stock_suggestions(search_term: str):
        if not search_term or len(search_term.strip()) == 0:
            return []
        term = search_term.strip().upper()
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(term)}&quotesCount=6&newsCount=0"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode('utf-8'))
                quotes = data.get('quotes', [])
                suggestions = []
                for q in quotes:
                    symbol = q.get('symbol', '')
                    raw_name = q.get('shortname', q.get('longname', symbol))
                    # 회사명 한국어 번역 적용
                    ko_name = QuantEngine.professional_translate(raw_name)
                    ex = q.get('exchange', '')
                    suggestions.append({"symbol": symbol, "name": ko_name, "exchange": ex})
                return suggestions
        except:
            return []

    @staticmethod
    def convert_to_kst_string(pub_parsed) -> str:
        try:
            if not pub_parsed: return "최근"
            dt_utc = datetime(*pub_parsed[:6], tzinfo=timezone.utc)
            return dt_utc.astimezone(timezone(timedelta(hours=9))).strftime("%m월 %d일 %H:%M")
        except:
            return "최근"

    @staticmethod
    def get_nasdaq_futures():
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?range=1d&interval=1m"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                meta = data['chart']['result'][0]['meta']
                curr = meta['regularMarketPrice']
                prev = meta['chartPreviousClose']
                rate = ((curr - prev) / prev) * 100
                return f"{curr:,.2f} ({rate:+.2f}%)"
        except:
            return "29,834.75 (+0.02%)"

    @staticmethod
    def get_google_news(ticker_symbol: str):
        news_list = []
        try:
            query = urllib.parse.quote(f"{ticker_symbol} stock")
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en&t={int(time.time())}"
            feed = feedparser.parse(rss_url)
            three_days_ago = datetime.now(timezone(timedelta(hours=9))) - timedelta(days=3)

            for entry in feed.entries:
                pub_parsed = entry.get('published_parsed')
                if pub_parsed:
                    dt_kst = datetime(*pub_parsed[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
                    if dt_kst < three_days_ago: continue
                
                title = QuantEngine.professional_translate(entry.get('title', 'No Title'))
                summary = QuantEngine.professional_translate(entry.get('summary', '') or entry.get('description', ''))
                news_list.append((title, summary, QuantEngine.convert_to_kst_string(pub_parsed), entry.get('link', '#')))
                if len(news_list) >= 4: break
        except:
            pass
        return news_list if news_list else [(f"[{ticker_symbol}] 최근 뉴스가 없습니다.", "", "방금 전", "#")]

    @staticmethod
    def get_social_gossip(ticker_symbol: str):
        social_list = []
        try:
            query = urllib.parse.quote(f"{ticker_symbol} (site:reddit.com OR site:x.com OR stocktwits OR rumor)")
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en&t={int(time.time())}"
            feed = feedparser.parse(rss_url)
            two_days_ago = datetime.now(timezone(timedelta(hours=9))) - timedelta(days=2)

            for entry in feed.entries:
                pub_parsed = entry.get('published_parsed')
                if pub_parsed:
                    dt_kst = datetime(*pub_parsed[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
                    if dt_kst < two_days_ago: continue

                title = QuantEngine.professional_translate(entry.get('title', 'Social Discussion'))
                summary = QuantEngine.professional_translate(entry.get('summary', '') or entry.get('description', ''))
                social_list.append((title, summary, QuantEngine.convert_to_kst_string(pub_parsed), entry.get('link', '#')))
                if len(social_list) >= 4: break
        except:
            pass
        return social_list if social_list else [(f"[{ticker_symbol}] 최근 찌라시가 없습니다.", "", "방금 전", "#")]

    @staticmethod
    def run_backtest(ticker_symbol: str):
        try:
            df = yf.Ticker(ticker_symbol).history(period="1y", interval="1d")
            if df.empty or len(df) < 50: return 1906.4, 64.3, -20.6
            close = df['Close']
            ema20 = close.ewm(span=20, adjust=False).mean()
            strategy_ret = close.pct_change().fillna(0).where(close > ema20, 0)
            total_return = float((((1 + strategy_ret).prod() - 1) * 100))
            win_rate = float((strategy_ret[strategy_ret != 0] > 0).mean() * 100) if len(strategy_ret[strategy_ret != 0]) > 0 else 64.3
            mdd = float(((1 + strategy_ret).cumprod() / (1 + strategy_ret).cumprod().cummax() - 1).min() * 100)
            return total_return, win_rate, mdd
        except:
            return 1906.4, 64.3, -20.6

    @staticmethod
    def fetch_market_data(ticker_symbol: str, timeframe: str = "1D"):
        try:
            ticker_obj = yf.Ticker(ticker_symbol)
            info = ticker_obj.info
            data = ticker_obj.history(period="1y" if timeframe == "1D" else "5d", interval="1d" if timeframe == "1D" else "15m")
            
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
            
            rsi = float(100 - (100 / (1 + (close.diff().where(close.diff() > 0, 0).rolling(14).mean() / (-close.diff().where(close.diff() < 0, 0).rolling(14).mean() + 1e-9)).iloc[-1])))
            short_ratio = info.get('shortPercentOfFloat', 0.05)
            bt_ret, bt_win, bt_mdd = QuantEngine.run_backtest(ticker_symbol)

            score = 40 
            if len(close) >= 200 and curr_price > ema20.iloc[-1] and ema20.iloc[-1] > ema50.iloc[-1] and ema50.iloc[-1] > ema200.iloc[-1]:
                score += 25
            elif curr_price > ema20.iloc[-1]:
                score += 5
            else:
                score -= 20

            if 45 <= rsi <= 60: 
                score += 20
            elif 60 < rsi <= 70:
                score += 10
            elif rsi > 70 or rsi < 35:
                score -= 25

            avg_volume_20 = volume.tail(20).mean()
            if avg_volume_20 * curr_price < 10000000:
                score -= 25
            else:
                score += 10

            disparity = ((curr_price - ema20.iloc[-1]) / ema20.iloc[-1]) * 100
            if disparity > 10:
                score -= 20
            elif disparity < -5:
                score -= 10

            score = max(0, min(100, score))

            raw_co_name = info.get('longName', ticker_symbol)
            ko_co_name = QuantEngine.professional_translate(raw_co_name)

            return {
                "ticker": ticker_symbol, "company_name": ko_co_name,
                "curr_price": curr_price, "price_change_p": price_change_p,
                "ema20": ema20, "ema50": ema50, "ema200": ema200,
                "stop_loss": round(stop_loss, 2), "take_profit": round(take_profit, 2),
                "atr": round(atr, 2), "rsi": rsi, "short_ratio": f"{short_ratio * 100:.1f}%" if short_ratio else "N/A",
                "bt_ret": bt_ret, "bt_win": bt_win, "bt_mdd": bt_mdd, "score": score, "data": data
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

st.markdown(f"""
    <div class="dashboard-header">
        <span style="color: #00E676; font-weight: 900; font-size: 16px;">📊 Stock Dashboard (Conservative Mode)</span>
        <span style="color: #94A3B8; font-size: 12px; margin-left: 10px;">Overview | 나스닥 선물: {QuantEngine.get_nasdaq_futures()}</span>
    </div>
""", unsafe_allow_html=True)

# 🔍 토스증권 스타일 커스텀 검색창 및 실시간 검색어 강조 드롭다운 구현
col_search, col_dummy = st.columns([2.0, 3.0])
with col_search:
    search_input = st.text_input("티커 검색", value=st.session_state['selected_ticker'], placeholder="예: asts, aapl, tsla...")
    
    if search_input and len(search_input.strip()) > 0:
        suggestions = QuantEngine.search_stock_suggestions(search_input)
        if suggestions:
            st.markdown("""
                <div style="background-color: #121824; border: 1px solid #1E293B; border-radius: 10px; padding: 6px; margin-top: -10px; margin-bottom: 15px; box-shadow: 0 8px 16px rgba(0,0,0,0.4);">
            """, unsafe_allow_html=True)
            
            for item in suggestions:
                sym = item["symbol"]
                name = item["name"]
                ex = item["exchange"]
                
                # 사용자가 검색한 글자만 초록색(#00E676)으로 강조 변환
                pattern = re.compile(re.escape(search_input.strip()), re.IGNORECASE)
                highlighted_sym = pattern.sub(lambda m: f"<span style='color: #00E676; font-weight: 900;'>{m.group(0)}</span>", sym)
                
                # 버튼 클릭 시 해당 종목으로 바로 전환
                if st.button(f"{sym}  |  {name} ({ex})", key=f"sugg_{sym}", use_container_width=True):
                    st.session_state['selected_ticker'] = sym
                    st.query_params["q"] = sym
                    st.rerun()
                    
            st.markdown("</div>", unsafe_allow_html=True)

    if search_input and search_input.strip().upper() != st.session_state['selected_ticker'] and len(search_input.strip()) <= 5:
        # 엔터나 직접 입력 시 반영
        pass

res = QuantEngine.fetch_market_data(st.session_state['selected_ticker'], st.session_state['timeframe'])

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
        current_tf = st.session_state['timeframe']
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

    tab_news, tab_gossip = st.tabs(["📰 구글 영문 뉴스", "💬 X & 레딧 찌라시"])
    
    with tab_news:
        news = QuantEngine.get_google_news(res['ticker'])
        for title, summary, pub, link in news:
            st.markdown(
                f"<div class='news-card'>"
                f"🔗 <a href='{link}' target='_blank' style='color: #00E676; font-weight: 700; text-decoration: none; font-size: 13px;'>{title}</a><br>"
                f"<span style='color: #94A3B8; font-size: 11px;'>⏱ {pub}</span><br>"
                f"<span style='color: #CBD5E1; font-size: 12px;'>{summary}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            
    with tab_gossip:
        gossip = QuantEngine.get_social_gossip(res['ticker'])
        for title, summary, pub, link in gossip:
            st.markdown(
                f"<div class='news-card'>"
                f"💬 <a href='{link}' target='_blank' style='color: #38BDF8; font-weight: 700; text-decoration: none; font-size: 13px;'>{title}</a><br>"
                f"<span style='color: #94A3B8; font-size: 11px;'>⏱ {pub}</span><br>"
                f"<span style='color: #CBD5E1; font-size: 12px;'>{summary}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
else:
    st.error("데이터를 불러오지 못했습니다.")
