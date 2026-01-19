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
st.set_page_config(page_title="高雄輕軌監測", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體處理 ---
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

# --- B. 樣式修復 (V5.4 強化版) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    {font_css}
    
    .stApp {{ background-color: #0e1117 !important; color: white !important; }}

    /* 標題放大 */
    .custom-title {{
        font-family: 'HandWrite' !important;
        font-size: clamp(38px, 12vw, 64px);
        color: #a5d6a7;
        text-align: center;
        margin: 30px 0;
        line-height: 1.2;
    }}

    .legend-box {{ 
        font-family: 'Zen Maru Gothic' !important; 
        background-color: #1a1d23; border-radius: 12px; padding: 12px; margin-bottom: 25px; 
        display: flex; justify-content: center; gap: 15px; border: 1px solid #30363d;
    }}

    /* 卡片樣式 */
    .info-card {{
        background-color: #1a1d23;
        border: 1px solid #444;
        border-radius: 15px;
        padding: 22px;
        margin-top: 25px; /* 這裡增加間距 */
        margin-bottom: 20px;
    }}

    .card-label {{ font-family: 'Zen Maru Gothic' !important; color: #81c784; font-size: 20px; margin-bottom: 12px; font-weight: bold; }}
    .card-content {{ font-family: 'HandWrite' !important; font-size: 30px; color: #ffffff; line-height: 1.4; }}
    
    /* 座標狀態文字 */
    .status-text {{
        font-family: 'Zen Maru Gothic' !important;
        font-size: 0.95em; 
        color: #aaa; 
        margin-top: 15px; 
        line-height: 1.8;
    }}

    /* 紅點波源極大化 */
    @keyframes sonar {{
        0% {{ transform: scale(1); opacity: 1; }}
        100% {{ transform: scale(10); opacity: 0; }}
    }}
    .gps-marker {{
        width: 24px; height: 24px; background: #ff1f1f; border-radius: 50%;
        border: 3px solid #fff; position: relative; box-shadow: 0 0 15px #ff1f1f;
    }}
    .gps-marker::after {{
        content: ""; position: absolute; width: 100%; height: 100%;
        border-radius: 50%; background: #ff1f1f;
        animation: sonar 1.0s infinite ease-out; top: -3px; left: -3px;
    }}
</style>
""", unsafe_allow_html=True)

# --- C. 定位邏輯 ---
user_pos = None
loc = get_geolocation()
if loc:
    user_pos = [loc['coords']['latitude'], loc['coords']['longitude']]
    dists = []
    for i, (name, coord) in enumerate(STATION_COORDS.items()):
        dists.append((i, haversine(user_pos[0], user_pos[1], coord[0], coord[1])))
    st.session_state.nearest_st_idx = min(dists, key=lambda x: x[1])[0]

# --- D. API 數據 ---
def get_tdx():
    try:
        cid = st.secrets["TD_ID_NEW"]
        csk = st.secrets["TD_SECRET_NEW"]
        tk = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                           data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}).json().get('access_token')
        res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                           headers={'Authorization': f'Bearer {tk}'}).json()
        pos_data = res.get('LivePositions', []) if isinstance(res, dict) else res
        return pos_data, tk
    except: return [], None

live_pos, token = get_tdx()

# --- E. UI 渲染 ---
st.markdown('<div class="custom-title">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-box">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13, tiles="cartodb voyager")
    if user_pos:
        folium.Marker(
            location=user_pos,
            icon=folium.DivIcon(html='<div class="gps-marker"></div>'),
            z_index_offset=3000
        ).add_to(m)
    
    if live_pos:
        for t in live_pos:
            try:
                coords = [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']]
                folium.Marker(coords, icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
            except: continue
    folium_static(m, height=500, width=900)

with col_info:
    st.markdown('<div class="card-label">🚉 選擇車站</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("車站列表", list(STATION_COORDS.keys()), index=st.session_state.get('nearest_st_idx', 0), label_visibility="collapsed")
    tid = sel_st.split()[0]

    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                                 headers={'Authorization': f'Bearer {token}'}).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999)):
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'<div class="info-card" style="margin-top:10px;"><div class="card-label">預計抵達時間</div><div class="card-content">{msg}</div></div>', unsafe_allow_html=True)
            else: st.info("⌛ 暫無列車資訊")
        except: pass

    tz = pytz.timezone('Asia/Taipei')
    now_t = datetime.datetime.now(tz).strftime("%Y/%m/%d %H:%M:%S")
    coords_txt = f"[{user_pos[0]:.6f}, {user_pos[1]:.6f}]" if user_pos else "讀取中..."
    st.markdown(f'<div class="status-text">📍 更新時間：{now_t}<br>🛰️ 目前座標：{coords_txt}</div>', unsafe_allow_html=True)

# --- F. 底部留言與更新 ---
st.markdown(f"""
<div class="info-card">
    <div class="card-label"><b>✍️ 作者留言：</b></div>
    <div class="card-content" style="font-size: 1.3em;">各位親朋好友們，不準的話可以私訊 IG 跟我講，資料由 TDX 平台提供，僅供參考。</div>
</div>
<div class="info-card">
    <div class="card-label"><b>📦 版本更新紀錄 (V5.4)：</b></div>
    <div style="font-family: 'Zen Maru Gothic'; font-size: 15px; color: #abb2bf; line-height: 1.8;">
        • <b>版面間距優化</b>：在座標讀取與下方卡片間增加顯著間距，提升觀感。<br>
        • <b>定位波源強化</b>：紅點核心與波紋範圍極大化，確保地圖顯示清晰。<br>
        • <b>樣式修正</b>：修復標籤閉合問題，標題與內文字體粗細已恢復正常。
    </div>
</div>
""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
