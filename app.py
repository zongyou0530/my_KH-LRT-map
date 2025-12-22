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
        .zong-font {{ font-family: 'ZongYouFont' !important; }}
        /* 標題不換行處理 */
        .custom-title {{ 
            font-family: 'ZongYouFont' !important; 
            font-size: 42px; 
            color: #a5d6a7; 
            text-align: center; 
            margin-bottom: 0px;
            white-space: nowrap; 
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 14px; color: #666; text-align: center; margin-bottom: 10px; letter-spacing: 2px; }}
        '''
    except: pass

# 2. 注入 CSS (優化標籤大小與卡片厚度)
st.markdown(f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kiwi+Maru:wght@400;500&display=swap');
    {font_css}

    /* 全域預設圓體 */
    html, body, [data-testid="stAppViewContainer"], p, div {{
        font-family: 'Kiwi Maru', serif;
    }}

    /* 極簡纖薄卡片 */
    .paper-card {{ 
        background-color: #1a1d23; 
        border: 1px solid #2d333b;
        border-left: 5px solid #4caf50;
        border-radius: 8px; 
        padding: 5px 12px; /* 極小化內距 */
        margin-bottom: 6px;
    }}
    
    /* 放大後的綠色標籤文字 */
    .green-tag-box {{
        background-color: #2e7d32;
        color: #ffffff !important;
        font-size: 0.9em; /* 文字放大 */
        padding: 3px 10px;
        border-radius: 5px;
        display: inline-block;
        margin-bottom: 4px;
        font-family: 'ZongYouFont' !important;
    }}

    .arrival-text {{
        font-family: 'ZongYouFont' !important;
        font-size: 2.0em !important;
        line-height: 1.0;
        margin-top: 2px;
    }}

    /* 顏色邏輯 */
    .urgent-red {{ color: #ff5252 !important; }}
    .calm-grey {{ color: #78909c !important; }}

    .st-label-zong {{ font-family: 'ZongYouFont' !important; font-size: 24px; color: #81c784; margin-bottom: 5px; }}
    
    /* 手機端標題縮小以防換行 */
    @media (max-width: 768px) {{
        .custom-title {{ font-size: 28px; }}
    }}
</style>
''', unsafe_allow_html=True)

# 3. 數據定義 (維持穩定性)
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
    folium_static(m, height=450, width=900)

with col_info:
    st.markdown('<div class="st-label-zong">🚉 選擇車站</div>', unsafe_allow_html=True)
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
                    color_class = "urgent-red" if est <= 2 else "calm-grey"
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="paper-card">
                        <div class="green-tag-box">輕軌預計抵達時間</div>
                        <div class="arrival-text {color_class}">{msg}</div>
                    </div>''', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 資料連線中")
    
    st.markdown(f'''
        <div style="margin-top:10px; border-top: 1px solid #333; padding-top: 5px;">
            <div style="font-size: 0.75em; color: #666;">📍 地圖更新：{now.strftime("%H:%M:%S")}</div>
            <div style="font-size: 0.75em; color: #666;">🕒 站牌更新：{now.strftime("%H:%M:%S")}</div>
        </div>
    ''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
