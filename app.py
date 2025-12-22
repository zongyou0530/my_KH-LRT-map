import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time
import base64
import os

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

# --- 時間邏輯 ---
tz = pytz.timezone('Asia/Taipei')
now = datetime.datetime.now(tz)
is_running = (now.hour > 6 or (now.hour == 6 and now.minute >= 30)) and (now.hour < 22 or (now.hour == 22 and now.minute <= 30))
now_str = now.strftime('%Y-%m-%d %H:%M:%S')

# --- 字體載入 ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode()
        font_css = f'''
        @font-face {{ font-family: 'ZongYouFont'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}
        
        /* 指定位置套用自定義字體 */
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 58px; color: #a5d6a7; text-align: center; margin-bottom: 0px; }}
        .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 16px; color: #666; text-align: center; margin-bottom: 15px; letter-spacing: 2px; }}
        .st-selectbox-label {{ font-family: 'ZongYouFont' !important; font-size: 28px !important; color: #81c784 !important; }}
        .arrival-status {{ font-family: 'ZongYouFont' !important; font-size: 2.2em !important; color: #ff8a65 !important; line-height: 1.2; }}
        '''
    except: pass

# 2. 注入 CSS (美化卡片與標籤)
st.markdown(f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kiwi+Maru:wght@400;500&display=swap');
    {font_css}

    /* 全域預設圓體 */
    html, body, [data-testid="stAppViewContainer"], p, div, span {{
        font-family: 'Kiwi Maru', serif;
        color: #fafafa !important;
    }}

    /* 下拉選單標籤樣式 */
    .selectbox-header {{
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    /* 輕量化卡片與綠色膠囊標籤 */
    .arrival-card {{ 
        background-color: #1c1f26; 
        border: 1px solid #30363d;
        border-left: 6px solid #4caf50;
        border-radius: 12px; 
        padding: 15px; 
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }}
    
    .green-tag {{
        background-color: #2e7d32;
        color: #ffffff !important;
        font-size: 0.75em;
        padding: 3px 10px;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 10px;
        font-family: 'Kiwi Maru', serif;
        font-weight: 500;
    }}

    .update-time-row {{ font-size: 0.8em; color: #888 !important; margin: 4px 0; }}

    /* 鎖死鍵盤 */
    div[data-testid="stSelectbox"] input {{
        pointer-events: none !important;
        user-select: none !important;
    }}

    @media (max-width: 768px) {{ .custom-title {{ font-size: 10vw; }} }}
</style>
''', unsafe_allow_html=True)

# 3. 車站資料與 API
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

# --- UI 開始 ---
st.markdown('<div class="custom-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="credit-text">zongyou x gemini</div>', unsafe_allow_html=True)

st.markdown('<div class="legend-box" style="background-color: #1b2e1b; border: 1px solid #4caf50; padding: 8px; border-radius: 8px; margin-bottom: 15px; display: flex; justify-content: center; gap: 20px; font-size: 0.9em;"><span>🟢 順行 (外圈)</span><span>🔵 逆行 (內圈)</span></div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token and is_running:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_pos.get('LivePositions', []):
                d_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color=d_color, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=950)

with col_info:
    # 選擇車站標題套用 ZongYouFont
    st.markdown('<div class="st-selectbox-label">🚉 選擇車站</div>', unsafe_allow_html=True)
    sel_st_label = st.selectbox("Station", list(STATION_MAP.keys()), index=19, label_visibility="collapsed")
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
                    st.markdown(f'''
                    <div class="arrival-card">
                        <div class="green-tag">輕軌預計抵達時間</div>
                        <div class="arrival-status">{msg}</div>
                    </div>''', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 資料同步中")
    
    st.markdown(f'''
        <div style="margin-top:15px;">
            <div class="update-time-row">📍 地圖更新：{now.strftime("%H:%M:%S")}</div>
            <div class="update-time-row">🕒 站牌更新：{now.strftime("%H:%M:%S")}</div>
        </div>
    ''', unsafe_allow_html=True)

# 底部區塊
st.markdown(f'''
<div style="background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; margin-top: 30px;">
    <div style="color: #ffcc80; font-size: 0.9em; font-weight: bold; margin-bottom: 5px;">✍️ 作者留言：</div>
    <div style="color: #8b949e; font-size: 0.85em; margin-bottom: 15px;">這是實驗性質專案。資料由 TDX 平台提供。</div>
    <hr style="border: 0; border-top: 1px solid #30363d; margin: 10px 0;">
    <div style="color: #58a6ff; font-size: 0.8em; font-weight: bold;">📋 版本紀錄 (V10.0)：</div>
    <div style="color: #8b949e; font-size: 0.75em;">
        • <b>指定字體精準套用</b>：選擇車站標題與卡片動態時間切換為自定義字體。<br>
        • <b>綠色層級標籤</b>：為卡片內標題增加深綠色背景圓角標籤，視覺層次更分明。<br>
        • <b>UI 微調</b>：優化卡片間距與陰影，提升整體專業感。
    </div>
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
