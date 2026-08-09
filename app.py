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


# =========================================================
# 기본 설정
# =========================================================

KST = timezone(timedelta(hours=9))


# =========================================================
# 로컬 이미지 Base64
# =========================================================

def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()

        ext = path.split(".")[-1].lower()

        if ext == "png":
            mime_type = "image/png"
        elif ext in ["jpg", "jpeg"]:
            mime_type = "image/jpeg"
        else:
            mime_type = "image/png"

        return f"data:{mime_type};base64,{encoded}"

    except Exception:
        return ""


# =========================================================
# 페이지 설정
# =========================================================

st.set_page_config(
    page_title="TAURUS LAB",
    page_icon="taurusfinal.png",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #0B0E14 !important;
        color: #E0E0E0 !important;
        font-family: -apple-system, BlinkMacSystemFont,
                     "Segoe UI", Roboto, sans-serif;
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


# =========================================================
# Quant Engine
# =========================================================

class QuantEngine:

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


    # =====================================================
    # 종목 검색
    # =====================================================

    @staticmethod
    def search_stock_suggestions(search_term: str):

        if not search_term or len(search_term.strip()) == 0:
            return []

        term = search_term.strip().upper()

        try:

            url = (
                "https://query2.finance.yahoo.com/v1/finance/search"
                f"?q={urllib.parse.quote(term)}"
                "&quotesCount=20"
                "&newsCount=0"
            )

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req, timeout=3) as response:

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
                exchange = q.get("exchange", "")
                symbol = q.get("symbol", "")

                if (
                    q_type == "EQUITY"
                    and (
                        exchange in us_exchanges
                        or "." not in symbol
                    )
                ):

                    name = q.get(
                        "shortname",
                        q.get(
                            "longname",
                            symbol
                        )
                    )

                    display_text = (
                        f"{symbol} | "
                        f"{name} ({exchange})"
                    )

                    suggestions.append(
                        (
                            display_text,
                            symbol
                        )
                    )

            return suggestions

        except Exception:
            return []


    # =====================================================
    # 번역
    # =====================================================

    @staticmethod
    def professional_translate(text: str):

        if not text:
            return text

        try:

            encoded_text = urllib.parse.quote(text)

            url = (
                "https://translate.googleapis.com/"
                "translate_a/single"
                "?client=gtx"
                "&sl=en"
                "&tl=ko"
                "&dt=t"
                f"&q={encoded_text}"
            )

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(
                req,
                timeout=3
            ) as response:

                res_data = json.loads(
                    response.read().decode()
                )

            translated = "".join(
                item[0]
                for item in res_data[0]
                if item[0]
            )

            for eng, kor in QuantEngine.FINANCIAL_DICT.items():

                translated = re.compile(
                    re.escape(eng),
                    re.IGNORECASE
                ).sub(kor, translated)

            return translated

        except Exception:

            return text


    # =====================================================
    # 날짜 변환
    # =====================================================

    @staticmethod
    def convert_to_kst_string(pub_parsed):

        try:

            if not pub_parsed:
                return "최근"

            dt_utc = datetime(
                *pub_parsed[:6],
                tzinfo=timezone.utc
            )

            return (
                dt_utc
                .astimezone(KST)
                .strftime("%m월 %d일 %H:%M")
            )

        except Exception:

            return "최근"


    # =====================================================
    # 나스닥 선물
    # =====================================================

    @staticmethod
    def get_nasdaq_futures():

        try:

            url = (
                "https://query1.finance.yahoo.com/"
                "v8/finance/chart/NQ=F"
                "?range=1d&interval=1m"
            )

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(
                req,
                timeout=3
            ) as response:

                data = json.loads(
                    response.read().decode()
                )

            meta = data["chart"]["result"][0]["meta"]

            curr = meta["regularMarketPrice"]
            prev = meta["chartPreviousClose"]

            rate = (
                (curr - prev)
                / prev
                * 100
            )

            return f"{curr:,.2f} ({rate:+.2f}%)"

        except Exception:

            return "데이터 없음"


    # =====================================================
    # 회사 정보 가져오기
    # =====================================================

    @staticmethod
    def get_company_name(ticker_symbol):

        try:

            ticker = yf.Ticker(ticker_symbol)

            info = ticker.info

            company_name = (
                info.get("longName")
                or info.get("shortName")
                or ticker_symbol
            )

            return company_name

        except Exception:

            return ticker_symbol


    # =====================================================
    # Google News
    # =====================================================

    @staticmethod
    def get_google_news(ticker_symbol):

        news_list = []

        try:

            company_name = (
                QuantEngine
                .get_company_name(ticker_symbol)
            )

            query_string = (
                f'"{ticker_symbol}" '
                f'"{company_name}" stock'
            )

            query = urllib.parse.quote(
                query_string
            )

            rss_url = (
                "https://news.google.com/rss/search"
                f"?q={query}"
                "&hl=en-US"
                "&gl=US"
                "&ceid=US:en"
                f"&t={int(time.time())}"
            )

            feed = feedparser.parse(rss_url)

            three_days_ago = (
                datetime.now(KST)
                - timedelta(days=3)
            )

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
                        .astimezone(KST)
                    )

                    if dt_kst < three_days_ago:
                        continue

                title_raw = entry.get(
                    "title",
                    ""
                )

                summary_raw = (
                    entry.get("summary", "")
                    or entry.get(
                        "description",
                        ""
                    )
                )

                raw_text = (
                    title_raw
                    + " "
                    + summary_raw
                )

                clean_text = re.sub(
                    r"<[^>]*>",
                    " ",
                    raw_text
                )

                clean_text = re.sub(
                    r"\s+",
                    " ",
                    clean_text
                )

                # 종목명이 전혀 없는 결과 제거
                ticker_found = (
                    re.search(
                        rf"\b{re.escape(ticker_symbol)}\b",
                        clean_text,
                        re.IGNORECASE
                    )
                    is not None
                )

                company_words = [
                    word.lower()
                    for word in re.findall(
                        r"[A-Za-z]{4,}",
                        company_name
                    )
                ]

                company_found = any(
                    word in clean_text.lower()
                    for word in company_words
                )

                if not ticker_found and not company_found:
                    continue

                title = (
                    QuantEngine
                    .professional_translate(
                        title_raw
                    )
                )

                summary = (
                    QuantEngine
                    .professional_translate(
                        re.sub(
                            r"<[^>]*>",
                            "",
                            summary_raw
                        )
                    )
                )

                news_list.append(
                    (
                        title,
                        summary[:180] + "...",
                        QuantEngine.convert_to_kst_string(
                            pub_parsed
                        ),
                        entry.get("link", "#")
                    )
                )

                if len(news_list) >= 5:
                    break

        except Exception:
            pass

        if not news_list:

            return [
                (
                    f"[{ticker_symbol}] "
                    "최근 관련 뉴스가 없습니다.",
                    "",
                    "최근",
                    "#"
                )
            ]

        return news_list


    # =====================================================
    # 소셜 검색 관련 핵심 함수
    # =====================================================

    @staticmethod
    def social_relevance_score(
        text,
        ticker_symbol,
        company_name
    ):

        text_lower = text.lower()

        ticker_lower = ticker_symbol.lower()

        score = 0

        # ---------------------------------------------
        # 티커 확인
        # ---------------------------------------------

        ticker_patterns = [
            rf"\${re.escape(ticker_lower)}\b",
            rf"\b{re.escape(ticker_lower)}\b"
        ]

        ticker_found = any(
            re.search(
                pattern,
                text_lower,
                re.IGNORECASE
            )
            for pattern in ticker_patterns
        )

        if ticker_found:
            score += 50


        # ---------------------------------------------
        # 회사명 확인
        # ---------------------------------------------

        company_clean = re.sub(
            r"[^A-Za-z0-9 ]",
            " ",
            company_name
        )

        company_words = [
            w.lower()
            for w in company_clean.split()
            if len(w) >= 4
        ]

        company_matches = 0

        for word in company_words:

            if word in text_lower:
                company_matches += 1

        score += min(
            company_matches * 15,
            45
        )


        # ---------------------------------------------
        # 주식 관련 단어
        # ---------------------------------------------

        finance_keywords = [
            "stock",
            "shares",
            "share",
            "price",
            "earnings",
            "revenue",
            "guidance",
            "investor",
            "investors",
            "market",
            "nasdaq",
            "nyse",
            "short",
            "shorts",
            "squeeze",
            "bullish",
            "bearish",
            "buy",
            "sell",
            "calls",
            "puts",
            "option",
            "options",
            "valuation",
            "analyst",
            "target",
            "launch",
            "satellite",
            "contract",
            "partnership"
        ]

        finance_count = sum(
            1
            for keyword in finance_keywords
            if keyword in text_lower
        )

        score += min(
            finance_count * 5,
            25
        )


        # ---------------------------------------------
        # 명백한 비관련 스포츠/농구 결과 감점
        # ---------------------------------------------

        unrelated_keywords = [
            "nba",
            "nfl",
            "mlb",
            "nhl",
            "basketball",
            "football",
            "baseball",
            "soccer",
            "tennis",
            "coach",
            "quarterback",
            "touchdown",
            "playoffs",
            "game score",
            "box score",
            "rebound",
            "assist",
            " dunk",
            "basket",
            "player",
            "roster",
            "draft pick"
        ]

        unrelated_count = sum(
            1
            for keyword in unrelated_keywords
            if keyword in text_lower
        )

        score -= unrelated_count * 40

        return score


    # =====================================================
    # 소셜 RSS 하나 가져오기
    # =====================================================

    @staticmethod
    def fetch_social_feed(
        ticker_symbol,
        company_name,
        source
    ):

        results = []

        try:

            # -----------------------------------------
            # 플랫폼별 검색어 분리
            # -----------------------------------------

            if source == "reddit":

                search_query = (
                    f'"{ticker_symbol}" '
                    f'"{company_name}" '
                    "site:reddit.com"
                )

            elif source == "x":

                search_query = (
                    f'"{ticker_symbol}" '
                    f'"{company_name}" '
                    "site:x.com"
                )

            elif source == "stocktwits":

                search_query = (
                    f'"{ticker_symbol}" '
                    f'"{company_name}" '
                    "site:stocktwits.com"
                )

            else:

                return []


            query = urllib.parse.quote(
                search_query
            )

            rss_url = (
                "https://news.google.com/rss/search"
                f"?q={query}"
                "&hl=en-US"
                "&gl=US"
                "&ceid=US:en"
                f"&t={int(time.time())}"
            )

            feed = feedparser.parse(
                rss_url
            )

            two_days_ago = (
                datetime.now(KST)
                - timedelta(days=2)
            )


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
                        .astimezone(KST)
                    )

                    if dt_kst < two_days_ago:
                        continue


                title_raw = entry.get(
                    "title",
                    ""
                )

                summary_raw = (
                    entry.get("summary", "")
                    or entry.get(
                        "description",
                        ""
                    )
                )


                combined_text = (
                    title_raw
                    + " "
                    + summary_raw
                )

                combined_text = re.sub(
                    r"<[^>]*>",
                    " ",
                    combined_text
                )

                combined_text = re.sub(
                    r"\s+",
                    " ",
                    combined_text
                ).strip()


                # -------------------------------------
                # 관련성 점수
                # -------------------------------------

                relevance = (
                    QuantEngine
                    .social_relevance_score(
                        combined_text,
                        ticker_symbol,
                        company_name
                    )
                )


                # -------------------------------------
                # 최소 관련성
                # -------------------------------------

                if relevance < 40:
                    continue


                title = (
                    QuantEngine
                    .professional_translate(
                        title_raw
                    )
                )

                summary_clean = re.sub(
                    r"<[^>]*>",
                    "",
                    summary_raw
                )

                summary = (
                    QuantEngine
                    .professional_translate(
                        summary_clean
                    )
                )


                # 플랫폼 이름
                source_label = {
                    "reddit": "Reddit",
                    "x": "X",
                    "stocktwits": "Stocktwits"
                }.get(
                    source,
                    source
                )


                results.append(
                    {
                        "title": title,
                        "summary": summary,
                        "pub": QuantEngine.convert_to_kst_string(
                            pub_parsed
                        ),
                        "link": entry.get(
                            "link",
                            "#"
                        ),
                        "source": source_label,
                        "score": relevance
                    }
                )


        except Exception:
            pass


        return results


    # =====================================================
    # X + Reddit + Stocktwits 통합
    # =====================================================

    @staticmethod
    def get_social_gossip(
        ticker_symbol,
        company_name
    ):

        all_results = []

        sources = [
            "reddit",
            "x",
            "stocktwits"
        ]

        for source in sources:

            results = (
                QuantEngine
                .fetch_social_feed(
                    ticker_symbol,
                    company_name,
                    source
                )
            )

            all_results.extend(results)


        # ---------------------------------------------
        # 중복 제거
        # ---------------------------------------------

        unique_results = []

        seen_titles = set()

        for item in all_results:

            normalized_title = re.sub(
                r"[^a-z0-9]",
                "",
                item["title"].lower()
            )

            if normalized_title in seen_titles:
                continue

            seen_titles.add(
                normalized_title
            )

            unique_results.append(
                item
            )


        # ---------------------------------------------
        # 관련성 + 최신순
        # ---------------------------------------------

        unique_results.sort(
            key=lambda x: x["score"],
            reverse=True
        )


        # ---------------------------------------------
        # 최대 6개
        # ---------------------------------------------

        unique_results = unique_results[:6]


        if not unique_results:

            return [
                {
                    "title": (
                        f"[{ticker_symbol}] "
                        "최근 X/Reddit 관련 "
                        "정보를 찾지 못했습니다."
                    ),
                    "summary": (
                        "검색 결과가 부족하거나 "
                        "종목과 직접적인 관련성이 "
                        "낮은 결과는 표시하지 않았습니다."
                    ),
                    "pub": "최근",
                    "link": "#",
                    "source": "검색",
                    "score": 0
                }
            ]


        return unique_results


    # =====================================================
    # 백테스트
    # =====================================================

    @staticmethod
    def run_backtest(ticker_symbol):

        try:

            df = yf.Ticker(
                ticker_symbol
            ).history(
                period="1y",
                interval="1d"
            )

            if df.empty or len(df) < 50:

                return (
                    0.0,
                    0.0,
                    0.0
                )


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


            active_returns = (
                strategy_ret[
                    strategy_ret != 0
                ]
            )


            if len(active_returns) > 0:

                win_rate = float(
                    (
                        active_returns > 0
                    ).mean() * 100
                )

            else:

                win_rate = 0.0


            equity = (
                1 + strategy_ret
            ).cumprod()

            drawdown = (
                equity
                / equity.cummax()
                - 1
            )

            mdd = float(
                drawdown.min() * 100
            )


            return (
                total_return,
                win_rate,
                mdd
            )


        except Exception:

            return (
                0.0,
                0.0,
                0.0
            )


    # =====================================================
    # 시장 데이터
    # =====================================================

    @staticmethod
    def fetch_market_data(
        ticker_symbol,
        timeframe="1D"
    ):

        try:

            ticker_obj = yf.Ticker(
                ticker_symbol
            )

            info = ticker_obj.info


            # -----------------------------------------
            # 데이터
            # -----------------------------------------

            if timeframe == "1D":

                data = ticker_obj.history(
                    period="1y",
                    interval="1d"
                )

            elif timeframe == "1H":

                data = ticker_obj.history(
                    period="5d",
                    interval="1h"
                )

            else:

                data = ticker_obj.history(
                    period="5d",
                    interval="15m"
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
                * 100
            )


            # -----------------------------------------
            # ATR
            # -----------------------------------------

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


            # -----------------------------------------
            # EMA
            # -----------------------------------------

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


            # -----------------------------------------
            # RSI
            # -----------------------------------------

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

            rsi_series = (
                100
                - (
                    100
                    / (1 + rs)
                )
            )

            rsi = float(
                rsi_series.iloc[-1]
            )


            # -----------------------------------------
            # Short
            # -----------------------------------------

            short_ratio = info.get(
                "shortPercentOfFloat",
                None
            )


            if short_ratio is not None:

                short_ratio_display = (
                    f"{short_ratio * 100:.1f}%"
                )

            else:

                short_ratio_display = "N/A"


            # -----------------------------------------
            # 백테스트
            # -----------------------------------------

            bt_ret, bt_win, bt_mdd = (
                QuantEngine
                .run_backtest(
                    ticker_symbol
                )
            )


            # -----------------------------------------
            # 점수
            # -----------------------------------------

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
                avg_volume_20 * curr_price
                < 10_000_000
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
                * 100
            )


            if disparity > 10:

                score -= 20

            elif disparity < -5:

                score -= 10


            score = max(
                0,
                min(
                    100,
                    score
                )
            )


            company_name = (
                info.get("longName")
                or info.get("shortName")
                or ticker_symbol
            )


            return {

                "ticker": ticker_symbol,

                "company_name": company_name,

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

                "short_ratio":
                    short_ratio_display,

                "bt_ret": bt_ret,

                "bt_win": bt_win,

                "bt_mdd": bt_mdd,

                "score": score,

                "data": data
            }


        except Exception as e:

            return None


# =========================================================
# Session State
# =========================================================

if "selected_ticker" not in st.session_state:

    st.session_state[
        "selected_ticker"
    ] = "ASTS"


if "timeframe" not in st.session_state:

    st.session_state[
        "timeframe"
    ] = "1D"


# =========================================================
# URL Parameters
# =========================================================

query_params = st.query_params


if "q" in query_params:

    st.session_state[
        "selected_ticker"
    ] = query_params["q"].upper()


if "tf" in query_params:

    st.session_state[
        "timeframe"
    ] = query_params["tf"].upper()


# =========================================================
# 우측 상단 메뉴
# =========================================================

_, col_popover = st.columns([10, 1])


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


# =========================================================
# 로고
# =========================================================

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
                text-align:center;
                margin-bottom:15px;
            ">
                <img
                    src="{main_logo}"
                    style="
                        max-width:240px;
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
            <h1 style="
                text-align:center;
                color:#F8FAFC;
            ">
                TAURUS LAB
            </h1>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# Market Overview
# =========================================================

st.markdown(
    f"""
    <div class="dashboard-header">
        <div style="
            font-size:13px;
            font-weight:700;
            color:#94A3B8;
        ">
            📊 Market Overview
        </div>

        <div style="
            font-size:15px;
            font-weight:800;
            color:#F8FAFC;
            margin-top:5px;
        ">
            나스닥 선물:
            {QuantEngine.get_nasdaq_futures()}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 종목 검색
# =========================================================

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

    st.query_params["q"] = (
        selected_ticker_result.upper()
    )

    st.rerun()


# =========================================================
# 시장 데이터
# =========================================================

res = QuantEngine.fetch_market_data(
    st.session_state["selected_ticker"],
    st.session_state["timeframe"]
)


# =========================================================
# 결과 출력
# =========================================================

if res:

    # ---------------------------------------------
    # 종목명
    # ---------------------------------------------

    col_title, col_btn = st.columns(
        [3.0, 1.0]
    )


    with col_title:

        st.markdown(
            f"""
            <h2 style="
                color:#F8FAFC;
                font-size:22px;
                margin-bottom:5px;
            ">
                [{res["ticker"]}]
                {res["company_name"]}
            </h2>
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
                    style="text-decoration:none;"
                >

                    <div style="
                        background-color:#121824;
                        padding:6px 14px 6px 12px;
                        border-radius:20px;
                        border:1px solid #1E293B;
                        display:inline-flex;
                        align-items:center;
                        gap:8px;
                    ">

                        <span style="
                            font-size:15px;
                        ">
                            📢
                        </span>

                        <span style="
                            color:#F8FAFC;
                            font-size:13px;
                            font-weight:600;
                        ">
                            실적발표 보러가기
                        </span>

                    </div>

                </a>

            </div>
            """,
            unsafe_allow_html=True
        )


    # ---------------------------------------------
    # 점수
    # ---------------------------------------------

    score = res["score"]


    if score >= 70:

        box_bg = (
            "linear-gradient("
            "135deg,"
            "#00E676,"
            "#00C853"
            ")"
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
            "135deg,"
            "#F59E0B,"
            "#D97706"
            ")"
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
            "135deg,"
            "#EF4444,"
            "#DC2626"
            ")"
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


    # ---------------------------------------------
    # Metrics
    # ---------------------------------------------

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


    # =====================================================
    # 차트 제목 + 시간 프레임
    # =====================================================

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


        ticker_for_url = (
            res["ticker"]
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
                    '?q={ticker_for_url}&tf=1D'
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
                    '?q={ticker_for_url}&tf=1H'
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
                    '?q={ticker_for_url}&tf=15M'
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


    # =====================================================
    # 차트
    # =====================================================

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
        fig,
        use_container_width=True
    )


    # =====================================================
    # 뉴스 / 찌라시
    # =====================================================

    tab_news, tab_gossip = st.tabs(
        [
            "📰 구글 영문 뉴스",
            "💬 X & 레딧 찌라시"
        ]
    )


    # =====================================================
    # 뉴스
    # =====================================================

    with tab_news:

        news = (
            QuantEngine
            .get_google_news(
                res["ticker"]
            )
        )


        for title, summary, pub, link in news:

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


    # =====================================================
    # X / Reddit
    # =====================================================

    with tab_gossip:

        st.caption(
            "종목 티커 + 회사명을 기준으로 관련성이 낮은 "
            "검색 결과는 자동 제외합니다."
        )


        gossip = (
            QuantEngine
            .get_social_gossip(
                res["ticker"],
                res["company_name"]
            )
        )


        for item in gossip:

            source = item["source"]

            if source == "Reddit":
                icon = "🔴"

            elif source == "X":
                icon = "⚫"

            elif source == "Stocktwits":
                icon = "🟠"

            else:
                icon = "💬"


            st.markdown(
                f"""
                <div class="news-card">

                    {icon}
                    <span style="
                        color:#64748B;
                        font-size:10px;
                        font-weight:700;
                    ">
                        {source}
                    </span>

                    &nbsp;

                    <a
                        href="{item['link']}"
                        target="_blank"
                        style="
                            color:#00E676;
                            font-weight:700;
                            text-decoration:none;
                            font-size:13px;
                        "
                    >
                        {item['title']}
                    </a>

                    <br>

                    <span style="
                        color:#94A3B8;
                        font-size:11px;
                    ">
                        ⏱ {item['pub']}
                    </span>

                    <br>

                    <span style="
                        color:#CBD5E1;
                        font-size:12px;
                    ">
                        {item['summary'][:220]}
                    </span>

                </div>
                """,
                unsafe_allow_html=True
            )


else:

    st.error(
        "데이터를 불러오지 못했습니다."
    )
