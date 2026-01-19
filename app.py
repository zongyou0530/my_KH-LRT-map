import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import base64
import os
import time
import datetime
import pytz

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體載入 ---
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
    /* 1. 匯入圓體 */
    @import url('https://fonts.googleapis.com/css2?family=Zen+Old+Mincho:wght@400;700&display=swap');
    
    /* 2. 定義手寫體 */
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{hand_base64}) format('opentype');
    }}

    /* 3. 基礎樣式 */
    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}
    .block-container {{ padding-top: 1rem !important; }}

    /* 標題：手寫體 */
    .header-title {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 40px;
        color: #a5d6a7;
        text-align: center;
        line-height: 1.2;
        margin-bottom: 10px;
    }}

    /* 圖例列：圓體 (Zen Old Mincho) */
    .legend-row {{
        font-family: 'Zen Old Mincho', serif !important;
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 8px 20px;
        text-align: center;
        margin: 0 auto 20px auto;
        width: fit-content;
        font-size: 18px;
    }}

    /* 卡片設計 */
    .info-card {{
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
    }}

    /* 卡片標籤：圓體 */
    .label-zen {{
        font-family: 'Zen Old Mincho', serif !important;
        color: #81c784;
        font-size: 18px;
        margin-bottom: 5px;
    }}

    /* 卡片內容 & 作者留言：手寫體 */
    .content-hand {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 28px;
        color: #ffffff;
    }}

    /* 更新紀錄文字：手寫體 */
    .log-text {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 18px;
        color: #cccccc;
        line-height: 1.6;
    }}
</style>
""", unsafe_allow_html=True)

# --- B. 標題與圖例 ---
st.markdown('<div class="header-title">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-row">🟢 順行 | 🔵 逆行 | 🔴 目前位置</div>', unsafe_allow_html=True)

# --- C. 資料抓取 ---
def get_tdx():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        tk = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                           data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}).json().get('access_token')
        res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                           headers={'Authorization': f'Bearer {tk}'}).json()
        return (res.get('LivePositions', []) if isinstance(res, dict) else res), tk
    except: return [], None

# --- D. 主介面 ---
col_map, col_info = st.columns([7, 3])

STATION_COORDS = {"C1 籬仔內": [22.6015, 120.3204], "C20 台鐵美術館": [22.6500, 120.2868], "C21 美術館": [22.6593, 120.2868], "C24 愛河之心": [22.6586, 120.3032]}

with col_map:
    m = folium.Map(location=[22.6593, 120.2868], zoom_start=14, tiles="cartodb voyager")
    live_data, token = get_tdx()
    for t in live_data:
        try:
            folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                          icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: continue
    folium_static(m, height=500, width=850)

with col_info:
    st.markdown('<div class="label-zen">🚉 選擇車站</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("", list(STATION_COORDS.keys()), index=2, label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                                 headers={'Authorization': f'Bearer {token}'}).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'<div class="info-card"><div class="label-zen">預計抵達時間</div><div class="content-hand">{msg}</div></div>', unsafe_allow_html=True)
        except: pass

    now_t = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%Y/%m/%d %H:%M:%S")
    st.markdown(f'<div style="color:#888; font-size:14px;">📍 更新時間：{now_t}</div>', unsafe_allow_html=True)

# --- E. 底部說明與更新紀錄 ---
st.markdown(f"""
<div class="info-card">
    <div class="label-zen">✍️ 作者留言：</div>
    <div class="content-hand" style="font-size: 20px;">
    各位親朋好友們，不準的話可以私訊 IG 跟我講，資料由 TDX 平台提供，僅供參考。
    </div>
</div>

<div class="info-card">
    <div class="label-zen">📦 最新更新內容說明：</div>
    <div class="log-text">
        • 修正字體權限，圖例文字恢復使用圓體 (Zen Old Mincho)。<br>
        • 網頁標題、卡片時間、留言內文正確套用 ZONGYOOOOOOU1 手寫字體。<br>
        • 修復卡片背景消失問題，維持深色主題質感。<br>
        • 確保自動更新 (30秒) 穩定運行。
    </div>
</div>
""", unsafe_allow_html=True)

# --- F. 自動更新 ---
time.sleep(30)
st.rerun()
