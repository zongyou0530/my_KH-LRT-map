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

# --- A. 車站座標數據 ---
STATION_COORDS = {
    "C1": [22.6015, 120.3204], "C2": [22.6026, 120.3168], "C3": [22.6025, 120.3117], "C4": [22.6033, 120.3060],
    "C5": [22.6000, 120.3061], "C6": [22.6052, 120.3021], "C7": [22.6075, 120.2989], "C8": [22.6105, 120.2982],
    "C9": [22.6133, 120.2965], "C10": [22.6186, 120.2933], "C11": [22.6225, 120.2885], "C12": [22.6200, 120.2842],
    "C13": [22.6214, 120.2798], "C14": [22.6218, 120.2730], "C15": [22.6268, 120.2738], "C16": [22.6311, 120.2758],
    "C17": [22.6358, 120.2778], "C18": [22.6398, 120.2795], "C19": [22.6455, 120.2835], "C20": [22.6500, 120.2868],
    "C21A": [22.6548, 120.2861], "C21": [22.6593, 120.2868], "C22": [22.6622, 120.2915], "C23": [22.6603, 120.2982],
    "C24": [22.6586, 120.3032], "C25": [22.6575, 120.3105], "C26": [22.6535, 120.3155], "C27": [22.6515, 120.3205],
    "C28": [22.6465, 120.3235], "C29": [22.6415, 120.3275], "C30": [22.6365, 120.3305], "C31": [22.6315, 120.3315],
    "C32": [22.6265, 120.3305], "C33": [22.6222, 120.3285], "C34": [22.6175, 120.3275], "C35": [22.6135, 120.3275],
    "C36": [22.6085, 120.3265], "C37": [22.6045, 120.3245]
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# --- B. 自動定位邏輯 ---
if 'auto_located' not in st.session_state:
    st.session_state.auto_located = False

map_center = [22.6280, 120.3014]
map_zoom = 13
closest_st_index = 19
user_pos = None

loc = get_geolocation()
if loc:
    user_pos = [loc['coords']['latitude'], loc['coords']['longitude']]
    if not st.session_state.auto_located:
        min_dist = float('inf')
        target_id = "C20"
        for st_id, coords in STATION_COORDS.items():
            dist = haversine(user_pos[0], user_pos[1], coords[0], coords[1])
            if dist < min_dist:
                min_dist, target_id = dist, st_id
        map_center = STATION_COORDS[target_id]
        map_zoom = 15
        st_ids = list(STATION_COORDS.keys())
        closest_st_index = st_ids.index(target_id)
        st.session_state.auto_located = True

# --- C. 時間處理 (2025年12月22日 17:23:30) ---
tz = pytz.timezone('Asia/Taipei')
now = datetime.datetime.now(tz)
is_running = (now.hour > 6 or (now.hour == 6 and now.minute >= 30)) and (now.hour < 22 or (now.hour == 22 and now.minute <= 30))
time_display = now.strftime("%Y年%m月%d日 %H:%M:%S")

# --- D. 字體與 CSS ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode()
        font_css = f'''
        @font-face {{ font-family: 'ZongYouFont'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 64px; color: #a5d6a7; text-align: center; line-height: 1.05; margin-bottom: 2px; }}
        .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 18px; color: #888; text-align: center; margin-bottom: 20px; letter-spacing: 2px; }}
        .st-label-zong {{ font-family: 'ZongYouFont' !important; font-size: 26px; color: #81c784; margin-bottom: 10px; }}
        .green-tag-box {{ background-color: #2e7d32; color: white !important; font-size: 13px; padding: 1px 8px; border-radius: 4px; display: inline-block; margin-bottom: 4px; font-family: 'ZongYouFont' !important; }}
        .arrival-text {{ font-family: 'ZongYouFont' !important; font-size: 32px !important; line-height: 1.1; }}
        
        /* 底部留言板優化：深色背景，無鮮豔邊框 */
        .footer-box {{
            background-color: #1a1d23;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 15px 20px;
            margin-top: 12px;
        }}
        .footer-title {{ font-size: 1.05em; font-weight: bold; margin-bottom: 5px; display: flex; align-items: center; gap: 8px; color: #eee; }}
        .footer-content {{ color: #abb2bf; line-height: 1.6; font-size: 0.9em; }}
        '''
    except: pass

st.markdown(f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&display=swap');
    {font_css}
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMarkdownContainer"], p, span, div, select, button, label {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
        font-weight: 500 !important;
    }}
    .stInfo {{ background-color: #212d3d !important; color: #b0c4de !important; border: 1px solid #3d4d5e !important; border-radius: 12px !important; }}
    .paper-card {{ background-color: #1a1d23; border: 1px solid #2d333b; border-left: 5px solid #4caf50; border-radius: 8px; padding: 12px 18px; margin-bottom: 10px; }}
    
    @keyframes pulse {{
        0% {{ transform: scale(0.1); opacity: 0; }}
        50% {{ opacity: 0.5; }}
        100% {{ transform: scale(1.2); opacity: 0; }}
    }}
    .pulse-circle {{ border: 4px solid #ff5252; border-radius: 50%; animation: pulse 2s infinite ease-out; }}
</style>
''', unsafe_allow_html=True)

# 3. 數據定義
STATION_MAP = {
    "C1 籬仔內": "C1", "C2 凱旋瑞田": "C2", "C3 前鎮之星": "C3", "C4 凱旋中華": "C4", "C5 夢時代": "C5",
    "C6 經貿園區": "C6", "C7 軟體園區": "C7", "C8 高雄展覽館": "C8", "C9 旅運中心": "C9", "C10 光榮碼頭": "C10",
    "C11 真愛碼頭": "C11", "C12 駁二大義": "C12", "C13 駁二蓬萊": "C13", "C14 哈瑪星": "C14", "C15 壽山公園": "C15",
    "C16 文武聖殿": "C16", "C17 鼓山區公所": "C17", "C18 鼓山": "C18", "C19 馬卡道": "C19", "C20 台鐵美術館": "C20",
    "C21A 內維中心": "C21A", "C21 美術館": "C21", "C22 聯合醫院": "C22", "C23 龍華國小": "C23", "C24 愛河之心": "C24",
    "C25 新上國小": "C25", "C26 灣仔內": "C26", "C27 鼎山街": "C27", "C28 高雄高工": "C28", "C29 樹德家商": "C29",
    "C30 科工館": "C30", "C31 聖功醫院": "C31", "C32 凱旋公園": "C32", "C33 衛生局": "C33", "C34 五權國小": "C34",
    "C35 凱旋武昌": "C35", "C36 凱旋二聖": "C36", "C37 輕軌機廠": "C37"
}

@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

token = get_token()

# --- UI 渲染 ---
st.markdown('<div class="custom-title">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="credit-text">zongyou x gemini</div>', unsafe_allow_html=True)

st.info("📍 地圖標示：🟢 順行  | 🔵 逆行 | 🔴 您目前的位置")

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=map_center, zoom_start=map_zoom)
    if user_pos:
        folium.CircleMarker(location=user_pos, radius=8, color='#ff5252', fill=True, fill_color='#ff5252', fill_opacity=0.9).add_to(m)
        folium.Marker(location=user_pos, icon=folium.DivIcon(html='<div class="pulse-circle" style="width: 40px; height: 40px; margin-left: -20px; margin-top: -20px;"></div>')).add_to(m)

    if token and is_running:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_pos.get('LivePositions', []):
                d_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color=d_color, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=900)

with col_info:
    st.markdown('<div class="st-label-zong">🚉 輕軌車站即時站牌</div>', unsafe_allow_html=True)
    sel_st_label = st.selectbox("Station", list(STATION_MAP.keys()), index=closest_st_index, label_visibility="collapsed")
    target_id = STATION_MAP[sel_st_label]

    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", headers={'Authorization': f'Bearer {token}'})
            matched = [d for d in resp.json() if d.get('StationID') == target_id and d.get('EstimateTime') is not None]
            if matched:
                matched.sort(key=lambda x: x.get('EstimateTime', 999))
                for item in matched:
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    color_class = "urgent-red" if est <= 2 else "calm-grey"
                    st.markdown(f'''<div class="paper-card"><div class="green-tag-box">輕軌預計抵達時間</div><div class="arrival-text {color_class}">{msg}</div></div>''', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 資料連線中...")
    
    st.markdown(f'''
    <div style="font-size: 0.8em; color: #888; margin-top:10px; line-height: 1.5;">
        📍 地圖更新：{time_display}<br>
        🕒 站牌更新：{time_display}<br>
        🛰️ 定位座標：{user_pos if user_pos else "定位中..."}
    </div>
    ''', unsafe_allow_html=True)

# --- 底部內容：保留深色區塊，移除鮮豔邊框 ---
st.markdown('---')

st.markdown(f'''
<div class="footer-box">
    <div class="footer-title">✍️ 作者留言：</div>
    <div class="footer-content">
        各位親朋好友們，拜託請幫我看看到底準不準，不準的話可以搜尋ig跟我講謝謝。資料由 TDX 平台提供，僅供參考。
    </div>
</div>

<div class="footer-box">
    <div class="footer-title">📦 版本更新紀錄 (V3.0) ：</div>
    <div class="footer-content">
        • <b>智慧定位核心</b>：首頁自動計算最近車站，地圖中心自動跳轉並放大。<br>
        • <b>雷達紅點標示</b>：新增紅色閃爍點，用於校正實際位置與系統誤差。<br>
        • <b>UI 介面優化</b>：精簡時間顯示，標題字體修正，採用低調深色背景區塊。
    </div>
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
