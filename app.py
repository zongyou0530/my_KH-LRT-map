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

# --- A. 字體與 CSS ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        font_base64 = base64.b64encode(f.read()).decode()
    font_css = f"@font-face {{ font-family: 'HandWrite'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}"

st.markdown(f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&display=swap');
    {font_css}
    
    /* 全域預設：圓體 */
    html, body, [data-testid="stAppViewContainer"], p, span, label, div, .stSelectbox {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
    }}

    /* 手寫體專用標籤 */
    .hand-style {{ font-family: 'HandWrite', sans-serif !important; }}

    /* 標題與特定文字 */
    .custom-title {{ font-family: 'HandWrite' !important; font-size: clamp(32px, 8vw, 44px); color: #a5d6a7; text-align: center; line-height: 1.2; margin-bottom: 10px; }}
    .st-board-header {{ font-family: 'HandWrite' !important; font-size: 26px; color: #81c784; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
    
    .legend-box {{ background-color: #212d3d; border-radius: 10px; padding: 10px; margin-bottom: 15px; display: flex; justify-content: center; gap: 15px; font-size: 14px; }}
    .paper-card {{ background-color: #1a1d23; border-left: 5px solid #4caf50; padding: 12px; margin-bottom: 10px; border-radius: 8px; }}
    .arrival-msg {{ font-family: 'HandWrite' !important; font-size: 24px; color: #fff; }}
    
    .footer-box {{ background-color: #1a1d23; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; }}
</style>
''', unsafe_allow_html=True)

# --- B. 暴力刷新 Token 邏輯 (無快取) ---
def get_fresh_data():
    try:
        # 使用新的變數名避開快取
        client_id = st.secrets["TD_ID_NEW"]
        client_secret = st.secrets["TD_SECRET_NEW"]
        
        auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
        res = requests.post(auth_url, data={'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': client_secret}, timeout=10)
        token = res.json().get('access_token')
        
        if not token: return None, "TOKEN_EMPTY"
        
        # 測試抓取列車位置
        pos_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
        headers = {'Authorization': f'Bearer {token}'}
        pos_res = requests.get(pos_url, headers=headers, timeout=10)
        
        if pos_res.status_code != 200:
            return None, f"API_ERROR_{pos_res.status_code}"
        
        return pos_res.json(), token
    except Exception as e:
        return None, str(e)

live_data, active_token = get_fresh_data()

# --- C. UI 渲染 ---
st.markdown('<div class="custom-title">高雄輕軌 即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#888; font-family:\'HandWrite\'; margin-bottom:20px; font-size:14px;">zongyou x gemini</div>', unsafe_allow_html=True)

# 顯示錯誤訊息 (調試用，如果成功就不會出現)
if not active_token or "LivePositions" not in str(live_data):
    st.error(f"⚠️ 目前無法連線至 TDX 服務。錯誤代碼: {live_data if not active_token else 'DATA_EMPTY'}")

st.markdown('<div class="legend-box">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

# (座標、時間處理省略，與 V4.0 相同)
STATION_COORDS = { "C1 籬仔內": [22.6015, 120.3204], "C2 凱旋瑞田": [22.6026, 120.3168], "C3 前鎮之星": [22.6025, 120.3117], "C4 凱旋中華": [22.6033, 120.3060], "C5 夢時代": [22.6000, 120.3061], "C6 經貿園區": [22.6052, 120.3021], "C7 軟體園區": [22.6075, 120.2989], "C8 高雄展覽館": [22.6105, 120.2982], "C9 旅運中心": [22.6133, 120.2965], "C10 光榮碼頭": [22.6186, 120.2933], "C11 真愛碼頭": [22.6225, 120.2885], "C12 駁二大義": [22.6200, 120.2842], "C13 駁二蓬萊": [22.6214, 120.2798], "C14 哈瑪星": [22.6218, 120.2730], "C15 壽山公園": [22.6268, 120.2738], "C16 文武聖殿": [22.6311, 120.2758], "C17 鼓山區公所": [22.6358, 120.2778], "C18 鼓山": [22.6398, 120.2795], "C19 馬卡道": [22.6455, 120.2835], "C20 台鐵美術館": [22.6500, 120.2868], "C21A 內維中心": [22.6548, 120.2861], "C21 美術館": [22.6593, 120.2868], "C22 聯合醫院": [22.6622, 120.2915], "C23 龍華國小": [22.6603, 120.2982], "C24 愛河之心": [22.6586, 120.3032], "C25 新上國小": [22.6575, 120.3105], "C26 灣仔內": [22.6535, 120.3155], "C27 鼎山街": [22.6515, 120.3205], "C28 高雄高工": [22.6465, 120.3235], "C29 樹德家商": [22.6415, 120.3275], "C30 科工館": [22.6365, 120.3305], "C31 聖功醫院": [22.6315, 120.3315], "C32 凱旋公園": [22.6265, 120.3305], "C33 衛生局": [22.6222, 120.3285], "C34 五權國小": [22.6175, 120.3275], "C35 凱旋武昌": [22.6135, 120.3275], "C36 凱旋二聖": [22.6085, 120.3265], "C37 輕軌機廠": [22.6045, 120.3245] }

tz = pytz.timezone('Asia/Taipei')
now = datetime.datetime.now(tz)
time_display = now.strftime("%Y年%m月%d日 %H:%M:%S")
user_pos = None
loc = get_geolocation()
if loc: user_pos = [loc['coords']['latitude'], loc['coords']['longitude']]

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if user_pos: folium.CircleMarker(user_pos, radius=8, color='#ff5252', fill=True).add_to(m)
    
    if active_token and isinstance(live_data, dict):
        for t in live_data.get('LivePositions', []):
            folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                          icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
    folium_static(m, height=420, width=900)

with col_info:
    # 標題手寫體
    st.markdown('<div class="st-board-header">🚉 車站即時站牌</div>', unsafe_allow_html=True)
    # 選單圓體 (Streamlit 預設)
    sel_st = st.selectbox("車站", list(STATION_COORDS.keys()), label_visibility="collapsed")
    target_id = sel_st.split()[0]

    if active_token:
        try:
            board_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{target_id}'&$format=JSON", headers={'Authorization': f'Bearer {active_token}'})
            for item in sorted(board_res.json(), key=lambda x: x.get('EstimateTime', 999)):
                est = int(item.get('EstimateTime', 0))
                msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                st.markdown(f'<div class="paper-card"><div style="color:#4caf50; font-size:12px;">預計抵達時間</div><div class="arrival-msg">{msg}</div></div>', unsafe_allow_html=True)
        except: st.info("⌛ 暫無即時資訊")

    st.markdown(f'<div style="font-size:0.85em; color:#888; margin-top:20px; border-top:1px solid #333; padding-top:10px;">📍 更新時間：{time_display}<br>🛰️ 座標：{user_pos if user_pos else "定位中..."}</div>', unsafe_allow_html=True)

# --- D. 底部留言板 (內容手寫體) ---
st.markdown(f'''
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:8px;">✍️ 作者留言：</div>
    <div class="hand-style" style="color:#abb2bf; font-size:1.15em; line-height:1.6;">
        各位親朋好友們，拜託請幫我看看到底準不準，不準的話可以搜尋ig跟我講謝謝。資料由 TDX 平台提供，僅供參考。
    </div>
</div>
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:5px;">📦 版本更新紀錄 (V4.2) ：</div>
    <div style="color:#abb2bf; font-size:14px;">
        • <b>暴力刷新機制</b>：強制更換 Secrets 變數以清除 Cloud 端快取。<br>
        • <b>字體分配精確化</b>：車站標題、到站時間、作者留言均改為自定義手寫體。<br>
        • <b>全網預設圓體</b>：保留下拉選單與系統文字為圓體。
    </div>
</div>
''', unsafe_allow_html=True)

time.sleep(30)
st.rerun()
