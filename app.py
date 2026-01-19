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

# --- A. 字體與視覺樣式 ---
font_path = "ZONGYOOOOOOU1.otf"
hand_font_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_font_base64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
    /* 載入圓體 (Zen Old Mincho) */
    @import url('https://fonts.googleapis.com/css2?family=Zen+Old+Mincho&display=swap');
    
    /* 載入你的手寫體 */
    @font-face {{
        font-family: 'ZongHand';
        src: url(data:font/otf;base64,{hand_font_base64}) format('opentype');
    }}

    /* 全域設定 */
    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}
    .block-container {{ padding-top: 1.5rem !important; }}

    /* 標題：手寫體 */
    .title-text {{
        font-family: 'ZongHand', sans-serif !important;
        font-size: 38px;
        color: #a5d6a7;
        text-align: center;
        margin-bottom: 5px;
    }}

    /* 圖例列：圓體 (Zen Old Mincho) */
    .legend-row {{
        font-family: 'Zen Old Mincho', serif !important;
        background-color: #1a1d23;
        border-radius: 10px;
        padding: 8px 15px;
        text-align: center;
        margin: 10px auto 25px auto;
        width: fit-content;
        border: 1px solid #30363d;
        font-size: 18px;
    }}

    /* 卡片設計：恢復深色背景與邊框 */
    .info-card {{
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
    }}

    .card-label {{
        font-family: 'Zen Old Mincho', serif;
        color: #81c784;
        font-size: 18px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
    }}

    /* 卡片時間內容與留言內容：手寫體 */
    .hand-content {{
        font-family: 'ZongHand' !important;
        font-size: 28px;
        color: #ffffff;
        margin: 5px 0;
    }}

    .update-time {{
        color: #888;
        font-size: 14px;
        font-family: sans-serif;
        margin-top: 10px;
    }}
</style>
""", unsafe_allow_html=True)

# --- B. 標題與圖例 ---
st.markdown('<div class="title-text">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-row">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

# --- C. 資料抓取邏輯 (TDX) ---
def get_tdx():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        tk_res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                               data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}).json()
        tk = tk_res.get('access_token')
        res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                           headers={'Authorization': f'Bearer {tk}'}).json()
        live = res.get('LivePositions', []) if isinstance(res, dict) else res
        return live, tk
    except: return [], None

# --- D. 主介面佈局 ---
col_map, col_info = st.columns([7, 3])

# 範例座標 (建議保留你原本的完整 STATION_COORDS)
STATION_COORDS = {"C1 籬仔內": [22.6015, 120.3204], "C20 台鐵美術館": [22.6500, 120.2868], "C21 美術館": [22.6593, 120.2868]}

with col_map:
    # 建立地圖
    m = folium.Map(location=[22.6593, 120.2868], zoom_start=14, tiles="cartodb voyager")
    live_data, token = get_tdx()
    for t in live_data:
        try:
            folium.Marker(
                [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')
            ).add_to(m)
        except: continue
    folium_static(m, height=500, width=800)

with col_info:
    st.markdown('<div class="card-label">🚉 選擇車站</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("", list(STATION_COORDS.keys()), index=1, label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    # 動態抓取車站進站資訊
    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                                 headers={'Authorization': f'Bearer {token}'}).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="card-label">預計抵達時間</div>
                        <div class="hand-content">{msg}</div>
                    </div>
                    """, unsafe_allow_html=True)
        except: st.write("讀取中...")

    now_t = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%Y/%m/%d %H:%M:%S")
    st.markdown(f'<div class="update-time">📍 更新時間：{now_t}</div>', unsafe_allow_html=True)

# --- E. 底部留言 ---
st.markdown(f"""
<div class="info-card">
    <div class="card-label">✍️ 作者留言：</div>
    <div class="hand-content" style="font-size: 20px;">
    各位親朋好友們，不準的話可以私訊 IG 跟我講，資料由 TDX 平台提供，僅供參考。
    </div>
</div>
""", unsafe_allow_html=True)

# --- F. 自動更新邏輯 ---
time.sleep(30)
st.rerun()
