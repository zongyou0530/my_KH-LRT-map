import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time
import base64
import os
from streamlit_js_eval import get_geolocation

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

# --- A. 字體處理 (手寫體載入) ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_base64 = base64.b64encode(f.read()).decode()
    font_css = f"""
    @font-face {{
        font-family: 'HandWrite';
        src: url(data:font/otf;base64,{font_base64}) format('opentype');
    }}
    """

# --- B. CSS 樣式分配 ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&display=swap');
    {font_css}
    
    /* 預設圓體 */
    html, body, [data-testid="stAppViewContainer"], p, span, label, div {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
    }}

    /* 主標題：手寫體 */
    .custom-title {{
        font-family: 'HandWrite' !important;
        font-size: clamp(32px, 8vw, 44px);
        color: #a5d6a7;
        text-align: center;
        margin-bottom: 20px;
    }}

    /* 車站即時站牌標題：手寫體 */
    .board-header {{
        font-family: 'HandWrite' !important;
        font-size: 28px;
        color: #81c784;
        margin-bottom: 10px;
    }}

    /* 到站時間數字：手寫體 */
    .arrival-time {{
        font-family: 'HandWrite' !important;
        font-size: 26px;
        color: #ffffff;
    }}

    /* 作者留言內容：手寫體 */
    .author-text {{
        font-family: 'HandWrite' !important;
        font-size: 1.25em;
        color: #abb2bf;
        line-height: 1.6;
    }}

    /* 下拉選單：強制圓體 */
    .stSelectbox div[data-baseweb="select"] {{
        font-family: 'Zen Maru Gothic' !important;
    }}

    .legend-box {{ background-color: #212d3d; border-radius: 10px; padding: 10px; margin-bottom: 15px; display: flex; justify-content: center; gap: 15px; }}
    .footer-box {{ background-color: #1a1d23; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; }}
    .paper-card {{ background-color: #1a1d23; border-left: 5px solid #4caf50; padding: 12px; margin-bottom: 10px; border-radius: 8px; }}
</style>
""", unsafe_allow_html=True)

# --- C. 核心數據抓取 (無快取暴力刷新) ---
def get_tdx_data():
    try:
        # 請確保您的 Secrets 名稱正確
        client_id = st.secrets.get("TD_ID_NEW") or st.secrets.get("TD_ID")
        client_secret = st.secrets.get("TD_SECRET_NEW") or st.secrets.get("TD_SECRET")
        
        # 1. 取得 Token
        auth_res = requests.post(
            'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token',
            data={'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': client_secret},
            timeout=10
        )
        token = auth_res.json().get('access_token')
        if not token: return None, "TOKEN_FAIL"

        # 2. 取得列車位置
        pos_res = requests.get(
            'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        return pos_res.json(), token
    except Exception as e:
        return None, str(e)

live_positions, token = get_tdx_data()

# --- D. 定位與時間 ---
tz = pytz.timezone('Asia/Taipei')
time_now = datetime.datetime.now(tz).strftime("%Y年%m月%d日 %H:%M:%S")
user_location = None
loc = get_geolocation()
if loc: user_location = [loc['coords']['latitude'], loc['coords']['longitude']]

# --- E. UI 渲染 ---
st.markdown('<div class="custom-title">高雄輕軌 即時位置監測</div>', unsafe_allow_html=True)

# 警示框 (只有在失敗時顯示)
if not token:
    st.error(f"❌ 無法讀取資料，請檢查 API 設定。代碼: {live_positions}")

st.markdown('<div class="legend-box">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if user_location:
        folium.CircleMarker(user_location, radius=8, color='#ff5252', fill=True).add_to(m)
    
    if token and isinstance(live_positions, dict):
        for t in live_positions.get('LivePositions', []):
            folium.Marker(
                [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')
            ).add_to(m)
    folium_static(m, height=420, width=900)

with col_info:
    # 標題：手寫體
    st.markdown('<div class="board-header">🚉 車站即時站牌</div>', unsafe_allow_html=True)
    
    # 車站列表
    stations = { "C1 籬仔內": [22.6015, 120.3204], "C20 台鐵美術館": [22.6500, 120.2868], "C21A 內維中心": [22.6548, 120.2861], "C24 愛河之心": [22.6586, 120.3032]} # 簡略示意
    sel_st = st.selectbox("選擇車站", list(stations.keys()), label_visibility="collapsed")
    target_id = sel_st.split()[0]

    if token:
        try:
            board_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{target_id}'&$format=JSON"
            board_res = requests.get(board_url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
            for item in sorted(board_res.json(), key=lambda x: x.get('EstimateTime', 999)):
                est = int(item.get('EstimateTime', 0))
                msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                st.markdown(f"""
                <div class="paper-card">
                    <div style="color:#4caf50; font-size:12px;">預計抵達時間</div>
                    <div class="arrival-time">{msg}</div>
                </div>
                """, unsafe_allow_html=True)
        except:
            st.write("⌛ 暫無列車資訊")

    # 資訊欄：圓體
    st.markdown(f"""
    <div style="font-size:0.85em; color:#888; margin-top:20px; border-top:1px solid #333; padding-top:10px;">
        📍 更新時間：{time_now}<br>
        🛰️ 目前座標：{user_location if user_location else "定位中..."}
    </div>
    """, unsafe_allow_html=True)

# --- F. 底部留言板 ---
st.markdown(f"""
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:8px;">✍️ 作者留言：</div>
    <div class="author-text">
        各位親朋好友們，拜託請幫我看看到底準不準，不準的話可以搜尋ig跟我講謝謝。資料由 TDX 平台提供，僅供參考。
    </div>
</div>
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:5px;">📦 版本更新紀錄 (V4.3) ：</div>
    <div style="color:#abb2bf; font-size:14px;">
        • <b>語法衝突修復</b>：解決截圖中出現的原始碼顯示問題。<br>
        • <b>字體深度分配</b>：標題/到站時間/留言採手寫體，選單/資訊欄採圓體。<br>
        • <b>跨月緩存清理</b>：確保 2026/01 資料讀取通暢。
    </div>
</div>
""", unsafe_allow_html=True)

# 隔 30 秒自動刷新
time.sleep(30)
st.rerun()
