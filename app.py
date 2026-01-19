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
st.set_page_config(page_title="高雄輕軌監測系統", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體載入 (手寫體處理) ---
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

# --- B. CSS 樣式 (包含新加入的方向標籤樣式) ---
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
    .dir-label {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #ffd54f; font-size: 15px; font-weight: bold; margin: 12px 0 5px 0; border-left: 4px solid #ffd54f; padding-left: 8px; }}
    .label-round {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #81c784; font-size: 14px; margin-bottom: 2px; }}
    .content-hand {{ font-family: 'MyHand', sans-serif !important; font-size: 24px; }}
    .status-text-left {{ font-family: 'Zen Maru Gothic', sans-serif !important; text-align: left; color: #718096; font-size: 12px; margin-top: 2px; }}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-title">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

# --- C. 資料處理邏輯 ---
user_loc = get_geolocation()
user_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc else None

def get_tdx_token():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                           data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk})
        return res.json().get('access_token')
    except: return None

token = get_tdx_token()

col_map, col_info = st.columns([7, 3.5])

with col_map:
    center = user_pos if user_pos else [22.6593, 120.2868]
    m = folium.Map(location=center, zoom_start=15)
    if user_pos:
        folium.CircleMarker(user_pos, radius=7, color='white', weight=2, fill=True, fill_color='red', fill_opacity=1).add_to(m)
    
    if token:
        try:
            pos_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                                   headers={'Authorization': f'Bearer {token}'}).json()
            live_data = pos_res if isinstance(pos_res, list) else pos_res.get('LivePositions', [])
            for t in live_data:
                p_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color=p_color, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=800)

with col_info:
    st.markdown('<div class="label-round">🚉 監測車站</div>', unsafe_allow_html=True)
    stations = {"C21 美術館": "C21", "C24 愛河之心": "C24", "C1 籬仔內": "C1", "C14 哈瑪星": "C14"}
    sel_st_label = st.selectbox("", list(stations.keys()), index=0, label_visibility="collapsed")
    tid = stations[sel_st_label]
    
    if token:
        try:
            b_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON"
            b_res = requests.get(b_url, headers={'Authorization': f'Bearer {token}'}).json()
            
            if isinstance(b_res, list) and len(b_res) > 0:
                # --- 智慧分流與容錯邏輯 ---
                dir0 = [i for i in b_res if i.get('Direction') == 0]
                dir1 = [i for i in b_res if i.get('Direction') == 1]
                
                # 保險機制：如果過濾後兩邊都空了，就取消過濾直接顯示，避免空白
                fallback_mode = False
                if not dir0 and not dir1:
                    dir0 = b_res[:2] # 取前兩筆
                    fallback_mode = True

                def draw_ui(data_list, title, is_fallback=False):
                    display_title = "📅 即將進站班次" if is_fallback else title
                    st.markdown(f'<div class="dir-label">{display_title}</div>', unsafe_allow_html=True)
                    if not data_list:
                        st.markdown('<div class="info-card"><div class="content-hand" style="font-size:16px; color:#718096;">暫無資訊</div></div>', unsafe_allow_html=True)
                    else:
                        for item in sorted(data_list, key=lambda x: x.get('EstimateTime', 999))[:1]:
                            est = int(item.get('EstimateTime', 0))
                            dest = item.get('DestinationStationName', {}).get('Zh_tw', '調度中')
                            msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                            text_style = 'color: #ff5252 !important;' if est <= 2 else 'color: #ffffff;'
                            st.markdown(f'''
                                <div class="info-card">
                                    <div class="content-hand" style="{text_style}">{msg}</div>
                                    <div style="font-size:12px; color:#718096; font-family: "Zen Maru Gothic";">往 {dest}</div>
                                </div>
                            ''', unsafe_allow_html=True)

                if fallback_mode:
                    draw_ui(dir0, "", is_fallback=True)
                else:
                    draw_ui(dir0, "🟢 順行方向")
                    draw_ui(dir1, "🔵 逆行方向")
            else:
                st.markdown('<div class="info-card"><div class="content-hand" style="font-size:16px; color:#718096;">🚉 此站暫無即時班次資訊</div></div>', unsafe_allow_html=True)
        except: st.write("連線異常，請稍後...")

    now_t = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%H:%M:%S")
    st.markdown(f'<div class="status-text-left">📍 更新時間：{now_t}</div>', unsafe_allow_html=True)

# --- D. 底部區塊 ---
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
col_msg, col_log = st.columns([1, 1.2])
with col_msg:
    st.markdown('<div class="info-card"><div class="label-round">✍️ 開發心得</div><div class="content-hand" style="font-size: 18px;">克服了環狀線資料轉換的斷點問題，實作了具備容錯能力的即時看板。</div></div>', unsafe_allow_html=True)
with col_log:
    st.markdown(f"""<div class="info-card"><div class="label-round">📦 技術進度</div><div class="update-log-box">
    • <b>智慧分流：</b>優先解析 Direction 標籤，失效時自動切換為全導向模式。<br>
    • <b>穩定性提升：</b>解決了地圖有車但看板空白的邏輯衝突。</div></div>""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
