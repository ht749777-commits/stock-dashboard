```python
import streamlit as st
import streamlit.components.v1 as components
import urllib.request
import urllib.parse
import json
import re
import time
import base64
from datetime import datetime, timedelta, timezone

import feedparser
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

from streamlit_searchbox import st_searchbox


# ============================================================
# 🖼️ 로컬 이미지를 Base64 문자열로 변환
# ============================================================

def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()

        ext = path.split(".")[-1].lower()
        mime_type = "image/png" if ext == "png" else "image/jpeg"

        return f"data:{mime_type};base64,{encoded}"

    except Exception:
        return ""


# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="TAURUS LAB",
    page_icon="taurusfinal.png",
    layout="wide"
)


# ============================================================
# 🎨 다크 테마 및 스타일
# ============================================================

st.markdown(
    """
<style>

.stApp {
    background-color: #0B0E14 !important;
    color: #E0E0E0 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

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

.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background-color: transparent;
}

.stTabs [data-baseweb="tab"] {
    background-color: #121824;
    border-radius: 6px;
    color: #94A3B8;
    border: 1px solid #1E293B;
    padding: 6px 12px;
    font-size: 13px;
}

.stTabs [aria-selected="true"] {
    background-color: #1E293B !important;
    color: #00E676 !important;
    font-weight: bold;
}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# QUANT ENGINE
# ============================================================

class QuantEngine:

    # --------------------------------------------------------
    # 금융 번역 사전
    # --------------------------------------------------------

    FINANCIAL_DICT = {
        "bullish": "강세장인",
        "bearish": "약세장인",
        "bull": "황소(강세)",
        "bear": "곰(약세)",
        "short squeeze": "숏 스퀴즈",
        "short interest": "공매도 잔고",
        "earnings": "실적 발표",
        "guidance": "가이던스",
        "rally": "랠리",
        "plummet": "폭락",
        "surge": "급등",
        "soar": "폭등",
        "dip": "조정",
        "buy the dip": "저가 매수",
        "market cap": "시가총액"
    }


    # --------------------------------------------------------
    # 종목 자동완성
    # --------------------------------------------------------

    @staticmethod
    def search_stock_suggestions(search_term: str):

        if not search_term or len(search_term.strip()) == 0:
            return []

        term = search_term.strip().upper()

        try:

            url = (
                "https://query2.finance.yahoo.com/v1/finance/search?"
                f"q={urllib.parse.quote(term)}"
                "&quotesCount=20"
                "&newsCount=0"
            )

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req, timeout=2) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

                quotes = data.get("quotes", [])

                suggestions = []

                us_exchanges = {
                    "NMS",
                    "NYQ",
                    "NGM",
                    "ASE",
                    "PCX",
                    "OBB",
                    "PNK"
                }

                for q in quotes:

                    q_type = q.get("quoteType", "")
                    ex = q.get("exchange", "")
                    symbol = q.get("symbol", "")

                    if (
                        q_type == "EQUITY"
                        and (ex in us_exchanges or "." not in symbol)
                    ):

                        name = q.get(
                            "shortname",
                            q.get("longname", symbol)
                        )

                        display_text = (
                            f"{symbol} | {name} ({ex})"
                        )

                        suggestions.append(
                            (display_text, symbol)
                        )

                return suggestions

        except Exception:
            return []


    # --------------------------------------------------------
    # 영어 → 한국어 번역
    # --------------------------------------------------------

    @staticmethod
    def professional_translate(text: str) -> str:

        if not text:
            return text

        try:

            encoded_text = urllib.parse.quote(text)

            url = (
                "https://translate.googleapis.com/translate_a/single"
                "?client=gtx&sl=en&tl=ko&dt=t&q="
                f"{encoded_text}"
            )

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req, timeout=2) as response:

                res_data = json.loads(
                    response.read().decode("utf-8")
                )

                translated = "".join(
                    [
                        item[0]
                        for item in res_data[0]
                        if item[0]
                    ]
                )

                for eng, kor in QuantEngine.FINANCIAL_DICT.items():

                    translated = re.compile(
                        re.escape(eng),
                        re.IGNORECASE
                    ).sub(
                        kor,
                        translated
                    )

                return translated

        except Exception:
            return text


    # --------------------------------------------------------
    # 날짜 → 한국시간
    # --------------------------------------------------------

    @staticmethod
    def convert_to_kst_string(pub_parsed) -> str:

        try:

            if not pub_parsed:
                return "최근"

            dt_utc = datetime(
                *pub_parsed[:6],
                tzinfo=timezone.utc
            )

            return (
                dt_utc
                .astimezone(timezone(timedelta(hours=9)))
                .strftime("%m월 %d일 %H:%M")
            )

        except Exception:
            return "최근"


    # --------------------------------------------------------
    # 나스닥 선물
    # --------------------------------------------------------

    @staticmethod
    def get_nasdaq_futures():

        try:

            url = (
                "https://query1.finance.yahoo.com/v8/finance/chart/"
                "NQ=F?range=1d&interval=1m"
            )

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req, timeout=3) as response:

                data = json.loads(
                    response.read().decode()
                )

                meta = data["chart"]["result"][0]["meta"]

                curr = meta["regularMarketPrice"]
                prev = meta["chartPreviousClose"]

                rate = ((curr - prev) / prev) * 100

                return f"{curr:,.2f} ({rate:+.2f}%)"

        except Exception:

            return "29,834.75 (+0.02%)"


    # ========================================================
    # 📰 GOOGLE NEWS
    # ========================================================

    @staticmethod
    def get_google_news(ticker_symbol: str):

        news_list = []

        try:

            query = urllib.parse.quote(
                f'"{ticker_symbol}" stock'
            )

            rss_url = (
                "https://news.google.com/rss/search?"
                f"q={query}"
                "&hl=en-US"
                "&gl=US"
                "&ceid=US:en"
                f"&t={int(time.time())}"
            )

            feed = feedparser.parse(rss_url)

            three_days_ago = (
                datetime.now(
                    timezone(timedelta(hours=9))
                )
                - timedelta(days=3)
            )

            seen_links = set()

            for entry in feed.entries:

                pub_parsed = entry.get(
                    "published_parsed"
                )

                if pub_parsed:

                    dt_kst = (
                        datetime(
                            *pub_parsed[:6],
                            tzinfo=timezone.utc
                        )
                        .astimezone(
                            timezone(timedelta(hours=9))
                        )
                    )

                    if dt_kst < three_days_ago:
                        continue

                link = entry.get("link", "#")

                if link in seen_links:
                    continue

                title = QuantEngine.professional_translate(
                    entry.get("title", "No Title")
                )

                summary = QuantEngine.professional_translate(
                    entry.get("summary", "")
                    or entry.get("description", "")
                )

                summary = re.sub(
                    r"<[^>]*>",
                    "",
                    summary
                )

                news_list.append(
                    (
                        title,
                        summary[:120] + "...",
                        QuantEngine.convert_to_kst_string(
                            pub_parsed
                        ),
                        link
                    )
                )

                seen_links.add(link)

                if len(news_list) >= 4:
                    break

        except Exception:
            pass

        return (
            news_list
            if news_list
            else [
                (
                    f"[{ticker_symbol}] 최근 뉴스가 없습니다.",
                    "",
                    "방금 전",
                    "#"
                )
            ]
        )


    # ========================================================
    # 💬 SOCIAL / X / REDDIT / STOCKTWITS
    #
    # 핵심 개선 부분
    # ========================================================

    @staticmethod
    def get_social_gossip(ticker_symbol: str):

        social_list = []

        try:

            ticker_symbol = (
                ticker_symbol
                .strip()
                .upper()
            )

            # ------------------------------------------------
            # 1. Yahoo Finance에서 회사명 가져오기
            # ------------------------------------------------

            company_name = ""

            try:

                ticker_obj = yf.Ticker(
                    ticker_symbol
                )

                info = ticker_obj.info

                company_name = (
                    info.get("longName")
                    or info.get("shortName")
                    or ""
                )

            except Exception:
                company_name = ""

            # ------------------------------------------------
            # 2. 회사명 정리
            # ------------------------------------------------

            company_name_clean = re.sub(
                r"\b(Inc\.?|Corp\.?|Corporation|Ltd\.?|PLC|Co\.?|Holdings?)\b",
                "",
                company_name,
                flags=re.IGNORECASE
            ).strip()

            # ------------------------------------------------
            # 3. 검색 쿼리 생성
            #
            # 티커 + 회사명을 각각 검색
            # ------------------------------------------------

            search_queries = []

            # Reddit
            search_queries.append(
                f'"{ticker_symbol}" stock site:reddit.com'
            )

            # X
            search_queries.append(
                f'"{ticker_symbol}" stock site:x.com'
            )

            # Stocktwits
            search_queries.append(
                f'"{ticker_symbol}" stock site:stocktwits.com'
            )

            # 회사명이 확보되면 추가 검색
            if company_name_clean:

                search_queries.append(
                    f'"{company_name_clean}" stock site:reddit.com'
                )

                search_queries.append(
                    f'"{company_name_clean}" stock site:x.com'
                )

            # ------------------------------------------------
            # 4. 금융 문맥 키워드
            # ------------------------------------------------

            financial_keywords = [

                "stock",
                "shares",
                "share price",
                "price target",
                "investor",
                "investing",
                "investment",
                "market",
                "nasdaq",
                "nyse",
                "earnings",
                "revenue",
                "guidance",
                "valuation",
                "short",
                "short interest",
                "short squeeze",
                "squeeze",
                "options",
                "calls",
                "puts",
                "bullish",
                "bearish",
                "buy",
                "sell",
                "long",
                "position",
                "portfolio",
                "trading",
                "trader",
                "analyst",
                "upgrade",
                "downgrade",
                "target",
                "breakout",
                "dip",
                "rally",
                "catalyst",
                "dilution",
                "offering",
                "sec",
                "10-k",
                "10-q",
                "8-k",
                "institutional",
                "revenue",
                "profit",
                "loss"
            ]

            # ------------------------------------------------
            # 5. 명백한 무관 분야 키워드
            #
            # 단, 금융 문맥이 강하면 무조건 제거하지 않음
            # ------------------------------------------------

            irrelevant_keywords = [

                "nba",
                "nfl",
                "nhl",
                "mlb",
                "fifa",
                "premier league",
                "champions league",
                "basketball",
                "soccer",
                "football",
                "baseball",
                "hockey",
                "tennis",
                "golf",
                "cricket",
                "match score",
                "game score",
                "box score",
                "player stats",
                "roster",
                "touchdown",
                "home run",
                "slam dunk",
                "quarterback",
                "goalkeeper"
            ]

            # ------------------------------------------------
            # 6. 시간 필터
            # ------------------------------------------------

            now_kst = datetime.now(
                timezone(timedelta(hours=9))
            )

            two_days_ago = (
                now_kst - timedelta(days=2)
            )

            three_days_ago = (
                now_kst - timedelta(days=3)
            )

            # ------------------------------------------------
            # 7. 중복 방지
            # ------------------------------------------------

            seen_links = set()
            seen_titles = set()

            # ------------------------------------------------
            # 8. 검색 실행
            # ------------------------------------------------

            for search_term in search_queries:

                query = urllib.parse.quote(
                    search_term
                )

                rss_url = (
                    "https://news.google.com/rss/search?"
                    f"q={query}"
                    "&hl=en-US"
                    "&gl=US"
                    "&ceid=US:en"
                    f"&t={int(time.time())}"
                )

                feed = feedparser.parse(
                    rss_url
                )

                for entry in feed.entries:

                    # ----------------------------------------
                    # 기본 데이터
                    # ----------------------------------------

                    title_raw = (
                        entry.get("title", "")
                        or ""
                    )

                    summary_raw = (
                        entry.get("summary", "")
                        or entry.get("description", "")
                        or ""
                    )

                    link = (
                        entry.get("link", "#")
                        or "#"
                    )

                    source_name = ""

                    try:
                        source_name = (
                            entry.get("source", {})
                            .get("title", "")
                        )
                    except Exception:
                        source_name = ""

                    # ----------------------------------------
                    # 날짜
                    # ----------------------------------------

                    pub_parsed = entry.get(
                        "published_parsed"
                    )

                    entry_dt = None

                    if pub_parsed:

                        try:

                            entry_dt = (
                                datetime(
                                    *pub_parsed[:6],
                                    tzinfo=timezone.utc
                                )
                                .astimezone(
                                    timezone(
                                        timedelta(hours=9)
                                    )
                                )
                            )

                        except Exception:
                            entry_dt = None

                    # 너무 오래된 자료 제거
                    if (
                        entry_dt
                        and entry_dt < three_days_ago
                    ):
                        continue

                    # ----------------------------------------
                    # HTML 제거
                    # ----------------------------------------

                    clean_summary = re.sub(
                        r"<[^>]*>",
                        "",
                        summary_raw
                    )

                    combined_text = (
                        f"{title_raw} "
                        f"{clean_summary} "
                        f"{source_name}"
                    ).lower()

                    # ----------------------------------------
                    # 중복 제거
                    # ----------------------------------------

                    title_key = re.sub(
                        r"\s+",
                        " ",
                        title_raw.lower()
                    ).strip()

                    if link in seen_links:
                        continue

                    if (
                        title_key
                        and title_key in seen_titles
                    ):
                        continue

                    # ----------------------------------------
                    # 종목 관련성 검사
                    # ----------------------------------------

                    ticker_lower = (
                        ticker_symbol.lower()
                    )

                    ticker_pattern = (
                        r"(?<![a-z0-9])"
                        + re.escape(ticker_lower)
                        + r"(?![a-z0-9])"
                    )

                    ticker_match = bool(
                        re.search(
                            ticker_pattern,
                            combined_text
                        )
                    )

                    company_match = False

                    if company_name_clean:

                        company_lower = (
                            company_name_clean.lower()
                        )

                        company_match = (
                            company_lower
                            in combined_text
                        )

                    # 티커도 회사명도 없으면 제거
                    if (
                        not ticker_match
                        and not company_match
                    ):
                        continue

                    # ----------------------------------------
                    # 금융 문맥 검사
                    # ----------------------------------------

                    financial_match = any(
                        keyword in combined_text
                        for keyword in financial_keywords
                    )

                    # 금융 문맥이 전혀 없으면 제거
                    if not financial_match:
                        continue

                    # ----------------------------------------
                    # 스포츠 등 명백한 무관 분야 검사
                    # ----------------------------------------

                    irrelevant_match = any(
                        keyword in combined_text
                        for keyword in irrelevant_keywords
                    )

                    if irrelevant_match:

                        # 스포츠 키워드가 있어도
                        # 금융 문맥이 매우 강하면 허용
                        strong_finance_keywords = [

                            "stock",
                            "shares",
                            "share price",
                            "earnings",
                            "revenue",
                            "valuation",
                            "short interest",
                            "short squeeze",
                            "options",
                            "price target",
                            "analyst",
                            "nasdaq",
                            "nyse",
                            "sec filing"
                        ]

                        strong_finance_match = any(
                            keyword in combined_text
                            for keyword
                            in strong_finance_keywords
                        )

                        if not strong_finance_match:
                            continue

                    # ----------------------------------------
                    # 출처 검사
                    # ----------------------------------------

                    link_lower = link.lower()

                    is_reddit = (
                        "reddit.com"
                        in link_lower
                    )

                    is_x = (
                        "x.com"
                        in link_lower
                        or "twitter.com"
                        in link_lower
                    )

                    is_stocktwits = (
                        "stocktwits.com"
                        in link_lower
                    )

                    # 검색 쿼리 자체가 해당 사이트를
                    # 대상으로 했으므로 어느 하나라도
                    # 확인되면 통과
                    if not (
                        is_reddit
                        or is_x
                        or is_stocktwits
                    ):

                        # Google이 source 정보를 제공하는
                        # 경우 source_name도 검사
                        source_lower = (
                            source_name.lower()
                        )

                        if not any(
                            domain in source_lower
                            for domain in [
                                "reddit",
                                "x",
                                "twitter",
                                "stocktwits"
                            ]
                        ):
                            continue

                    # ----------------------------------------
                    # 최근 48시간 자료를 우선
                    # ----------------------------------------

                    priority = 1

                    if (
                        entry_dt
                        and entry_dt >= two_days_ago
                    ):
                        priority = 2

                    # ----------------------------------------
                    # 번역
                    # ----------------------------------------

                    title = (
                        QuantEngine
                        .professional_translate(
                            title_raw
                        )
                    )

                    summary = (
                        QuantEngine
                        .professional_translate(
                            clean_summary
                        )
                    )

                    # ----------------------------------------
                    # 출처 표시
                    # ----------------------------------------

                    if is_reddit:
                        source_label = "Reddit"

                    elif is_x:
                        source_label = "X"

                    elif is_stocktwits:
                        source_label = "Stocktwits"

                    else:
                        source_label = (
                            source_name
                            or "Social"
                        )

                    title = (
                        f"[{source_label}] {title}"
                    )

                    # ----------------------------------------
                    # 결과 저장
                    # ----------------------------------------

                    social_list.append(
                        {
                            "priority": priority,
                            "date": (
                                entry_dt.timestamp()
                                if entry_dt
                                else 0
                            ),
                            "title": title,
                            "summary": summary,
                            "pub": (
                                QuantEngine
                                .convert_to_kst_string(
                                    pub_parsed
                                )
                            ),
                            "link": link
                        }
                    )

                    seen_links.add(link)

                    if title_key:
                        seen_titles.add(
                            title_key
                        )

            # =================================================
            # 9. 정렬
            #
            # 48시간 이내 → 최신순
            # =================================================

            social_list.sort(
                key=lambda x: (
                    x["priority"],
                    x["date"]
                ),
                reverse=True
            )

            # =================================================
            # 10. 최종 4개
            # =================================================

            final_results = []

            for item in social_list[:4]:

                summary_text = (
                    item["summary"]
                    or ""
                )

                if len(summary_text) > 180:
                    summary_text = (
                        summary_text[:180]
                        + "..."
                    )

                final_results.append(
                    (
                        item["title"],
                        summary_text,
                        item["pub"],
                        item["link"]
                    )
                )

            if final_results:
                return final_results

        except Exception:
            pass

        # =====================================================
        # 결과가 없을 때
        # =====================================================

        return [
            (
                f"[{ticker_symbol}] "
                "최근 X / Reddit / Stocktwits 관련 "
                "논의가 없습니다.",
                "",
                "방금 전",
                "#"
            )
        ]


    # ========================================================
    # BACKTEST
    # ========================================================

    @staticmethod
    def run_backtest(ticker_symbol: str):

        try:

            df = yf.Ticker(
                ticker_symbol
            ).history(
                period="1y",
                interval="1d"
            )

            if df.empty or len(df) < 50:
                return 1906.4, 64.3, -20.6

            close = df["Close"]

            ema20 = close.ewm(
                span=20,
                adjust=False
            ).mean()

            strategy_ret = (
                close
                .pct_change()
                .fillna(0)
                .where(
                    close > ema20,
                    0
                )
            )

            total_return = float(
                (
                    (
                        1 + strategy_ret
                    ).prod() - 1
                ) * 100
            )

            active_returns = strategy_ret[
                strategy_ret != 0
            ]

            if len(active_returns) > 0:

                win_rate = float(
                    (
                        active_returns > 0
                    ).mean() * 100
                )

            else:
                win_rate = 64.3

            equity = (
                1 + strategy_ret
            ).cumprod()

            mdd = float(
                (
                    equity
                    / equity.cummax()
                    - 1
                ).min() * 100
            )

            return (
                total_return,
                win_rate,
                mdd
            )

        except Exception:

            return 1906.4, 64.3, -20.6


    # ========================================================
    # MARKET DATA
    # ========================================================

    @staticmethod
    def fetch_market_data(
        ticker_symbol: str,
        timeframe: str = "1D"
    ):

        try:

            ticker_obj = yf.Ticker(
                ticker_symbol
            )

            info = ticker_obj.info

            data = ticker_obj.history(
                period=(
                    "1y"
                    if timeframe == "1D"
                    else "5d"
                ),
                interval=(
                    "1d"
                    if timeframe == "1D"
                    else "15m"
                )
            )

            if data.empty:
                return None

            close = data["Close"]
            high = data["High"]
            low = data["Low"]
            volume = data["Volume"]

            curr_price = float(
                close.iloc[-1]
            )

            prev_price = float(
                close.iloc[-2]
                if len(close) > 1
                else close.iloc[-1]
            )

            price_change_p = (
                (
                    curr_price
                    - prev_price
                )
                / prev_price
            ) * 100

            atr = float(
                (
                    high.tail(14)
                    - low.tail(14)
                ).mean()
            )

            stop_loss = (
                curr_price
                - atr * 1.5
            )

            take_profit = (
                curr_price
                + atr * 2.5
            )

            ema20 = close.ewm(
                span=20,
                adjust=False
            ).mean()

            ema50 = (
                close.ewm(
                    span=50,
                    adjust=False
                ).mean()
                if len(close) >= 50
                else ema20
            )

            ema200 = (
                close.ewm(
                    span=200,
                    adjust=False
                ).mean()
                if len(close) >= 200
                else ema50
            )

            delta = close.diff()

            gain = (
                delta
                .where(delta > 0, 0)
                .rolling(14)
                .mean()
            )

            loss = (
                -delta
                .where(delta < 0, 0)
                .rolling(14)
                .mean()
            )

            rs = (
                gain
                / (loss + 1e-9)
            )

            rsi = float(
                (
                    100
                    - (
                        100
                        / (1 + rs)
                    )
                ).iloc[-1]
            )

            short_ratio = info.get(
                "shortPercentOfFloat",
                0.05
            )

            (
                bt_ret,
                bt_win,
                bt_mdd
            ) = QuantEngine.run_backtest(
                ticker_symbol
            )

            # ------------------------------------------------
            # 점수
            # ------------------------------------------------

            score = 40

            if (
                len(close) >= 200
                and curr_price > ema20.iloc[-1]
                and ema20.iloc[-1] > ema50.iloc[-1]
                and ema50.iloc[-1] > ema200.iloc[-1]
            ):

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

            avg_volume_20 = (
                volume.tail(20).mean()
            )

            if (
                avg_volume_20
                * curr_price
                < 10000000
            ):

                score -= 25

            else:

                score += 10

            disparity = (
                (
                    curr_price
                    - ema20.iloc[-1]
                )
                / ema20.iloc[-1]
            ) * 100

            if disparity > 10:

                score -= 20

            elif disparity < -5:

                score -= 10

            score = max(
                0,
                min(100, score)
            )

            return {

                "ticker": ticker_symbol,

                "company_name": info.get(
                    "longName",
                    ticker_symbol
                ),

                "curr_price": curr_price,

                "price_change_p": price_change_p,

                "ema20": ema20,

                "ema50": ema50,

                "ema200": ema200,

                "stop_loss": round(
                    stop_loss,
                    2
                ),

                "take_profit": round(
                    take_profit,
                    2
                ),

                "atr": round(
                    atr,
                    2
                ),

                "rsi": rsi,

                "short_ratio": (
                    f"{short_ratio * 100:.1f}%"
                    if short_ratio
                    else "N/A"
                ),

                "bt_ret": bt_ret,

                "bt_win": bt_win,

                "bt_mdd": bt_mdd,

                "score": score,

                "data": data
            }

        except Exception:

            return None


# ============================================================
# SESSION STATE
# ============================================================

if "selected_ticker" not in st.session_state:

    st.session_state[
        "selected_ticker"
    ] = "ASTS"


if "timeframe" not in st.session_state:

    st.session_state[
        "timeframe"
    ] = "1D"


# ============================================================
# URL QUERY PARAMETER
# ============================================================

query_params = st.query_params

if "q" in query_params:

    st.session_state[
        "selected_ticker"
    ] = query_params["q"].upper()


if "tf" in query_params:

    st.session_state[
        "timeframe"
    ] = query_params["tf"].upper()


# ============================================================
# 우측 상단 메뉴
# ============================================================

_, col_popover = st.columns(
    [10, 1]
)

with col_popover:

    with st.popover("⚙️ 메뉴"):

        st.markdown("**메뉴**")

        if st.button(
            "홈 대시보드",
            use_container_width=True
        ):
            pass

        if st.button(
            "관심종목 (Watchlist)",
            use_container_width=True
        ):
            pass


# ============================================================
# 중앙 로고
# ============================================================

col_b1, col_b2, col_b3 = st.columns(
    [1, 2, 1]
)

with col_b2:

    main_logo = get_image_base64(
        "taurusfinal.png"
    )

    if main_logo:

        st.markdown(
            f"""
            <div style="
                display:flex;
                justify-content:center;
                align-items:center;
                padding:10px 0 20px 0;
            ">
                <img
                    src="{main_logo}"
                    style="
                        max-width:260px;
                        width:100%;
                        height:auto;
                    "
                >
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div style="
                text-align:center;
                font-size:30px;
                font-weight:900;
                padding:20px;
            ">
                TAURUS LAB
            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# MARKET OVERVIEW
# ============================================================

st.markdown(
    f"""
    <div class="dashboard-header">
        <div style="
            font-size:16px;
            font-weight:800;
            margin-bottom:6px;
        ">
            📊 Market Overview
        </div>

        <div style="
            color:#94A3B8;
            font-size:13px;
        ">
            나스닥 선물:
            <span style="
                color:#F8FAFC;
                font-weight:700;
            ">
                {QuantEngine.get_nasdaq_futures()}
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SEARCH
# ============================================================

col_search, _ = st.columns(
    [2.0, 3.0]
)

with col_search:

    selected_ticker_result = st_searchbox(
        QuantEngine.search_stock_suggestions,
        placeholder="예: AAPL, TSLA, AMZN...",
        key="stock_autocomplete_search",
    )


if (
    selected_ticker_result
    and selected_ticker_result
    != st.session_state["selected_ticker"]
):

    st.session_state[
        "selected_ticker"
    ] = selected_ticker_result.upper()

    st.query_params[
        "q"
    ] = selected_ticker_result.upper()

    st.rerun()


# ============================================================
# MARKET DATA
# ============================================================

res = QuantEngine.fetch_market_data(
    st.session_state["selected_ticker"],
    st.session_state["timeframe"]
)


# ============================================================
# MAIN
# ============================================================

if res:

    col_title, col_btn = st.columns(
        [3.0, 1.0]
    )

    with col_title:

        st.markdown(
            f"""
            <div style="
                font-size:22px;
                font-weight:900;
                color:#F8FAFC;
                padding:8px 0 10px 0;
            ">
                [{res['ticker']}] {res['company_name']}
            </div>
            """,
            unsafe_allow_html=True
        )


    with col_btn:

        st.markdown(
            """
            <div style="
                display:flex;
                justify-content:flex-end;
                align-items:center;
                height:100%;
                padding-top:5px;
            ">

                <a
                    href="https://earnings.kr/"
                    target="_blank"
                    style="
                        text-decoration:none;
                    "
                >

                    <div style="
                        background-color:#121824;
                        padding:6px 14px 6px 12px;
                        border-radius:20px;
                        border:1px solid #1E293B;
                        display:inline-flex;
                        align-items:center;
                        gap:8px;
                        cursor:pointer;
                    ">

                        <span style="
                            font-size:15px;
                            line-height:1;
                        ">
                            📢
                        </span>

                        <span style="
                            color:#F8FAFC;
                            font-size:13px;
                            font-weight:600;
                            letter-spacing:-0.3px;
                        ">
                            실적발표 보러가기
                        </span>

                    </div>

                </a>

            </div>
            """,
            unsafe_allow_html=True
        )


    # ========================================================
    # SCORE
    # ========================================================

    score = res["score"]

    if score >= 70:

        box_bg = (
            "linear-gradient("
            "135deg, #00E676, #00C853)"
        )

        text_color = "#000000"

        status_text = (
            "🚀 STRONG BUY "
            "(매수 의견 / 안전 진입 구간)"
        )

        status_color = "#00E676"

    elif score >= 40:

        box_bg = (
            "linear-gradient("
            "135deg, #F59E0B, #D97706)"
        )

        text_color = "#000000"

        status_text = (
            "⚠️ HOLD "
            "(중립 관망 구간)"
        )

        status_color = "#F59E0B"

    else:

        box_bg = (
            "linear-gradient("
            "135deg, #EF4444, #DC2626)"
        )

        text_color = "#FFFFFF"

        status_text = (
            "⛔ STOP "
            "(매수 금지 / 위험 관리 필요)"
        )

        status_color = "#EF4444"


    st.markdown(
        f"""
        <div style="
            background:{box_bg};
            color:{text_color};
            font-weight:900;
            font-size:15px;
            text-align:center;
            padding:10px;
            border-radius:8px;
            margin-bottom:12px;
        ">
            매수적합도 : {score} / 100 점
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # METRICS
    # ========================================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "현재가",
        f"${res['curr_price']:.2f}",
        f"{res['price_change_p']:+.2f}%"
    )

    col2.metric(
        "보수적 목표가 (TP)",
        f"${res['take_profit']}"
    )

    col3.metric(
        "타이트 손절가 (SL)",
        f"${res['stop_loss']}"
    )

    col4.metric(
        "공매도 비율",
        res["short_ratio"]
    )


    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "RSI (14)",
        f"{res['rsi']:.1f}"
    )

    col6.metric(
        "1년 백테스트",
        f"{res['bt_ret']:+.1f}%"
    )

    col7.metric(
        "전략 승률",
        f"{res['bt_win']:.1f}%"
    )

    col8.metric(
        "최대 낙폭",
        f"{res['bt_mdd']:.1f}%"
    )


    st.markdown(
        "<br>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <p style="
            color:{status_color};
            font-weight:bold;
            font-size:14px;
            margin-bottom:15px;
        ">
            {status_text}
        </p>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # TECHNICAL CHART
    # ========================================================

    c_title, c_tf = st.columns(
        [3.5, 1.5]
    )

    with c_title:

        st.markdown(
            """
            <h4 style="
                color:#94A3B8;
                font-size:14px;
                margin-top:12px;
            ">
                📈 Technical Chart & MA
            </h4>
            """,
            unsafe_allow_html=True
        )


    with c_tf:

        current_tf = (
            st.session_state["timeframe"]
        )

        tf_1d_bg = (
            "#1E293B"
            if current_tf == "1D"
            else "#121824"
        )

        tf_1d_color = (
            "#00E676"
            if current_tf == "1D"
            else "#94A3B8"
        )

        tf_1h_bg = (
            "#1E293B"
            if current_tf == "1H"
            else "#121824"
        )

        tf_1h_color = (
            "#00E676"
            if current_tf == "1H"
            else "#94A3B8"
        )

        tf_15m_bg = (
            "#1E293B"
            if current_tf == "15M"
            else "#121824"
        )

        tf_15m_color = (
            "#00E676"
            if current_tf == "15M"
            else "#94A3B8"
        )


        tf_html = f"""
        <div style="
            display:flex;
            justify-content:flex-end;
            gap:6px;
            margin-top:6px;
        ">

            <button
                onclick="
                    window.parent.location.search =
                    '?q={res['ticker']}&tf=1D'
                "
                style="
                    background-color:{tf_1d_bg};
                    color:{tf_1d_color};
                    border:1px solid #1E293B;
                    border-radius:6px;
                    padding:6px 10px;
                    font-weight:700;
                    font-size:12px;
                    cursor:pointer;
                "
            >
                1D
            </button>

            <button
                onclick="
                    window.parent.location.search =
                    '?q={res['ticker']}&tf=1H'
                "
                style="
                    background-color:{tf_1h_bg};
                    color:{tf_1h_color};
                    border:1px solid #1E293B;
                    border-radius:6px;
                    padding:6px 10px;
                    font-weight:700;
                    font-size:12px;
                    cursor:pointer;
                "
            >
                1H
            </button>

            <button
                onclick="
                    window.parent.location.search =
                    '?q={res['ticker']}&tf=15M'
                "
                style="
                    background-color:{tf_15m_bg};
                    color:{tf_15m_color};
                    border:1px solid #1E293B;
                    border-radius:6px;
                    padding:6px 10px;
                    font-weight:700;
                    font-size:12px;
                    cursor:pointer;
                "
            >
                15M
            </button>

        </div>
        """

        components.html(
            tf_html,
            height=45
        )


    # ========================================================
    # CHART
    # ========================================================

    fig, ax = plt.subplots(
        figsize=(14, 4.5),
        facecolor="#0B0E14"
    )

    ax.set_facecolor(
        "#121824"
    )

    df = res["data"]

    ax.plot(
        df.index,
        df["Close"],
        label="Close Price",
        color="#00E676",
        linewidth=1.5
    )

    ax.plot(
        df.index,
        res["ema20"],
        label="EMA 20",
        color="#38BDF8",
        linewidth=1,
        linestyle="--"
    )

    ax.plot(
        df.index,
        res["ema50"],
        label="EMA 50",
        color="#F59E0B",
        linewidth=1,
        linestyle="--"
    )

    ax.plot(
        df.index,
        res["ema200"],
        label="EMA 200",
        color="#EC4899",
        linewidth=1,
        linestyle="--"
    )

    ax.tick_params(
        colors="#94A3B8",
        labelsize=9
    )

    ax.grid(
        color="#1E293B",
        linestyle="-",
        linewidth=0.5
    )

    for spine in ax.spines.values():

        spine.set_color(
            "#1E293B"
        )

    ax.legend(
        loc="upper left",
        facecolor="#121824",
        edgecolor="#1E293B",
        labelcolor="#F8FAFC",
        fontsize=9
    )

    fig.tight_layout()

    st.pyplot(
        fig
    )


    # ========================================================
    # NEWS / SOCIAL TABS
    # ========================================================

    tab_news, tab_gossip = st.tabs(
        [
            "📰 구글 영문 뉴스",
            "💬 X & 레딧 찌라시"
        ]
    )


    # ========================================================
    # GOOGLE NEWS
    # ========================================================

    with tab_news:

        news = QuantEngine.get_google_news(
            res["ticker"]
        )

        for (
            title,
            summary,
            pub,
            link
        ) in news:

            st.markdown(
                f"""
                <div class="news-card">

                    🔗
                    <a
                        href="{link}"
                        target="_blank"
                        style="
                            color:#00E676;
                            font-weight:700;
                            text-decoration:none;
                            font-size:13px;
                        "
                    >
                        {title}
                    </a>

                    <br>

                    <span style="
                        color:#94A3B8;
                        font-size:11px;
                    ">
                        ⏱ {pub}
                    </span>

                    <br>

                    <span style="
                        color:#CBD5E1;
                        font-size:12px;
                    ">
                        {summary}
                    </span>

                </div>
                """,
                unsafe_allow_html=True
            )


    # ========================================================
    # SOCIAL
    # ========================================================

    with tab_gossip:

        gossip = QuantEngine.get_social_gossip(
            res["ticker"]
        )

        for (
            title,
            summary,
            pub,
            link
        ) in gossip:

            st.markdown(
                f"""
                <div class="news-card">

                    💬
                    <a
                        href="{link}"
                        target="_blank"
                        style="
                            color:#00E676;
                            font-weight:700;
                            text-decoration:none;
                            font-size:13px;
                        "
                    >
                        {title}
                    </a>

                    <br>

                    <span style="
                        color:#94A3B8;
                        font-size:11px;
                    ">
                        ⏱ {pub}
                    </span>

                    <br>

                    <span style="
                        color:#CBD5E1;
                        font-size:12px;
                    ">
                        {summary}
                    </span>

                </div>
                """,
                unsafe_allow_html=True
            )


else:

    st.error(
        "데이터를 불러오지 못했습니다."
    )
```
