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
        
        .custom-font {{ font-family: 'ZongYouFont' !important; }}
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 52px; color: #a5d6a7; text-align: center; margin-bottom: 5px; }}
        .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 14px; color: #666; text-align: center; margin-bottom: 10px; letter-spacing: 2px; }}
        .st-selectbox-label {{ font-family: 'ZongYouFont' !important; font-size: 24px !important; color: #81c784 !important; margin-bottom: 5px; }}
        '''
    except: pass

# 2. 注入 CSS (極簡卡片與動態配色)
st.markdown(f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kiwi+Maru:wght@400;500&display=swap');
    {font_css}

    /* 全域預設圓體 */
    html, body, [data-testid="stAppViewContainer"], p, div, span {{
        font-family: 'Kiwi Maru', serif;
        color: #fafafa !important;
    }}

    /* 瘦身版卡片 */
    .arrival-card {{ 
        background-color: #1c1f26; 
        border: 1px solid #30363d;
        border-left: 4px solid #4caf50;
        border-radius: 8px; 
        padding: 8px 12px; 
        margin-bottom: 6px; /* 縮小卡片間距 */
    }}
    
    /* 標籤改用自定義字體 */
    .green-tag {{
        background-color: #2e7d32;
        color: #ffffff !important;
        font-size: 0.7em;
        padding: 2px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 5px;
        font-family: 'ZongYouFont' !important; /* 使用自定義字體 */
    }}

    /* 時間字體基礎樣式 */
    .status-base {{
        font-family: 'ZongYouFont' !important;
        font-size: 1.8em !important;
        line-height: 1.1;
    }}

    /* 動態顏色：緊急 (<=2分) 與 普通 (>2分) */
    .urgent {{ color: #ff5252 !important; font-weight: bold; }}
    .normal {{ color: #b0bec5 !important; }}

    .update-time-row {{ font-size: 0.75em; color: #777 !important; margin: 2px 0; }}

    /* 鎖死鍵盤 */
    div[data-testid="stSelectbox"] input {{ pointer-events: none !important; }}
</style>
''', unsafe_allow_html=True)

# 3. 資料處理 (省略重複的 STATION_MAP 與 get_token 以保持簡潔)
# ... (此處維持與前版本相同的 STATION_MAP 與 get_token 函數)

# --- UI 開始 ---
st.markdown('<div class="custom-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="credit-text">zongyou x gemini</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    # 地圖部分維持 (使用優先)
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    folium_static(m, height=450, width=900)

with col_info:
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
                    
                    # 顏色邏輯判斷
                    is_urgent = est <= 2
                    color_class = "urgent" if is_urgent else "normal"
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card">
                        <div class="green-tag">輕軌預計抵達時間</div>
                        <div class="status-base {color_class}">{msg}</div>
                    </div>''', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 資料同步中")
    
    st.markdown(f'''
        <div style="margin-top:10px; border-top: 1px solid #333; padding-top: 5px;">
            <div class="update-time-row">📍 地圖更新：{now.strftime("%H:%M:%S")}</div>
            <div class="update-time-row">🕒 站牌更新：{now.strftime("%H:%M:%S")}</div>
        </div>
    ''', unsafe_allow_html=True)
