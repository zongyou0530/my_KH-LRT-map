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

# --- A. 字體與 CSS (包含閃爍動畫) ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode()
        font_css = f'''
        @font-face {{ font-family: 'ZongYouFont'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}
        
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 44px; color: #a5d6a7; text-align: center; line-height: 1.1; margin-bottom: 2px; }}
        .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 15px; color: #888; text-align: center; margin-bottom: 12px; letter-spacing: 2px; }}
        
        @keyframes blink-red {{
            0% {{ border: 2px solid #ff5252; box-shadow: 0 0 10px #ff5252; }}
            50% {{ border: 2px solid transparent; box-shadow: 0 0 0px transparent; }}
            100% {{ border: 2px solid #ff5252; box-shadow: 0 0 10px #ff5252; }}
        }}

        .quota-exceeded-box {{
            background-color: #2c1616;
            color: #ffbaba;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            font-family: 'ZongYouFont' !important;
            font-size: 22px;
            margin: 15px auto;
            max-width: 90%;
            line-height: 1.6;
            animation: blink-red 1.5s infinite;
        }}
        '''
    except: pass

st.markdown(f'''<style>{font_css}
    .legend-box {{ font-size: 12px !important; margin-bottom: 10px; display: flex; justify-content: center; gap: 10px; }}
</style>''', unsafe_allow_html=True)

# --- B. 核心檢測與 Token ---
@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

token = get_token()
quota_exceeded = False

# 強制檢查：不使用 cache，直接去撞門
try:
    if token:
        # 測試一個最簡單的 API
        t_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=1', 
                             headers={'Authorization': f'Bearer {token}'}, timeout=5)
        # 如果狀態碼不是 200，或者回傳內容有 "Quota" 或 "limit"
        if t_res.status_code != 200 or "Quota" in t_res.text or "limit" in t_res.text:
            quota_exceeded = True
    else:
        # 連 Token 都拿不到通常也是因為流量被鎖
        quota_exceeded = True
except:
    quota_exceeded = True

# --- C. UI 渲染 ---
st.markdown('<div class="custom-title">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="credit-text">zongyou x gemini</div>', unsafe_allow_html=True)

# 顯示閃爍通知 (置頂顯示)
if quota_exceeded:
    st.markdown('''
        <div class="quota-exceeded-box">
            因訪問人數太多<br>
            我這個月TDX的免費點數已耗盡<br>
            請下個月再來 😭
        </div>
    ''', unsafe_allow_html=True)

# --- (後續地圖與車站資料的 if 判斷都要加上 not quota_exceeded) ---
# ... (此處省略中間 STATION_COORDS 等不變的部分) ...

# 只有在沒爆點數時才跑地圖與資料
if not quota_exceeded:
    # 這裡放原本顯示地圖和站牌的邏輯
    st.markdown('<div class="stInfo legend-box">🟢順行 | 🔵逆行 | 🔴您目前位置</div>', unsafe_allow_html=True)
    # ... (地圖與站牌程式碼) ...
else:
    # 點數爆了，地圖顯示靜態預設圖或空圖
    st.info("⚠️ 系統目前無法獲取即時資料，請參考上方說明。")

# --- 底部內容 ---
# ... (您的 Footer 保持不變) ...
