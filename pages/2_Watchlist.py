import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(
    page_title="Watchlist & Scanner",
    page_icon="📋",
    layout="wide"
)

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
    </style>
""", unsafe_allow_html=True)

WATCHLIST = [
    "SPCX", "ASTS", "NVDA", "TSLA", "PLTR", "AMD", "AAPL", "MSFT", "AMZN",
    "GOOGL", "META", "AVGO", "SMCI", "COIN", "MSTR", "IONQ", "RKLB"
]

st.markdown("""
    <div class="dashboard-header">
        <span style="color: #00E676; font-weight: 900; font-size: 16px;">📋 Watchlist & Scanner</span>
        <span style="color: #94A3B8; font-size: 12px; margin-left: 10px;">보수적 퀀트 필터가 적용된 감시 종목 모니터링</span>
    </div>
""", unsafe_allow_html=True)

table_data = []
scanner_data = []

for t in WATCHLIST:
    try:
        ticker_obj = yf.Ticker(t)
        df = ticker_obj.history(period="1y", interval="1d")
        
        # 데이터가 비어있거나 충분하지 않은 경우 안전하게 예외 처리 분기
        if df is None or df.empty or len(df) < 20:
            table_data.append({"티커": t, "현재가": "N/A", "등락률": "N/A", "퀀트 점수": "데이터 없음", "raw_change": 0.0})
            continue

        close = df['Close']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
        
        curr_p = float(close.iloc[-1])
        prev_p = float(close.iloc[-2] if len(close) > 1 else curr_p)
        change_p = ((curr_p - prev_p) / prev_p) * 100 if prev_p > 0 else 0.0
        
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean() if len(close) >= 50 else ema20
        ema200 = close.ewm(span=200, adjust=False).mean() if len(close) >= 200 else ema50
        
        # RSI 계산 안전장치
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi = float(100 - (100 / (1 + rs.iloc[-1])))

        # 🛡️ 보수적 퀀트 점수 산정 로직
        score = 40
        if len(close) >= 200 and curr_p > ema20.iloc[-1] and ema20.iloc[-1] > ema50.iloc[-1] and ema50.iloc[-1] > ema200.iloc[-1]:
            score += 25
        elif curr_p > ema20.iloc[-1]:
            score += 5
        else:
            score -= 20

        if 45 <= rsi <= 60:
            score += 20
        elif 60 < rsi <= 70:
            score += 10
        elif rsi > 70 or rsi < 35:
            score -= 25

        avg_volume_20 = volume.tail(20).mean() if not volume.empty else 0
        if avg_volume_20 * curr_p < 10000000:
            score -= 25
        else:
            score += 10

        disparity = ((curr_p - ema20.iloc[-1]) / ema20.iloc[-1]) * 100 if ema20.iloc[-1] > 0 else 0
        if disparity > 10:
            score -= 20
        elif disparity < -5:
            score -= 10

        score = max(0, min(100, score))
        
        row_item = {
            "티커": t,
            "현재가": f"${curr_p:,.2f}",
            "등락률": f"{change_p:+.2f}%",
            "퀀트 점수": f"{score}점",
            "raw_change": change_p
        }
        table_data.append(row_item)
        
        if score >= 75 and change_p > 0:
            scanner_data.append(row_item)
            
    except Exception as e:
        table_data.append({"티커": t, "현재가": "N/A", "등락률": "N/A", "퀀트 점수": "0점", "raw_change": 0.0})

def render_dark_table(data_list):
    if not data_list:
        return "<p style='color: #94A3B8; font-size: 13px;'>조건을 만족하는 종목이 없습니다.</p>"
    
    rows_html = ""
    for idx, row in enumerate(data_list):
        bg_color = "#121824" if idx % 2 == 0 else "#161F2E"
        chg_color = "#00E676" if row["raw_change"] >= 0 else "#EF4444"
        rows_html += f'<tr style="background-color: {bg_color}; border-bottom: 1px solid #1E293B;"><td style="padding: 12px 18px; color: #F8FAFC; font-weight: 800;">{row["티커"]}</td><td style="padding: 12px 18px; color: #E2E8F0; text-align: right; font-weight: 600;">{row["현재가"]}</td><td style="padding: 12px 18px; color: {chg_color}; text-align: right; font-weight: 700;">{row["등락률"]}</td><td style="padding: 12px 18px; color: #F59E0B; text-align: right; font-weight: 800;">{row["퀀트 점수"]}</td></tr>'

    complete_html = f'<div style="background-color: #121824; border: 1px solid #1E293B; border-radius: 10px; overflow: hidden; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);"><table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;"><thead><tr style="background-color: #1A2233; color: #94A3B8; border-bottom: 1px solid #1E293B;"><th style="padding: 14px 18px; font-weight: 700;">티커</th><th style="padding: 14px 18px; font-weight: 700; text-align: right;">현재가</th><th style="padding: 14px 18px; font-weight: 700; text-align: right;">등락률</th><th style="padding: 14px 18px; font-weight: 700; text-align: right;">퀀트 점수</th></tr></thead><tbody>{rows_html}</tbody></table></div>'
    return complete_html

st.markdown(f"<h4 style='color: #F8FAFC; font-size: 15px; margin-bottom: 10px;'>📊 Watchlist 명단 ({len(WATCHLIST)}개 감시중)</h4>", unsafe_allow_html=True)
st.markdown(render_dark_table(table_data), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"<h4 style='color: #00E676; font-size: 15px; margin-bottom: 10px;'>🚀 클린 우량 급등주 ({len(scanner_data)}개 포착)</h4>", unsafe_allow_html=True)

if scanner_data:
    st.markdown(render_dark_table(scanner_data), unsafe_allow_html=True)
else:
    st.markdown("<p style='color: #94A3B8; font-size: 13px;'>현재 엄격한 퀀트 조건을 만족하는 우량 급등주가 없습니다.</p>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 전체 재탐색 수행", use_container_width=True):
    st.success("모든 종목의 데이터를 새롭게 갱신했습니다!")
    st.rerun()
