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
        dist_results = []
        for st_id, coords in STATION_COORDS.items():
            dist = haversine(user_pos[0], user_pos[1], coords[0], coords[1])
            dist_results.append((st_id, dist))
        dist_results.sort(key=lambda x: x[1])
        target_id = dist_results[0][0]
        map_center = STATION_COORDS[target_id]
        map_zoom = 15
        st_ids = list(STATION_COORDS.keys())
        closest_st_index = st_ids.index(target_id)
        st.session_state.auto_located = True

# --- C. 時間處理 ---
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
        '''
    except: pass

st.markdown(f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&display=swap');
    {font_css}
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
    }}
    
    /* 標題與副標 */
    .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 42px; color: #a5d6a7; text-align: center; margin-bottom: 0px; }}
    .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 14px; color: #888; text-align: center; margin-bottom: 20px; }}

    /* 警示框修正 */
    @keyframes blink-red {{
        0% {{ border: 2px solid #ff5252; opacity: 1; }}
        50% {{ border: 2px solid transparent; opacity: 0.7; }}
        100% {{ border: 2px solid #ff5252; opacity: 1; }}
    }}
    .quota-exceeded-box {{
        background-color: #2c1616 !important;
        color: #ffbaba !important;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-family: 'ZongYouFont' !important;
        font-size: 20px;
        margin: 10px auto;
        animation: blink-red 1.5s infinite;
        border: 2px solid #ff5252;
    }}

    /* 圖標說明間距修正 */
    .legend-box {{ 
        font-size: 13px !important; 
        margin-top: 20px !important; 
        margin-bottom: 15px !important; 
        display: flex; 
        justify-content: center; 
        gap: 15px;
        padding: 8px !important;
        background-color: #212d3d !important;
        border-radius: 10px;
    }}

    /* 留言板背景修正 */
    .footer-box {{ 
        background-color: #1a1d23 !important; 
        border: 1px solid #30363d !important; 
        border-radius: 10px; 
        padding: 15px 20px; 
        margin-top: 15px !important;
        display: block !important;
    }}
    .footer-title {{ font-size: 1.1em; font-weight: bold; color: #eee; margin-bottom: 5px; }}
    .footer-content {{ font-family: 'ZongYouFont' !important; color: #abb2bf; font-size: 1.1em; }}

    .paper-card {{ background-color: #1a1d23; border-left: 5px solid #4caf50; padding: 12px; margin-bottom: 10px; border-radius: 5px; }}
</style>
''', unsafe_allow_html=True)

# 3. Token 與 強力點數檢測
@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TD_ID"], 'client_secret': st.secrets["TD_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# 為了確保抓到，我們在這邊執行一次不帶 cache 的測試
token = get_token()
quota_exceeded = False
try:
    test_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=1'
    t_res = requests.get(test_url, headers={'Authorization': f'Bearer {token}'}, timeout=5)
    # 如果看到 401, 403, 429 或者內容包含 Quota，就判定耗盡
    if t_res.status_code != 200 or "Quota" in t_res.text or "limit" in t_res.text:
        quota_exceeded = True
except:
    quota_exceeded = True

# --- UI 渲染 ---
st.markdown('<div class="custom-title">高雄輕軌 即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="credit-text">zongyou x gemini</div>', unsafe_allow_html=True)

# 1. 警示區
if quota_exceeded:
    st.markdown('<div class="quota-exceeded-box">因訪問人數太多，我這個月TDX的免費點數已耗盡<br>請下個月再來 😭</div>', unsafe_allow_html=True)

# 2. 圖標說明 (增加 margin 避免貼齊)
st.markdown('<div class="legend-box">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    # 增加地圖上方的間距
    st.write("") 
    m = folium.Map(location=map_center, zoom_start=map_zoom)
    if user_pos:
        folium.CircleMarker(location=user_pos, radius=8, color='#ff5252', fill=True, fill_color='#ff5252', fill_opacity=0.9).add_to(m)
    
    # 列車位置
    if token and not quota_exceeded:
        try:
            live_data = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_data.get('LivePositions', []):
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=420, width=900)

with col_info:
    st.markdown('<div style="font-family: \'ZongYouFont\'; font-size: 22px; color: #81c784; margin-bottom: 10px;">🚉 車站即時站牌</div>', unsafe_allow_html=True)
    STATION_MAP = {k: k.split()[0] for k in STATION_COORDS.keys()} # 簡化對應
    # 這裡沿用您原本的 Selectbox 邏輯...
    sel_st = st.selectbox("選擇車站", list(STATION_COORDS.keys()), index=closest_st_index)
    
    if quota_exceeded:
        st.info("⌛ 點數耗盡，暫時無法獲取到站時間")
    else:
        st.write("📡 資料讀取中...")

# --- 3. 留言板背景修正 (使用直接的 HTML) ---
st.markdown(f'''
<div class="footer-box">
    <div class="footer-title">✍️ 作者留言：</div>
    <div class="footer-content">
        各位親朋好友們，拜託請幫我看看到底準不準，不準的話可以搜尋ig跟我講謝謝。資料由 TDX 平台提供，僅供參考。
    </div>
</div>

<div class="footer-box">
    <div class="footer-title">📦 版本更新紀錄 (V3.8) ：</div>
    <div style="color: #abb2bf; font-size: 14px;">
        • 修正 CSS 覆蓋問題，確保留言板背景正常顯示。<br>
        • 調整 UI 間距，防止圖標說明與地圖重疊。<br>
        • 強化點數耗盡偵測與閃爍警示顯示邏輯。
    </div>
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
