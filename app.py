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
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
    /* 載入圓體 */
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    
    /* 定義手寫體 */
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{hand_base64}) format('opentype');
    }}

    /* 全域背景 */
    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}
    
    /* 主容器間距控制 */
    .block-container {{ 
        padding-top: 3rem !important; 
        max-width: 1200px;
    }}

    /* 1. 標題：手寫體，往下移動 */
    .header-title {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 34px;
        color: #a5d6a7;
        text-align: center;
        margin-bottom: 25px;
        letter-spacing: 2px;
    }}

    /* 2. 圖例：微縮、圓體、精簡化 */
    .legend-container {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 20px;
        padding: 5px 15px;
        text-align: center;
        margin: 0 auto 15px auto;
        width: fit-content;
        font-size: 14px; /* 縮小字體 */
        color: #ffffff;
    }}

    /* 3. 卡片設計：增加間距與質感 */
    .info-card {{
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px; /* 增加卡片間距 */
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }}

    /* 4. 字體分配標籤 */
    .label-round {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
        color: #81c784;
        font-size: 16px;
        margin-bottom: 8px;
        font-weight: 700;
    }}

    .content-hand {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 26px;
        color: #ffffff;
        margin-top: 4px;
    }}

    /* 5. 更新紀錄專用：純圓體 */
    .update-log-box {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
        font-size: 15px;
        color: #cbd5e0;
        line-height: 1.8;
    }}

    .stSelectbox {{ margin-bottom: 25px; }}
</style>
""", unsafe_allow_html=True)

# --- B. 標題與圖例 ---
st.markdown('<div class="header-title">高雄輕軌 即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

# --- C. 資料處理 ---
def get_tdx():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        tk = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                           data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}).json().get('access_token')
        res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                           headers={'Authorization': f'Bearer {tk}'}).json()
        return (res if isinstance(res, list) else res.get('LivePositions', [])), tk
    except: return [], None

col_map, col_info = st.columns([7, 3.5])

with col_map:
    # 增加地圖與上方間距的平衡感
    m = folium.Map(location=[22.6593, 120.2868], zoom_start=14, tiles="cartodb voyager")
    live_data, token = get_tdx()
    for t in live_data:
        try:
            folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                          icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: continue
    folium_static(m, height=550, width=800)

with col_info:
    # 選擇車站區塊
    st.markdown('<div class="label-round">🚉 選擇車站</div>', unsafe_allow_html=True)
    stations = ["C1 籬仔內", "C20 台鐵美術館", "C21 美術館", "C24 愛河之心"]
    sel_st = st.selectbox("", stations, index=2, label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    # 預計抵達時間 (卡片排版優化)
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
                            <div class="label-round">預計抵達時間</div>
                            <div class="content-hand">{msg}</div>
                        </div>
                    """, unsafe_allow_html=True)
        except: pass

    now_t = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%Y/%m/%d %H:%M:%S")
    st.markdown(f'<div style="color:#718096; font-size:13px; font-family: sans-serif; text-align:right;">📍 更新時間：{now_t}</div>', unsafe_allow_html=True)

st.markdown("---") # 分隔線

# --- D. 底部區塊：作者留言與更新紀錄 ---
col_msg, col_log = st.columns([1, 1])

with col_msg:
    st.markdown(f"""
    <div class="info-card">
        <div class="label-round">✍️ 作者留言：</div>
        <div class="content-hand" style="font-size: 20px;">
        各位親朋好友們，不準的話可以私訊 IG 跟我講，資料由 TDX 平台提供，僅供參考。
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_log:
    st.markdown(f"""
    <div class="info-card">
        <div class="label-round">📦 最新更新內容說明：</div>
        <div class="update-log-box">
            • 視覺比例優化：縮小圖例說明，並將標題下移，增加頁面呼吸感。<br>
            • 字體分離邏輯：更新內容說明改回使用「圓體」，僅重點內容保留手寫體。<br>
            • 卡片間距修正：解決卡片過於擁擠問題，提升手機版閱讀體驗。<br>
            • 穩定更新：確保每 30 秒資料與位置同步。
        </div>
    </div>
    """, unsafe_allow_html=True)

time.sleep(30)
st.rerun()
