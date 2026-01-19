import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time
import base64
import os
import math

# 1. 頁面基本設定 (最頂端)
st.set_page_config(page_title="高雄輕軌監測", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體強制載入邏輯 ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""

if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_base64 = base64.b64encode(f.read()).decode()
    # 這裡使用最強制的 CSS 選擇器，確保從 html 到最深層的 div 都用你的手寫體
    font_css = f"""
    @font-face {{
        font-family: 'ZongHandwritten';
        src: url(data:font/otf;base64,{font_base64}) format('opentype');
    }}
    
    /* 全域強制套用 */
    * {{
        font-family: 'ZongHandwritten' !important;
    }}
    
    /* 針對 Streamlit 標題與選單的特殊補強 */
    .stMarkdown, .stText, .stButton, .stSelectbox, .stHeader, h1, h2, h3, p, span, div {{
        font-family: 'ZongHandwritten' !important;
    }}
    """
else:
    st.error(f"找不到檔案: {font_path}")

# --- B. 視覺修正 CSS ---
st.markdown(f"""
<style>
    {font_css}

    /* 1. 徹底消除頂部空白與 Streamlit 紅色/白色裝飾線 */
    header {{ visibility: hidden !important; height: 0px !important; }}
    .stApp {{ background-color: #0e1117 !important; }}
    .block-container {{ padding-top: 0rem !important; padding-bottom: 0rem !important; }}
    [data-testid="stDecoration"] {{ display: none !important; }}

    /* 2. 標題區：兩行嚴格等大，解決你截圖中大小不一的問題 */
    .title-box {{
        text-align: center;
        padding: 20px 0;
        color: #a5d6a7;
    }}
    .title-line {{
        font-size: 42px !important; /* 統一兩行大小 */
        line-height: 1.2;
        display: block;
    }}

    /* 3. 卡片式設計 (與截圖一致) */
    .info-card {{
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
    }}
    .card-label {{ color: #81c784; font-size: 18px !important; }}
    .card-value {{ color: white; font-size: 26px !important; margin-top: 5px; }}
    
    /* 修正選單字體與顏色 */
    .stSelectbox div[data-baseweb="select"] {{
        background-color: #262730 !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- C. 標題與圖例 ---
st.markdown("""
<div class="title-box">
    <span class="title-line">高雄輕軌</span>
    <span class="title-line">即時位置地圖</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 20px; font-size: 18px;">
    <span>🟢 順行</span><span>🔵 逆行</span><span>🔴 目前位置</span>
</div>
""", unsafe_allow_html=True)

# --- D. 數據抓取 ---
def get_tdx_data():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        tk = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                           data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}).json().get('access_token')
        res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                           headers={'Authorization': f'Bearer {tk}'}).json()
        return (res.get('LivePositions', []) if isinstance(res, dict) else res), tk
    except: return [], None

# --- E. 頁面佈局 ---
col_map, col_info = st.columns([7, 3])

# 車站座標 (縮減版)
STATION_COORDS = {"C1 籬仔內": [22.6015, 120.3204], "C20 台鐵美術館": [22.6500, 120.2868], "C21 美術館": [22.6593, 120.2868]} # 建議保留完整名單

with col_map:
    m = folium.Map(location=[22.6593, 120.2868], zoom_start=14, tiles="cartodb voyager")
    live_pos, token = get_tdx_data()
    for t in live_pos:
        try:
            folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                          icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: continue
    folium_static(m, height=500, width=850)

with col_info:
    st.write("🚉 選擇車站")
    sel_st = st.selectbox("", list(STATION_COORDS.keys()), index=1, label_visibility="collapsed")
    
    if token:
        # 這裡放置即時進站邏輯...
        st.markdown('<div class="info-card"><div class="card-label">預計抵達時間</div><div class="card-value">即時進站</div></div>', unsafe_allow_html=True)

# --- F. 底部留言 ---
st.markdown(f"""
<div class="info-card">
    <div class="card-label">✍️ 作者留言：</div>
    <div class="card-value" style="font-size: 1.1em !important;">
    各位親朋好友們，不準的話可以私訊 IG 跟我講，資料由 TDX 平台提供，僅供參考。
    </div>
</div>
""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
