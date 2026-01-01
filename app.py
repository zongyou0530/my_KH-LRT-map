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
        target_id_full = dist_results[0][0]
        map_center = STATION_COORDS[target_id_full]
        map_zoom = 15
        st_ids = list(STATION_COORDS.keys())
        closest_st_index = st_ids.index(target_id_full)
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
        font_css = f"@font-face {{ font-family: 'ZongYouFont'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}"
    except: pass

st.markdown(f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&display=swap');
    {font_css}
    
    html, body, [data-testid="stAppViewContainer"], p, span, label, div {{
        font-family: 'Zen Maru Gothic', 'ZongYouFont', sans-serif !important;
        font-weight: 500 !important;
    }}

    .custom-title {{ font-family: 'ZongYouFont' !important; font-size: clamp(32px, 8vw, 44px); color: #a5d6a7; text-align: center; line-height: 1.2; margin-bottom: 5px; }}
    .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 14px; color: #888; text-align: center; margin-bottom: 20px; letter-spacing: 2px; }}

    .quota-exceeded-box {{
        background-color: #2c1616 !important;
        border: 2px solid #ff5252;
        color: #ffbaba;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-family: 'ZongYouFont' !important;
        font-size: 20px;
        margin: 15px auto;
        animation: blink 2s infinite;
    }}
    @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}

    .legend-box {{ background-color: #212d3d; border-radius: 10px; padding: 10px; margin: 10px 0 15px 0; display: flex; justify-content: center; gap: 15px; font-size: 14px; }}
    .paper-card {{ background-color: #1a1d23; border-left: 5px solid #4caf50; padding: 12px; margin-bottom: 10px; border-radius: 8px; }}
    .arrival-text {{ font-family: 'ZongYouFont' !important; font-size: 24px; color: #fff; }}
    
    .footer-box {{ background-color: #1a1d23 !important; border: 1px solid #30363d !important; border-radius: 12px; padding: 18px; margin-top: 15px; }}
</style>
''', unsafe_allow_html=True)

# --- E. 跨月點數偵測 ---
def get_token_fresh():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TD_ID"], 'client_secret': st.secrets["TD_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

token = get_token_fresh()
quota_exceeded = False

if token:
    try:
        test_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=1', headers={'Authorization': f'Bearer {token}'}, timeout=5)
        if test_res.status_code != 200 or "Quota" in test_res.text:
            quota_exceeded = True
    except: quota_exceeded = True
else: quota_exceeded = True

# --- UI 渲染 ---
st.markdown(f'<div class="custom-title">高雄輕軌 即時位置監測</div>', unsafe_allow_html=True)
st.markdown(f'<div class="credit-text">zongyou x gemini</div>', unsafe_allow_html=True)

if quota_exceeded:
    st.markdown('<div class="quota-exceeded-box">因訪問人數太多，我這個月TDX的免費點數已耗盡<br>請下個月再來 😭</div>', unsafe_allow_html=True)

st.markdown('<div class="legend-box">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=map_center, zoom_start=map_zoom)
    if user_pos:
        folium.CircleMarker(location=user_pos, radius=8, color='#ff5252', fill=True, fill_color='#ff5252', fill_opacity=0.9).add_to(m)
    
    if token and not quota_exceeded and is_running:
        try:
            live_data = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_data.get('LivePositions', []):
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=420, width=900)

with col_info:
    st.markdown('<div style="font-family: \'ZongYouFont\'; font-size: 22px; color: #81c784; margin-bottom: 10px;">🚉 車站即時站牌</div>', unsafe_allow_html=True)
    sel_st_full = st.selectbox("選擇車站", list(STATION_COORDS.keys()), index=closest_st_index, label_visibility="collapsed")
    target_id = sel_st_full.split()[0]

    if token and not quota_exceeded:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", headers={'Authorization': f'Bearer {token}'})
            matched = [d for d in resp.json() if d.get('StationID') == target_id and d.get('EstimateTime') is not None]
            if matched:
                matched.sort(key=lambda x: x.get('EstimateTime', 999))
                for item in matched:
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'<div class="paper-card"><div style="color:#4caf50; font-size:12px; margin-bottom:4px;">預計抵達時間</div><div class="arrival-text">{msg}</div></div>', unsafe_allow_html=True)
            else: st.info("⌛ 暫無列車資訊")
        except: st.info("📡 資料讀取中...")
    
    # --- 找回遺失的資訊欄位 ---
    st.markdown(f'''
    <div style="font-size: 0.85em; color: #888; margin-top:20px; line-height: 1.8; border-top: 1px solid #333; padding-top: 10px;">
        📍 更新時間：{time_display}<br>
        🛰️ 目前座標：{user_pos if user_pos else "定位中..."}
    </div>
    ''', unsafe_allow_html=True)

# --- 底部留言板 ---
st.markdown(f'''
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:5px;">✍️ 作者留言：</div>
    <div style="font-family:'ZongYouFont'; color:#abb2bf; font-size:1.1em;">各位親朋好友們，拜託請幫我看看到底準不準，不準的話可以搜尋ig跟我講謝謝。資料由 TDX 平台提供，僅供參考。</div>
</div>
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:5px;">📦 版本更新紀錄 (V4.0) ：</div>
    <div style="color:#abb2bf; font-size:14px;">
        • <b>資訊欄修復</b>：找回遺失的更新時間與座標顯示。<br>
        • <b>跨月同步</b>：因應 2026/01/01 更新 Token 抓取機制。<br>
        • <b>UI 微調</b>：優化右側資訊欄的間距與圓體文字層次。
    </div>
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
