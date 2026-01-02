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
from streamlit_js_eval import get_geolocation

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

# --- A. 字體與車站數據 ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_base64 = base64.b64encode(f.read()).decode()
    font_css = f"@font-face {{ font-family: 'HandWrite'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}"

STATION_COORDS = {
    "C1 籬仔內": [22.6015, 120.3204], "C2 凱旋瑞田": [22.6026, 120.3168], "C3 前鎮之星": [22.6025, 120.3117], 
    "C4 凱旋中華": [22.6033, 120.3060], "C5 夢時代": [22.6000, 120.3061], "C6 經貿園區": [22.6052, 120.3021], 
    "C7 軟體園區": [22.6075, 120.2989], "C8 高雄展覽館": [22.6105, 120.2982], "C9 旅運中心": [22.6133, 120.2965], 
    "C10 光榮碼頭": [22.6186, 120.2933], "C11 真愛碼頭": [22.6225, 120.2885], "C12 駁二大義": [22.6200, 120.2842],
    "C13 駁二蓬萊": [22.6214, 120.2798], "C14 哈瑪星": [22.6218, 120.2730], "C15 壽山公園": [22.6268, 120.2738], 
    "C16 文武聖殿": [22.6311, 120.2758], "C17 鼓山區公所": [22.6358, 120.2778], "C18 鼓山": [22.6398, 120.2795], 
    "C19 馬卡道": [22.6455, 120.2835], "C20 台鐵美術館": [22.6500, 120.2868], "C21A 內維中心": [22.6548, 120.2861], 
    "C21 美術館": [22.6593, 120.2868], "C22 聯合醫院": [22.6622, 120.2915], "C23 龍華國小": [22.6603, 120.2982],
    "C24 愛河之心": [22.6586, 120.3032], "C25 新上國小": [22.6575, 120.3105], "C26 灣仔內": [22.6535, 120.3155], 
    "C27 鼎山街": [22.6515, 120.3205], "C28 高雄高工": [22.6465, 120.3235], "C29 樹德家商": [22.6415, 120.3275], 
    "C30 科工館": [22.6365, 120.3305], "C31 聖功醫院": [22.6315, 120.3315], "C32 凱旋公園": [22.6265, 120.3305], 
    "C33 衛生局": [22.6222, 120.3285], "C34 五權國小": [22.6175, 120.3275], "C35 凱旋武昌": [22.6135, 120.3275], 
    "C36 凱旋二聖": [22.6085, 120.3265], "C37 輕軌機廠": [22.6045, 120.3245]
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# --- B. 樣式修復 ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&display=swap');
    {font_css}
    
    html, body, [data-testid="stAppViewContainer"], p, span, label, div {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
    }}

    /* 1. 標題修復：禁止換行，自動縮放 */
    .custom-title {{
        font-family: 'HandWrite' !important;
        font-size: clamp(28px, 7vw, 44px);
        color: #a5d6a7;
        text-align: center;
        white-space: nowrap;
        margin: 10px 0;
    }}

    /* 2. 圖標說明字體修復 */
    .legend-box {{ 
        font-family: 'Zen Maru Gothic' !important;
        background-color: #212d3d; border-radius: 10px; padding: 10px; margin-bottom: 15px; 
        display: flex; justify-content: center; gap: 15px; font-size: 14px; 
    }}

    .board-header {{ font-family: 'HandWrite' !important; font-size: 28px; color: #81c784; margin-bottom: 10px; }}
    
    /* 4. 卡片標籤字體修復 */
    .arrival-label {{ font-family: 'HandWrite' !important; color: #4caf50; font-size: 14px; }}
    .arrival-time {{ font-family: 'HandWrite' !important; font-size: 28px; color: #ffffff; }}

    .author-text {{ font-family: 'HandWrite' !important; font-size: 1.25em; color: #abb2bf; }}

    /* 定位水波紋：絲滑廣播感 */
    .pulse {{
        width: 15px; height: 15px; background: #ff5252; border-radius: 50%;
        position: relative; box-shadow: 0 0 10px #ff5252;
    }}
    .pulse::after {{
        content: ""; position: absolute; width: 100%; height: 100%;
        border-radius: 50%; background: #ff5252; opacity: 0.8;
        animation: sonar 1.5s infinite ease-out;
    }}
    @keyframes sonar {{
        0% {{ transform: scale(1); opacity: 0.8; }}
        100% {{ transform: scale(4); opacity: 0; }}
    }}
</style>
""", unsafe_allow_html=True)

# --- C. 自動定位車站邏輯 ---
if 'nearest_st_idx' not in st.session_state:
    st.session_state.nearest_st_idx = 0

user_pos = None
loc = get_geolocation()
if loc:
    user_pos = [loc['coords']['latitude'], loc['coords']['longitude']]
    # 計算最近車站
    dists = []
    for i, (name, coord) in enumerate(STATION_COORDS.items()):
        dists.append((i, haversine(user_pos[0], user_pos[1], coord[0], coord[1])))
    st.session_state.nearest_st_idx = min(dists, key=lambda x: x[1])[0]

# --- D. 數據抓取 (延續 V4.3 暴力刷新) ---
def get_tdx():
    try:
        cid = st.secrets.get("TD_ID_NEW") or st.secrets.get("TD_ID")
        csk = st.secrets.get("TD_SECRET_NEW") or st.secrets.get("TD_SECRET")
        tk_res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                               data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}, timeout=10)
        tk = tk_res.json().get('access_token')
        pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                           headers={'Authorization': f'Bearer {tk}'}, timeout=10).json()
        return pos, tk
    except: return None, None

live_pos, token = get_tdx()

# --- E. UI 渲染 ---
st.markdown('<div class="custom-title">高雄輕軌 即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-box">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if user_pos:
        # 自定義絲滑水波紋 HTML Marker
        icon_html = '<div class="pulse"></div>'
        folium.Marker(user_pos, icon=folium.DivIcon(html=icon_html)).add_to(m)
    
    if token:
        for t in live_pos.get('LivePositions', []):
            folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                          icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
    folium_static(m, height=450, width=900)

with col_info:
    st.markdown('<div class="board-header">🚉 車站即時站牌</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("選擇車站", list(STATION_COORDS.keys()), index=st.session_state.nearest_st_idx, label_visibility="collapsed")
    tid = sel_st.split()[0]

    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                                 headers={'Authorization': f'Bearer {token}'}, timeout=10).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999)):
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'<div class="paper-card"><div class="arrival-label">預計抵達時間</div><div class="arrival-time">{msg}</div></div>', unsafe_allow_html=True)
            else: st.info("⌛ 暫無列車資訊")
        except: pass

    tz = pytz.timezone('Asia/Taipei')
    st.markdown(f'<div style="font-size:0.85em; color:#888; margin-top:20px; border-top:1px solid #333; padding-top:10px;">📍 更新：{datetime.datetime.now(tz).strftime("%H:%M:%S")}<br>🛰️ 座標：{user_pos if user_pos else "定位中..."}</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:8px;">✍️ 作者留言：</div>
    <div class="author-text">各位親朋好友們，拜託請幫我看看到底準不準，不準的話可以搜尋ig跟我講謝謝。資料由 TDX 平台提供，僅供參考。</div>
</div>
""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
