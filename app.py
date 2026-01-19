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

# 1. 頁面配置：必須是第一個 Streamlit 指令
st.set_page_config(page_title="高雄輕軌監測", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體與基礎樣式修復 (包含解決頂部白邊) ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_base64 = base64.b64encode(f.read()).decode()
    font_css = f"@font-face {{ font-family: 'HandWrite'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}"

st.markdown(f"""
<style>
    {font_css}
    /* 強制移除 Streamlit 頂部預設空白 */
    .block-container {{ padding-top: 1rem !important; padding-bottom: 0rem !important; }}
    .stApp {{ background-color: #0e1117 !important; color: white !important; }}
    
    /* 標題嚴格格式：兩行等大，手寫體 */
    .custom-header {{ 
        font-family: 'HandWrite', sans-serif !important; 
        font-size: 38px !important; 
        color: #a5d6a7 !important; 
        text-align: center; 
        margin: 0px 0px 10px 0px; 
        line-height: 1.3; 
        font-weight: normal;
    }}

    .legend-box {{ font-family: sans-serif !important; background-color: #1a1d23; border-radius: 8px; padding: 8px; margin-bottom: 12px; display: flex; justify-content: center; gap: 10px; border: 1px solid #30363d; font-size: 0.9em; }}
    .info-card {{ background-color: #1a1d23; border: 1px solid #30363d; border-radius: 12px; padding: 12px; margin-bottom: 10px; }}
    .card-label {{ color: #81c784; font-size: 16px; font-weight: bold; margin-bottom: 5px; }}
    .card-content {{ font-family: 'HandWrite' !important; font-size: 26px; color: #ffffff; line-height: 1.2; }}
    .urgent-text {{ color: #ff5252 !important; }}
    .status-text {{ font-size: 0.85em; color: #888; margin-top: 8px; }}
</style>
""", unsafe_allow_html=True)

# --- B. 核心功能函式 ---
STATION_COORDS = {{
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
}}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_tdx():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        tk = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                           data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}).json().get('access_token')
        res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                           headers={'Authorization': f'Bearer {tk}'}).json()
        return (res.get('LivePositions', []) if isinstance(res, dict) else res), tk
    except: return [], None

# --- C. 主頁面渲染 ---
# 1. 標題與圖例 (在最上方顯示)
st.markdown('<div class="custom-header">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-box">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

# 定位獲取
loc = get_geolocation()
user_pos = [loc['coords']['latitude'], loc['coords']['longitude']] if loc else None

# 自動尋找最近車站
if user_pos and 'nearest_st_idx' not in st.session_state:
    dists = [(i, haversine(user_pos[0], user_pos[1], coord[0], coord[1])) for i, coord in enumerate(STATION_COORDS.values())]
    st.session_state.nearest_st_idx = min(dists, key=lambda x: x[1])[0]

# --- D. 內容顯示區塊 ---
col_map, col_info = st.columns([7, 3])

with col_map:
    # 預設地圖中心點
    map_center = list(STATION_COORDS.values())[st.session_state.get('nearest_st_idx', 20)]
    m = folium.Map(location=map_center, zoom_start=15, tiles="cartodb voyager")
    
    if user_pos:
        folium.Circle(user_pos, radius=25, color='white', weight=2, fill=True, fill_color='red', fill_opacity=1).add_to(m)
        folium.Circle(user_pos, radius=150, color='red', weight=1, fill=True, fill_opacity=0.2).add_to(m)
    
    live_pos, token = get_tdx()
    for t in live_pos:
        try:
            folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                          icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: continue
    folium_static(m, height=450, width=900)

with col_info:
    st.markdown('<div class="card-label">🚉 選擇車站</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("車站", list(STATION_COORDS.keys()), index=st.session_state.get('nearest_st_idx', 0), key="st_select", label_visibility="collapsed")
    tid = sel_st.split()[0]

    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                                 headers={'Authorization': f'Bearer {token}'}).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999)):
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'<div class="info-card"><div class="card-label">預計抵達時間</div><div class="card-content {"urgent-text" if est <= 2 else ""}">{msg}</div></div>', unsafe_allow_html=True)
            else: st.info("⌛ 暫無列車資訊")
        except: pass

    now_t = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%H:%M:%S")
    st.markdown(f'<div class="status-text">📍 更新時間：{now_t} (每30秒更新)</div>', unsafe_allow_html=True)

# 頁尾留言
st.markdown('<hr style="border-color:#444">', unsafe_allow_html=True)
st.markdown('<div class="info-card"><div class="card-label">✍️ 作者留言：</div><div class="card-content" style="font-size: 1.1em;">各位親朋好友們，不準的話可以私訊 IG 跟我講，資料由 TDX 平台提供，僅供參考。</div></div>', unsafe_allow_html=True)

# --- E. 自動更新觸發器 ---
# 使用 time.sleep(30) 後 rerun，這是 Streamlit 最穩定的自動刷新方式
time.sleep(30)
st.rerun()
