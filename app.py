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

# --- B. CSS 與字體分配 ---
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
    
    /* 全域圓體 */
    html, body, [data-testid="stAppViewContainer"], p, span, div {{
        font-family: 'Zen Maru Gothic', sans-serif !important;
    }}

    /* 選單強制圓體 */
    [data-testid="stSelectbox"] div {{
        font-family: 'Zen Maru Gothic' !important;
    }}

    /* 手寫體專用標籤 */
    .hand-font {{
        font-family: 'HandWrite' !important;
    }}

    .custom-title {{ font-family: 'HandWrite' !important; font-size: 42px; color: #a5d6a7; text-align: center; margin-bottom: 10px; }}
    .st-board-title {{ font-family: 'HandWrite' !important; font-size: 26px; color: #81c784; margin-bottom: 15px; }}
    .author-msg {{ font-family: 'HandWrite' !important; font-size: 1.2em; color: #abb2bf; line-height: 1.6; }}

    .footer-box {{ background-color: #1a1d23; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-top: 15px; }}
    .legend-box {{ background-color: #212d3d; border-radius: 10px; padding: 10px; margin: 10px 0; display: flex; justify-content: center; gap: 15px; }}
</style>
''', unsafe_allow_html=True)

# --- C. 核心 API 抓取 (移除快取確保 1 月點數正常) ---
def fetch_token():
    try:
        data = {{'grant_type': 'client_credentials', 'client_id': st.secrets["TD_ID"], 'client_secret': st.secrets["TD_SECRET"]}}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=7)
        return res.json().get('access_token')
    except Exception as e:
        return None

token = fetch_token()
quota_status = "OK"

if token:
    try:
        test_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=1', headers={{'Authorization': f'Bearer {{token}}'}}, timeout=5)
        if test_res.status_code != 200 or "Quota" in test_res.text:
            quota_status = "EXCEEDED"
    except: quota_status = "ERROR"
else: quota_status = "TOKEN_FAILED"

# --- D. 定位與時間 ---
tz = pytz.timezone('Asia/Taipei')
now = datetime.datetime.now(tz)
time_display = now.strftime("%Y年%m月%d日 %H:%M:%S")
user_pos = None
loc = get_geolocation()
if loc: user_pos = [loc['coords']['latitude'], loc['coords']['longitude']]

# --- E. UI 渲染 ---
st.markdown('<div class="custom-title">高雄輕軌 即時位置監測</div>', unsafe_allow_html=True)

if quota_status != "OK":
    st.markdown(f'<div style="border:2px solid #ff5252; padding:15px; border-radius:12px; text-align:center; color:#ffbaba; font-family:\'HandWrite\';">點數已耗盡或連線異常 (狀態: {{quota_status}})<br>請下個月再來 😭</div>', unsafe_allow_html=True)

st.markdown('<div class="legend-box">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if user_pos:
        folium.CircleMarker(location=user_pos, radius=8, color='#ff5252', fill=True, fill_opacity=0.9).add_to(m)
    
    # 只有 OK 時才畫火車
    if quota_status == "OK":
        try:
            live_data = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={{'Authorization': f'Bearer {{token}}'}}).json()
            for t in live_data.get('LivePositions', []):
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], icon=folium.Icon(color='green' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=420, width=900)

with col_info:
    # 1. 標題用手寫體
    st.markdown('<div class="st-board-title">🚉 車站即時站牌</div>', unsafe_allow_html=True)
    # 2. 選單維持圓體
    sel_st = st.selectbox("車站", list(STATION_COORDS.keys()), label_visibility="collapsed")
    target_id = sel_st.split()[0]

    if quota_status == "OK":
        try:
            resp = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{{target_id}}'&$format=JSON", headers={{'Authorization': f'Bearer {{token}}'}})
            data = resp.json()
            if data:
                for item in sorted(data, key=lambda x: x.get('EstimateTime', 999)):
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {{est}} 分鐘"
                    st.markdown(f'<div style="background:#1a1d23; border-left:5px solid #4caf50; padding:10px; margin-bottom:8px; border-radius:5px;">預計抵達時間：<span style="font-size:20px; font-family:\'HandWrite\'; color:#fff;">{{msg}}</span></div>', unsafe_allow_html=True)
            else: st.info("⌛ 暫無列車資訊")
        except: st.error("連線超時")

    st.markdown(f'<div style="font-size:0.8em; color:#888; margin-top:15px; border-top:1px solid #333; padding-top:10px;">📍 更新時間：{{time_display}}<br>🛰️ 座標：{{user_pos if user_pos else "定位中..."}}</div>', unsafe_allow_html=True)

# --- F. 底部留言板 (內容手寫體) ---
st.markdown(f'''
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:5px;">✍️ 作者留言：</div>
    <div class="author-msg">各位親朋好友們，拜託請幫我看看到底準不準，不準的話可以搜尋ig跟我講謝謝。資料由 TDX 平台提供，僅供參考。</div>
</div>
<div class="footer-box">
    <div style="font-weight:bold; color:#eee; margin-bottom:5px;">📦 版本更新紀錄 (V4.1) ：</div>
    <div style="color:#abb2bf; font-size:14px;">
        • <b>字體細分修復</b>：標題/留言採手寫體，選單採圓體。<br>
        • <b>點數偵測修復</b>：移除快取，解決 2026/01 點數重置後讀取不到的問題。<br>
        • <b>錯誤追蹤</b>：新增偵測狀態碼顯示。
    </div>
</div>
''', unsafe_allow_html=True)
