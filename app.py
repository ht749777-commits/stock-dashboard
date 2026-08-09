# ── [Market Overview 영역 (게임 아이템 툴팁 - 마우스 오버 시 높이 확장 및 최상위 덮어씌기)] ──
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
    body {{
        margin: 0;
        background-color: transparent;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        overflow: visible;
    }}
    .market-overview-container {{
        position: relative;
        width: 100%;
        background-color: #121824;
        border-radius: 8px;
        border: 1px solid #1E293B;
        box-sizing: border-box;
        overflow: visible;
        /* 평소엔 48px, 마우스 올리면 툴팁 공간(약 165px)까지 높이 확장 */
        height: 48px;
        transition: height 0.1s ease;
        z-index: 999999;
    }}
    .market-overview-container:hover {{
        height: 175px;
    }}
    .market-bar {{
        display: flex;
        align-items: center;
        height: 48px;
        padding: 0 16px;
        cursor: pointer;
    }}
    .market-title-badge {{
        color: #00E676; 
        font-weight: 900; 
        font-size: 14px; 
        white-space: nowrap;
        margin-right: 15px;
        display: flex;
        align-items: center;
    }}
    .ticker-slider-window {{
        height: 24px;
        overflow: hidden;
        position: relative;
        flex-grow: 1;
    }}
    .ticker-slider-list {{
        display: flex;
        flex-direction: column;
        margin: 0;
        padding: 0;
        list-style: none;
        position: absolute;
        width: 100%;
        animation: slotRoll 18s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    .market-overview-container:hover .ticker-slider-list {{
        animation-play-state: paused;
    }}
    .ticker-item {{
        height: 24px;
        line-height: 24px;
        font-size: 13px;
        color: #94A3B8;
        white-space: nowrap;
    }}
    @keyframes slotRoll {{
        0% {{ top: 0px; }}
        12% {{ top: 0px; }}
        16% {{ top: -24px; }}
        28% {{ top: -24px; }}
        32% {{ top: -48px; }}
        44% {{ top: -48px; }}
        48% {{ top: -72px; }}
        60% {{ top: -72px; }}
        64% {{ top: -96px; }}
        76% {{ top: -96px; }}
        80% {{ top: -120px; }}
        92% {{ top: -120px; }}
        100% {{ top: -144px; }}
    }}
    /* 게임 아이템 툴팁 스타일 - 아래쪽으로 자연스럽게 펼쳐지며 덮어씌움 */
    .dropdown-panel {{
        display: none;
        position: absolute;
        top: 50px;
        left: 0;
        width: 100%;
        background-color: rgba(13, 17, 23, 0.98);
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 12px 14px;
        box-sizing: border-box;
        box-shadow: 0 16px 36px rgba(0, 0, 0, 0.95);
        backdrop-filter: blur(6px);
    }}
    .market-overview-container:hover .dropdown-panel {{
        display: block;
    }}
    .grid-container {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
    }}
    .grid-item {{
        background-color: #121824;
        border: 1px solid #1E293B;
        border-radius: 6px;
        padding: 6px 8px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    .label-name {{
        color: #94A3B8;
        font-weight: 600;
        font-size: 11px;
        margin-bottom: 2px;
    }}
    .value-box {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
    }}
    .label-val {{
        color: #F8FAFC;
        font-weight: 700;
        font-size: 13px;
    }}
    .label-chg {{
        font-size: 11px;
        font-weight: 600;
    }}
</style>
</head>
<body>
<div class="market-overview-container">
    <div class="market-bar">
        <div class="market-title-badge">📊 Market Overview <span style="font-size:11px; color:#64748B; margin-left:6px; font-weight:normal;">(아이템 정보 보기)</span></div>
        <div class="ticker-slider-window">
            <ul class="ticker-slider-list">
                <li class="ticker-item">나스닥 100 선물: <b style="color:#F8FAFC;">{nq_val:,.2f}</b> <span style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({nq_chg:+.2f}%)</span></li>
                <li class="ticker-item">S&P 500 선물: <b style="color:#F8FAFC;">{es_val:,.2f}</b> <span style="color:{'#00E676' if es_chg>=0 else '#EF4444'};">({es_chg:+.2f}%)</span></li>
                <li class="ticker-item">원/달러 환율: <b style="color:#F8FAFC;">₩{usd_val:,.2f}</b> <span style="color:{'#00E676' if usd_chg>=0 else '#EF4444'};">({usd_chg:+.2f}%)</span></li>
                <li class="ticker-item">VIX (공포 지수): <b style="color:#F8FAFC;">{vix_val:,.2f}</b> <span style="color:{'#EF4444' if vix_chg>=0 else '#00E676'};">({vix_chg:+.2f}%)</span></li>
                <li class="ticker-item">미국 10년물 국채금리: <b style="color:#F8FAFC;">{tnx_val:.2f}%</b> <span style="color:{'#00E676' if tnx_chg>=0 else '#EF4444'};">({tnx_chg:+.2f}%)</span></li>
                <li class="ticker-item">비트코인 (BTC): <b style="color:#F8FAFC;">${btc_val:,.0f}</b> <span style="color:{'#00E676' if btc_chg>=0 else '#EF4444'};">({btc_chg:+.2f}%)</span></li>
                <li class="ticker-item">나스닥 100 선물: <b style="color:#F8FAFC;">{nq_val:,.2f}</b> <span style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({nq_chg:+.2f}%)</span></li>
            </ul>
        </div>
    </div>
    
    <div class="dropdown-panel">
        <div class="grid-container">
            <div class="grid-item">
                <span class="label-name">나스닥 100 선물</span>
                <div class="value-box">
                    <span class="label-val">{nq_val:,.2f}</span>
                    <span class="label-chg" style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({nq_chg:+.2f}%)</span>
                </div>
            </div>
            <div class="grid-item">
                <span class="label-name">S&P 500 선물</span>
                <div class="value-box">
                    <span class="label-val">{es_val:,.2f}</span>
                    <span class="label-chg" style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({es_chg:+.2f}%)</span>
                </div>
            </div>
            <div class="grid-item">
                <span class="label-name">원/달러 환율</span>
                <div class="value-box">
                    <span class="label-val">₩{usd_val:,.2f}</span>
                    <span class="label-chg" style="color:{'#00E676' if nq_chg>=0 else '#EF4444'};">({usd_chg:+.2f}%)</span>
                </div>
            </div>
            <div class="grid-item">
                <span class="label-name">VIX (변동성 지수)</span>
                <div class="value-box">
                    <span class="label-val">{vix_val:,.2f}</span>
                    <span class="label-chg" style="color:{'#EF4444' if vix_chg>=0 else '#EF4444'};">({vix_chg:+.2f}%)</span>
                </div>
            </div>
            <div class="grid-item">
                <span class="label-name">미국 10년물 국채금리</span>
                <div class="value-box">
                    <span class="label-val">{tnx_val:.2f}%</span>
                    <span class="label-chg" style="color:{'#00E676' if tnx_chg>=0 else '#EF4444'};">({tnx_chg:+.2f}%)</span>
                </div>
            </div>
            <div class="grid-item">
                <span class="label-name">비트코인 (BTC)</span>
                <div class="value-box">
                    <span class="label-val">${btc_val:,.0f}</span>
                    <span class="label-chg" style="color:{'#00E676' if tnx_chg>=0 else '#EF4444'};">({btc_chg:+.2f}%)</span>
                </div>
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""

# 평소에는 52px, 마우스 올리면 컴포넌트 자체 높이가 늘어나도록 설정
components.html(market_component_html, height=55, scrolling=False)
