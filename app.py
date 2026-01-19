import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import base64
import os
import time
import datetime
import pytz
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
    .block-container {{ padding-top: 6rem !important; padding-bottom: 2rem !important; }}
    .header-title {{ font-family: 'MyHand', sans-serif !important; font-size: 52px !important; color: #a5d6a7; text-align: center; line-height: 1.1; margin-bottom: 10px !important; }}
    .legend-container {{ font-family: 'Zen Maru Gothic', sans-serif !important; background-color: #1a1d23; border: 1px solid #30363d; border-radius: 15px; padding: 4px 12px; text-align: center; margin: 0 auto 10px auto !important; width: fit-content; font-size: 13px; color: #cccccc; }}
    .info-card {{ background-color: #1a1d23; border: 1px solid #30363d; border-radius: 10px; padding: 10px 15px; margin-bottom: 8px; }}
    .dir-label {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #ffd54f; font-size: 14px; font-weight: bold; margin-bottom: 5px; border-left: 3px solid #ffd54f; padding-left: 8px; }}
    .label-round {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #81c784; font-size: 14px; margin-bottom: 2px; }}
    .content-hand {{ font-family: 'MyHand', sans-serif !important; font-size: 22px; }}
    .update-log-box {{ font-family: 'Zen Maru Gothic', sans-serif !important; font-size: 14px; color: #cbd5e0; line-height: 1.6; text-align: left; }}
    .status-text-left {{ font-family: 'Zen Maru Gothic', sans-serif !important; text-align: left; color: #718096; font-size: 12px; margin-top: 2px; }}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-title">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

# --- C. 抓取資料 ---
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
    center = user_pos if user_pos else [22.6593, 120.2868]
    m = folium.Map(location=center, zoom_start=15)
    if user_pos:
        folium.CircleMarker(user_pos, radius=6, color='white', weight=2, fill=True, fill_color='red', fill_opacity=1).add_to(m)
    live_data, token = get_tdx()
    for t in live_data:
        try:
            folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                          icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: continue
    folium_static(m, height=480, width=800)

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
                # 分別過濾出順行(0)與逆行(1)
                dir0 = [i for i in b_res if i.get('Direction') == 0]
                dir1 = [i for i in b_res if i.get('Direction') == 1]
                
                # 建立一個簡單的顯示函式來避免重複程式碼
                def show_board(data_list, title):
                    st.markdown(f'<div class="dir-label">{title}</div>', unsafe_allow_html=True)
                    if not data_list:
                        st.markdown('<div class="info-card"><div class="content-hand" style="font-size:16px;">目前無列車資訊</div></div>', unsafe_allow_html=True)
                    else:
                        for item in sorted(data_list, key=lambda x: x.get('EstimateTime', 999))[:1]:
                            est = int(item.get('EstimateTime', 0))
                            msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                            text_style = 'color: #ff5252 !important;' if est <= 2 else 'color: #ffffff;'
                            st.markdown(f'<div class="info-card"><div class="content-hand" style="{text_style}">{msg}</div></div>', unsafe_allow_html=True)

                show_board(dir0, "🟢 順行 (往 C24 愛河之心)")
                show_board(dir1, "🔵 逆行 (往 C1 籬仔內)")
        except: pass

    now_t = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%Y/%m/%d %H:%M:%S")
    st.markdown(f'<div class="status-text-left">📍 更新時間：{now_t}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="status-text-left">{"✅ 座標已讀取" if user_pos else "⚠️ 座標讀取中..."}</div>', unsafe_allow_html=True)

# --- D. 底部區塊 ---
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
col_msg, col_log = st.columns([1, 1.2])

with col_msg:
    st.markdown(f'<div class="info-card"><div class="label-round">✍️ 作者留言：</div><div class="content-hand" style="font-size: 18px;">資料由 TDX 提供，順逆行邏輯已修正！</div></div>', unsafe_allow_html=True)

with col_log:
    st.markdown(f"""
    <div class="info-card">
        <div class="label-round">📦 深度技術更新：</div>
        <div class="update-log-box">
            • <b>邏輯分流：</b> 成功解析 JSON 中的 Direction 欄位，將資料過濾為順行(0)與逆行(1)。<br>
            • <b>介面優化：</b> 看板區分為兩個方向，解決當初資料混雜、方向不明的問題。<br>
            • <b>邊界測試：</b> 即使某個方向目前無車，系統也能穩定顯示提示訊息而不當機。
        </div>
    </div>
    """, unsafe_allow_html=True)

time.sleep(30)
st.rerun()
