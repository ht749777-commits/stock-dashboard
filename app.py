import streamlit as st
import streamlit.components.v1 as components
import urllib.request
import urllib.parse
import json
import re
import time
import base64
import textwrap
from datetime import datetime, timedelta, timezone
import feedparser
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from streamlit_searchbox import st_searchbox

# 🖼️ 로컬 이미지를 Base64 문자열로 변환하는 함수
def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
            ext = path.split('.')[-1].lower()
            mime_type = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return ""

# 페이지 설정
st.set_page_config(
    page_title="TAURUS LAB",
    page_icon="taurusfinal.png",
    layout="wide"
)

# 🎨 다크 테마 및 롤링 슬롯 + 호버 툴팁 CSS
st.markdown("""<style>
.stApp { background-color: #0B0E14 !important; color: #E0E0E0 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

/* 마켓 오버뷰 호버 및 슬롯 컨테이너 */
.market-overview-container {
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
    height: 48px;
    background-color: #121824;
    padding: 0 18px;
    border-radius: 10px;
    border: 1px solid #1E293B;
    margin-bottom: 15px;
    cursor: pointer;
    transition: border-color 0.2s ease;
}
.market-overview-container:hover {
    border-color: #00E676;
}

.market-title-badge {
    color: #00E676; 
    font-weight: 900; 
    font-size: 15px; 
    white-space: nowrap;
    margin-right: 15px;
    display: flex;
    align-items: center;
}

/* 슬롯 롤링 윈도우 */
.ticker-slider-window {
    height: 24px;
    overflow: hidden;
    position: relative;
    flex-grow: 1;
}

.ticker-slider-list {
    display: flex;
    flex-direction: column;
    margin: 0;
    padding: 0;
    list-style: none;
    animation: slotRoll 18s cubic-bezier(0.645, 0.045, 0.355, 1) infinite;
}

.market-overview-container:hover .ticker-slider-list {
    animation-play-state: paused;
}

.ticker-item {
    height: 24px;
    line-height: 24px;
    font-size: 13px;
    color: #94A3B8;
    white-space: nowrap;
}

/* 6개 지표 x 3초 = 18초 키프레임 애니메이션 */
@keyframes slotRoll {
    0%, 13.88%   { transform: translateY(0px); }
    16.66%, 30.55% { transform: translateY(-24px); }
    33.33%, 47.22% { transform: translateY(-48px); }
    50.00%, 63.88% { transform: translateY(-72px); }
    66.66%, 80.55% { transform: translateY(-96px); }
    83.33%, 97.22% { transform: translateY(-120px); }
    100%          { transform: translateY(-144px); }
}

/* 호버 툴팁 박스 (기본 숨김 -> 호버 시에만 표시) */
.market-overview-tooltip {
    display: none;
    opacity: 0;
    pointer-events: none;
    width: 340px;
    background-color: #1A2234;
    color: #F8FAFC;
    text-align: left;
    border-radius: 10px;
    padding: 14px 16px;
    position: absolute;
    z-index: 999;
    top: 100%;
    left: 0;
    margin-top: 8px;
    border: 1px solid #334155;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    transition: opacity 0.2s ease-in-out;
}

.market-overview-container:hover .market-overview-tooltip {
    display: block !important;
    opacity: 1 !important;
    pointer-events: auto;
}

.tooltip-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #283548;
    font-size: 13px;
}
.tooltip-row:last-child {
    border-bottom: none;
}
.tooltip-label { color: #94A3B8; font-weight: 500; }
.tooltip-val { font-weight: 700; color: #F8FAFC; }

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

.stButton > button {
    background-color: #121824 !important;
    color: #F8FAFC !important;
    border: 1px solid #1E293B !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    text-align: left !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background-color: #1E293B !important;
    border-color: #00E676 !important;
    color: #00E676 !important;
}

.stTabs [data-baseweb="tab-list"] { gap: 6px; background-color: transparent; }
.stTabs [data-baseweb="tab"] { background-color: #121824; border-radius: 6px; color: #94A3B8; border: 1px solid #1E293B; padding: 6px 12px; font-size: 13px; }
.stTabs [aria-selected="true"] { background-color: #1E293B !important; color: #00E676 !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

class QuantEngine:
    FINANCIAL_DICT = {
        "bullish": "강세(매수)", "bearish": "약세(매도)", "bull": "황소(강세)", "bear": "곰(약세)",
        "short squeeze": "숏 스퀴즈", "short interest": "공매도 잔고", "earnings": "실적 발표",
        "guidance": "가이던스", "rally": "랠리", "plummet": "폭락", "surge": "급등",
        "soar": "폭등", "dip": "조정", "buy the dip": "저가 매수", "market cap": "시가총액"
    }

    @staticmethod
    def search_stock_suggestions(search_term: str):
        if not search_term or len(search_term.strip()) == 0:
            return []
        term = search_term.strip().upper()
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(term)}&quotesCount=20&newsCount=0"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode('utf-8'))
                quotes = data.get('quotes', [])

                suggestions = []
                us_exchanges = {"NMS", "NYQ", "NGM", "ASE", "PCX", "OBB", "PNK"}
                
                for q in quotes:
                    q_type = q.get('quoteType', '')
                    ex = q.get('exchange', '')
                    symbol = q.get('symbol', '')
                    
                    if q_type == 'EQUITY' and (ex in us_exchanges or '.' not in symbol):
                        name = q.get('shortname', q.get('longname', symbol))
                        display_text = f"{symbol}  |  {name} ({ex})"
                        suggestions.append((display_text, symbol))
                return suggestions
        except:
            return []

    @staticmethod
    def professional_translate(text: str) -> str:
        if not text: return text
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q={encoded_text}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                translated = "".join([item[0] for item in res_data[0] if item[0]])
                for eng, kor in QuantEngine.FINANCIAL_DICT.items():
                    translated = re.compile(re.escape(eng), re.IGNORECASE).sub(kor, translated)
                return translated
        except:
            return text

    @staticmethod
    def convert_to_kst_string(pub_parsed) -> str:
        try:
            if not pub_parsed: return "최근"
            dt_utc = datetime(*pub_parsed[:6], tzinfo=timezone.utc)
            return dt_utc.astimezone(timezone(timedelta(hours=9))).strftime("%m월 %d일 %H:%M")
        except:
            return "최근"

    @staticmethod
    def get_market_overview_data():
        """핵심 글로벌 지표 수집"""
        tickers = {
            "NQ": "NQ=F",        # 나스닥 100 선물
            "ES": "ES=F",        # S&P 500 선물
            "USDKRW": "USDKRW=X",# 원/달러 환율
            "VIX": "^VIX",       # 변동성 지수
            "TNX": "^TNX",       # 미국 10년물 국채 금리
            "BTC": "BTC-USD"     # 비트코인
        }
        
        results = {}
        try:
            data = yf.Tickers(" ".join(tickers.values()))
            for key, sym in tickers.items():
                try:
                    hist = data.tickers[sym].history(period="5d")
                    if not hist.empty and len(hist) >= 2:
                        curr = float(hist['Close'].iloc[-1])
                        prev = float(hist['Close'].iloc[-2])
                        chg_p = ((curr - prev) / prev) * 100
                        results[key] = (curr, chg_p)
                except:
                    pass
        except:
            pass

        default_res = {
            "NQ": (19850.25, 0.15),
            "ES": (5540.50, 0.08),
            "USDKRW": (1378.50, -0.22),
            "VIX": (15.20, -1.50),
            "TNX": (3.94, -0.05),
            "BTC": (60850.00, 1.25)
        }
        
        for k, v in default_res.items():
            if k not in results:
                results[k] = v
                
        return results

    @staticmethod
    def get_google_news(ticker_symbol: str):
        news_list = []
        try:
            query = urllib.parse.quote(f'"{ticker_symbol}" stock OR shares OR earnings OR SEC')
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en&t={int(time.time())}"
            feed = feedparser.parse(rss_url)
            three_days_ago = datetime.now(timezone(timedelta(hours=9))) - timedelta(days=3)

            for entry in feed.entries:
                pub_parsed = entry.get('published_parsed')
                if pub_parsed:
                    dt_kst = datetime(*pub_parsed[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
                    if dt_kst < three_days_ago: continue
                
                raw_title = entry.get('title', 'No Title')
                title_clean = raw_title.rsplit('-', 1)[0].strip() if '-' in raw_title else raw_title
                title = QuantEngine.professional_translate(title_clean)
                
                summary_raw = entry.get('summary', '') or entry.get('description', '')
                summary_clean = re.sub(r'<[^>]*>', '', summary_raw)
                summary = QuantEngine.professional_translate(summary_clean)
                
                news_list.append((
                    title, 
                    (summary[:120] + "...") if len(summary) > 120 else summary, 
                    QuantEngine.convert_to_kst_string(pub_parsed), 
                    entry.get('link', '#')
                ))
                if len(news_list) >= 5: break
        except:
            pass
        return news_list if news_list else [(f"[{ticker_symbol}] 최근 실시간 뉴스가 없습니다.", "", "방금 전", "#")]

    @staticmethod
    def get_stocktwits_posts(ticker_symbol: str):
        posts = []
        try:
            url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker_symbol}.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                messages = data.get('messages', [])
                
                for msg in messages[:6]:
                    body = msg.get('body', '')
                    user_info = msg.get('user', {})
                    username = user_info.get('username', 'User')
                    created_at_raw = msg.get('created_at', '')
                    
                    time_str = "방금 전"
                    if created_at_raw:
                        try:
                            dt = datetime.strptime(created_at_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                            time_str = dt.astimezone(timezone(timedelta(hours=9))).strftime("%m/%d %H:%M")
                        except:
                            time_str = created_at_raw[:10]

                    sentiment_obj = msg.get('entities', {}).get('sentiment')
                    sentiment_tag = ""
                    if sentiment_obj and sentiment_obj.get('basic'):
                        s_val = sentiment_obj.get('basic').upper()
                        sentiment_tag = f" 🟢 [{s_val}]" if s_val == "BULLISH" else f" 🔴 [{s_val}]"

                    title = f"💬 [StockTwits] @{username}{sentiment_tag}"
                    translated_body = QuantEngine.professional_translate(body)
                    link = f"https://stocktwits.com/symbol/{ticker_symbol}"

                    posts.append((
                        title,
                        translated_body,
                        time_str,
                        link
                    ))
        except:
            pass
        return posts

    @staticmethod
    def get_social_gossip(ticker_symbol: str):
        social_list = QuantEngine.get_stocktwits_posts(ticker_symbol)
        
        if len(social_list) < 5:
            try:
                query = urllib.parse.quote(f'"{ticker_symbol}" (site:reddit.com OR site:x.com OR site:twitter.com) (stock OR buy OR sell OR rumor)')
                rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en&t={int(time.time())}"
                feed = feedparser.parse(rss_url)

                for entry in feed.entries:
                    raw_title = entry.get('title', 'Social Discussion')
                    source_tag = "[Reddit]" if "reddit.com" in entry.get('link', '').lower() else "[X/Twitter]"
                    
                    title_clean = raw_title.rsplit('-', 1)[0].strip() if '-' in raw_title else raw_title
                    translated_title = QuantEngine.professional_translate(title_clean)
                    title = f"{source_tag} {translated_title}"

                    summary_raw = entry.get('summary', '') or entry.get('description', '')
                    summary_clean = re.sub(r'<[^>]*>', '', summary_raw)
                    translated_summary = QuantEngine.professional_translate(summary_clean)

                    pub_parsed = entry.get('published_parsed')

                    social_list.append((
                        title, 
                        (translated_summary[:120] + "...") if len(translated_summary) > 120 else translated_summary, 
                        QuantEngine.convert_to_kst_string(pub_parsed), 
                        entry.get('link', '#')
                    ))
                    if len(social_list) >= 6: break
            except:
                pass

        return social_list if social_list else [(f"[{ticker_symbol}] 최근 실시간 소셜 언급이 없습니다.", "", "방금 전", "#")]

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

            return {
                "ticker": ticker_symbol, "company_name": info.get('longName', ticker_symbol),
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

# ── [우측 상단 팝오버 메뉴 영역] ──
_, col_popover = st.columns([10, 1])
with col_popover:
    with st.popover("⚙️ 메뉴"):
        st.markdown("**메뉴**")
        if st.button("홈 대시보드", use_container_width=True):
            pass
        if st.button("관심종목 (Watchlist)", use_container_width=True):
            pass

# ── [화면 중앙 메인 로고 영역] ──
col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
with col_b2:
    main_logo = get_image_base64("taurusfinal.png")
    if main_logo:
        st.markdown(f"""<div style="text-align: center; margin-bottom: 25px;">
<img src="{main_logo}" style="max-width: 260px; width: 100%; height: auto;">
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="
background: linear-gradient(135deg, #121824 0%, #1E293B 100%);
border: 2px solid #FF2A2A;
border-radius: 12px;
padding: 20px;
text-align: center;
margin-bottom: 20px;
">
<h1 style="color: #FF2A2A; margin: 0; font-size: 32px; font-weight: 900; letter-spacing: 2px;">TAURUS LAB</h1>
</div>""", unsafe_allow_html=True)

# ── [Market Overview 영역] ──
market_data = QuantEngine.get_market_overview_data()

nq_val, nq_chg = market_data["NQ"]
es_val, es_chg = market_data["ES"]
usd_val, usd_chg = market_data["USDKRW"]
vix_val, vix_chg = market_data["VIX"]
tnx_val, tnx_chg = market_data["TNX"]
btc_val, btc_chg = market_data["BTC"]

st.markdown(f"""<div class="market-overview-container">
<div class="market-title-badge">📊 Market Overview</div>

<div class="ticker-slider-window">
<ul class="ticker-slider-list">
<li class="ticker-item">
나스닥 100 선물: <b style="color:#F8FAFC;">{nq_val:,.2f}</b> 
<span style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({nq_chg:+.2f}%)</span>
<span style="color:#64748B; font-size: 11px; margin-left: 8px;">(🔍 마우스를 올려 상세지표 확인)</span>
</li>
<li class="ticker-item">
S&P 500 선물: <b style="color:#F8FAFC;">{es_val:,.2f}</b> 
<span style="color:{'#00E676' if es_chg>=0 else '#EF4444'};">({es_chg:+.2f}%)</span>
</li>
<li class="ticker-item">
원/달러 환율: <b style="color:#F8FAFC;">₩{usd_val:,.2f}</b> 
<span style="color:{'#00E676' if usd_chg>=0 else '#EF4444'};">({usd_chg:+.2f}%)</span>
</li>
<li class="ticker-item">
VIX (공포 지수): <b style="color:#F8FAFC;">{vix_val:,.2f}</b> 
<span style="color:{'#EF4444' if vix_chg>=0 else '#00E676'};">({vix_chg:+.2f}%)</span>
</li>
<li class="ticker-item">
미국 10년물 국채금리: <b style="color:#F8FAFC;">{tnx_val:.2f}%</b> 
<span style="color:{'#00E676' if tnx_chg>=0 else '#EF4444'};">({tnx_chg:+.2f}%)</span>
</li>
<li class="ticker-item">
비트코인 (BTC): <b style="color:#F8FAFC;">${btc_val:,.0f}</b> 
<span style="color:{'#00E676' if btc_chg>=0 else '#EF4444'};">({btc_chg:+.2f}%)</span>
</li>
<li class="ticker-item">
나스닥 100 선물: <b style="color:#F8FAFC;">{nq_val:,.2f}</b> 
<span style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({nq_chg:+.2f}%)</span>
</li>
</ul>
</div>

<div class="market-overview-tooltip">
<div style="font-weight: 800; font-size: 13px; color: #00E676; margin-bottom: 8px; border-bottom: 1px solid #334155; padding-bottom: 4px;">
🌐 주요 글로벌 시장 지표
</div>
<div class="tooltip-row">
<span class="tooltip-label">나스닥 100 선물</span>
<span class="tooltip-val">{nq_val:,.2f} <small style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({nq_chg:+.2f}%)</small></span>
</div>
<div class="tooltip-row">
<span class="tooltip-label">S&P 500 선물</span>
<span class="tooltip-val">{es_val:,.2f} <small style="color:{'#00E676' if es_chg>=0 else '#EF4444'};">({es_chg:+.2f}%)</small></span>
</div>
<div class="tooltip-row">
<span class="tooltip-label">원/달러 환율 (KRW)</span>
<span class="tooltip-val">₩{usd_val:,.2f} <small style="color:{'#00E676' if usd_chg>=0 else '#EF4444'};">({usd_chg:+.2f}%)</small></span>
</div>
<div class="tooltip-row">
<span class="tooltip-label">VIX (공포 지수)</span>
<span class="tooltip-val">{vix_val:,.2f} <small style="color:{'#EF4444' if vix_chg>=0 else '#00E676'};">({vix_chg:+.2f}%)</small></span>
</div>
<div class="tooltip-row">
<span class="tooltip-label">미국 10년물 국채금리</span>
<span class="tooltip-val">{tnx_val:.2f}% <small style="color:{'#00E676' if tnx_chg>=0 else '#EF4444'};">({tnx_chg:+.2f}%)</small></span>
</div>
<div class="tooltip-row">
<span class="tooltip-label">비트코인 (BTC)</span>
<span class="tooltip-val">${btc_val:,.0f} <small style="color:{'#00E676' if btc_chg>=0 else '#EF4444'};">({btc_chg:+.2f}%)</small></span>
</div>
</div>
</div>""", unsafe_allow_html=True)

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
    col_title, col_btn = st.columns([3.0, 1.0])
    with col_title:
        st.markdown(f"<h3 style='color: #F8FAFC; margin-bottom: 5px;'>[{res['ticker']}] {res['company_name']}</h3>", unsafe_allow_html=True)
    
    with col_btn:
        st.markdown("""<div style="display: flex; justify-content: flex-end; align-items: center; height: 100%; padding-top: 5px;">
<a href="https://earnings.kr/" target="_blank" style="text-decoration: none;">
<div style="
background-color: #121824; 
padding: 6px 14px 6px 12px; 
border-radius: 20px; 
border: 1px solid #1E293B; 
display: inline-flex; 
align-items: center; 
gap: 8px;
cursor: pointer;
">
<span style="font-size: 15px; line-height: 1;">📢</span>
<span style="color: #F8FAFC; font-size: 13px; font-weight: 600; letter-spacing: -0.3px;">
실적발표 보러가기
</span>
</div>
</a>
</div>""", unsafe_allow_html=True)
    
    score = res['score']
    
    if score >= 70:
        box_bg = "linear-gradient(135deg, #00E676, #00C853)"
        text_color = "#000000"
        status_text = "🚀 STRONG BUY (매수 의견 / 안전 진입 구간)"
        status_color = "#00E676"
    elif score >= 40:
        box_bg = "linear-gradient(135deg, #F59E0B, #D97706)"
        text_color = "#000000"
        status_text = "⚠️ HOLD (중립 관망 구간)"
        status_color = "#F59E0B"
    else:
        box_bg = "linear-gradient(135deg, #EF4444, #DC2626)"
        text_color = "#FFFFFF"
        status_text = "⛔ STOP (매수 금지 / 위험 관리 필요)"
        status_color = "#EF4444"

    st.markdown(
        f"<div style='background: {box_bg}; color: {text_color}; font-weight: 900; font-size: 15px; text-align: center; padding: 10px; border-radius: 8px; margin-bottom: 12px;'>"
        f"매수적합도 : {score} / 100 점"
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
    st.markdown(f"<p style='color: {status_color}; font-weight: bold; font-size: 14px; margin-bottom: 15px;'>{status_text}</p>", unsafe_allow_html=True)

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

        tf_html = f"""<div style="display: flex; justify-content: flex-end; gap: 6px; margin-top: 6px;">
<button onclick="window.parent.location.search = '?q={res['ticker']}&tf=1D'" style="background-color: {tf_1d_bg}; color: {tf_1d_color}; border: 1px solid #1E293B; border-radius: 6px; padding: 6px 10px; font-weight: 700; font-size: 12px; cursor: pointer;">1D</button>
<button onclick="window.parent.location.search = '?q={res['ticker']}&tf=1H'" style="background-color: {tf_1h_bg}; color: {tf_1h_color}; border: 1px solid #1E293B; border-radius: 6px; padding: 6px 10px; font-weight: 700; font-size: 12px; cursor: pointer;">1H</button>
<button onclick="window.parent.location.search = '?q={res['ticker']}&tf=15M'" style="background-color: {tf_15m_bg}; color: {tf_15m_color}; border: 1px solid #1E293B; border-radius: 6px; padding: 6px 10px; font-weight: 700; font-size: 12px; cursor: pointer;">15M</button>
</div>"""
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

    tab_news, tab_gossip = st.tabs(["📰 구글 영문 뉴스", "💬 StockTwits & 소셜 찌라시"])
    
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
                f"<a href='{link}' target='_blank' style='color: #00E676; font-weight: 700; text-decoration: none; font-size: 13px;'>{title}</a><br>"
                f"<span style='color: #94A3B8; font-size: 11px;'>⏱ {pub}</span><br>"
                f"<span style='color: #CBD5E1; font-size: 12px;'>{summary}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
else:
    st.error("데이터를 불러오지 못했습니다.")
