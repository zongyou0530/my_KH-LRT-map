import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import base64
import os
import time
import datetime
import pytz
import math
from streamlit_js_eval import get_geolocation

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
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{hand_base64}) format('opentype');
    }}

    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}
    .block-container {{ padding-top: 2rem !important; }}

    /* 標題：放大且換行 */
    .header-title {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 52px !important; /* 加大標題 */
        color: #a5d6a7;
        text-align: center;
        line-height: 1.1 !important;
        margin-bottom: 20px;
    }}

    /* 圖例列：縮小 */
    .legend-container {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 15px;
        padding: 4px 12px;
        text-align: center;
        margin: 0 auto 20px auto;
        width: fit-content;
        font-size: 13px;
        color: #cccccc;
    }}

    /* 卡片微縮化 */
    .info-card {{
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 10px 15px; /* 縮小內邊距 */
        margin-bottom: 10px; /* 縮小間距 */
    }}

    .label-round {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
        color: #81c784;
        font-size: 15px;
        margin-bottom: 2px;
    }}

    .content-hand {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 24px;
        color: #ffffff;
    }}

    /* 更新紀錄：靠左、圓體 */
    .update-log-box {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
        font-size: 14px;
        color: #cbd5e0;
        line-height: 1.6;
        text-align: left !important;
    }}
    
    .status-text-left {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
        text-align: left;
        color: #718096;
        font-size: 13px;
        margin-top: 5px;
    }}
</style>
""", unsafe_allow_html=True)

# --- B. 標題與圖例 ---
st.markdown('<div class="header-title">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

# --- C. 抓取位置與資料 ---
user_loc = get_geolocation()
user_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc else None

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
    # 預設美術館中心，如果有使用者位置則以此為中心
    center = user_pos if user_pos else [22.6593, 120.2868]
    m = folium.Map(location=center, zoom_start=15, tiles="cartodb voyager")
    
    # 標記使用者紅點
    if user_pos:
        folium.CircleMarker(user_pos, radius=6, color='white', weight=2, fill=True, fill_color='red', fill_opacity=1, popup="目前位置").add_to(m)
    
    live_data, token = get_tdx()
    for t in live_data:
        try:
            folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                          icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: continue
    folium_static(m, height=500, width=800)

with col_info:
    st.markdown('<div class="label-round">🚉 選擇車站</div>', unsafe_allow_html=True)
    stations = {"C21 美術館": [22.6593, 120.2868], "C24 愛河之心": [22.6586, 120.3032], "C1 籬仔內": [22.6015, 120.3204]}
    sel_st = st.selectbox("", list(stations.keys()), index=0, label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                                 headers={'Authorization': f'Bearer {token}'}).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'<div class="info-card"><div class="label-round">預計抵達時間</div><div class="content-hand">{msg}</div></div>', unsafe_allow_html=True)
        except: pass

    now_t = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%Y/%m/%d %H:%M:%S")
    st.markdown(f'<div class="status-text-left">📍 更新時間：{now_t}</div>', unsafe_allow_html=True)
    if user_pos:
        st.markdown(f'<div class="status-text-left">✅ 已成功讀取座標</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-text-left">⚠️ 正在嘗試讀取座標...</div>', unsafe_allow_html=True)

# --- D. 底部說明 ---
st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
col_msg, col_log = st.columns([1, 1.2])

with col_msg:
    st.markdown(f"""
    <div class="info-card">
        <div class="label-round">✍️ 作者留言：</div>
        <div class="content-hand" style="font-size: 19px;">
        各位親朋好友們，不準的話可以私訊 IG 跟我講，資料由 TDX 平台提供，僅供參考。
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_log:
    st.markdown(f"""
    <div class="info-card">
        <div class="label-round">📦 最新更新內容說明：</div>
        <div class="update-log-box">
            • 標題放大且換行處理，修正頂部視覺比例。<br>
            • 恢復紅點標記：加入自動抓取當前位置座標功能。<br>
            • 精簡化卡片：縮小預計抵達時間卡片尺寸與文字。<br>
            • 底部資訊靠左：更新時間與座標讀取狀態全面置左。<br>
            • 字體修正：說明內容改回圓體，保持閱讀舒適度。
        </div>
    </div>
    """, unsafe_allow_html=True)

time.sleep(30)
st.rerun()
