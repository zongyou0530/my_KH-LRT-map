import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import base64
import os
import time

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體載入 ---
font_path = "ZONGYOOOOOOU1.otf"
handwriting_font = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    handwriting_font = f"""
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{data}) format('opentype');
    }}
    """

st.markdown(f"""
<style>
    /* 匯入 Google 字體 Zen Old Mincho */
    @import url('https://fonts.googleapis.com/css2?family=Zen+Old+Mincho&display=swap');
    {handwriting_font}

    /* 全域背景保持深色 */
    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}
    .block-container {{ padding-top: 1rem; }}

    /* 1. 網頁標題：強制手寫體 */
    .main-title {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 42px;
        color: #a5d6a7;
        text-align: center;
        margin-bottom: 5px;
    }}

    /* 2. 圖例：使用 Zen Old Mincho */
    .legend-text {{
        font-family: 'Zen Old Mincho', serif !important;
        font-size: 18px;
        text-align: center;
        margin-bottom: 20px;
    }}

    /* 3. 卡片設計：找回背景顏色與陰影 */
    .info-card {{
        background-color: #1a1d23;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}

    /* 卡片內的標籤 (例如：預計抵達時間) */
    .card-label {{
        font-family: 'Zen Old Mincho', serif;
        color: #81c784;
        font-size: 18px;
        margin-bottom: 10px;
    }}

    /* 4. 卡片內的時間數字/內容：強制手寫體 */
    .card-content-hand {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 32px;
        color: #ffffff;
    }}

    /* 5. 作者留言內文：強制手寫體 */
    .author-text {{
        font-family: 'MyHand', sans-serif !important;
        font-size: 22px;
        line-height: 1.5;
    }}
</style>
""", unsafe_allow_html=True)

# --- B. 介面呈現 ---

# 網頁標題
st.markdown('<div class="main-title">高雄輕軌 即時位置監測</div>', unsafe_allow_html=True)

# 圖例 (Zen Old Mincho)
st.markdown('<div class="legend-text">🟢 順行 | 🔵 逆行 | 🔴 目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

# 車站座標 (範例)
STATION_COORDS = {"C1 籬仔內": [22.6015, 120.3204], "C20 台鐵美術館": [22.6500, 120.2868], "C21 美術館": [22.6593, 120.2868]}

with col_map:
    m = folium.Map(location=[22.6593, 120.2868], zoom_start=14, tiles="cartodb voyager")
    # 此處應有讀取 API 標記地圖的程式碼...
    folium_static(m, height=500, width=800)

with col_info:
    st.markdown('<p style="font-family:Zen Old Mincho; color:#81c784;">🚉 選擇車站</p>', unsafe_allow_html=True)
    sel_st = st.selectbox("", list(STATION_COORDS.keys()), index=1, label_visibility="collapsed")
    
    # 預計抵達時間卡片
    st.markdown(f"""
    <div class="info-card">
        <div class="card-label">預計抵達時間</div>
        <div class="card-content-hand">即時進站</div>
    </div>
    <div class="info-card">
        <div class="card-label">預計抵達時間</div>
        <div class="card-content-hand">約 4 分鐘</div>
    </div>
    """, unsafe_allow_html=True)

# 作者留言區
st.markdown(f"""
<div class="info-card">
    <div class="card-label">✍️ 作者留言：</div>
    <div class="author-text">
    各位親朋好友們，不準的話可以私訊 IG 跟我講，資料由 TDX 平台提供，僅供參考。
    </div>
</div>
""", unsafe_allow_html=True)

# 自動更新
time.sleep(30)
st.rerun()
