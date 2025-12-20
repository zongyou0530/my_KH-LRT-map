import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pandas as pd

# 1. 基礎設定與樣式
st.set_page_config(page_title="高雄輕軌監測 VERSE 3-1", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Zen Maru Gothic", sans-serif !important;
        background-color: #f8f9fa;
    }
    h1 { font-family: "Dela Gothic One", cursive !important; color: #2c3e50; }
    .stSelectbox label { font-weight: 700; color: #495057; }
    /* 電子看板高級感卡片 */
    .arrival-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        border-left: 5px solid #2e7d32;
    }
    .time-highlight { color: #d32f2f; font-weight: bold; font-size: 1.2em; }
</style>
''', unsafe_allow_html=True)

# 2. 座標資料
ALL_STATIONS = {
    "哈瑪星": [22.6225, 120.2885], "愛河之心": [22.6565, 120.3028], 
    "台鐵美術館": [22.6537, 120.2863], "夢時代": [22.5961, 120.3045], 
    "旅運中心": [22.6133, 120.2974], "駁二大義": [22.6193, 120.2863]
    # ... 其他站點可依需求補回
}

# 3. 核心 API 函數
def get_token():
    try:
        auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        return requests.post(auth_url, data=data).json().get('access_token')
    except: return None

def get_live_data(token):
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    return requests.get(api_url, headers=headers).json().get('LivePositions', [])

def get_station_arrival(token, station_name):
    # 此處串接你截圖中的 StationArrival API
    api_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/RealTimeArrival/KLRT?$filter=StationName/Zh_tw eq '{station_name}'&$format=JSON"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        data = requests.get(api_url, headers=headers).json()
        return data
    except: return []

# --- 介面佈局 ---
st.title("🚂 高雄輕軌即時監測系統")
st.info("✅ VERSE 3-1: 高級感地圖 + 即時到站看板")

# 建立左右兩欄
col1, col2 = st.columns([7, 3])

token = get_token()

with col1:
    # 地圖選擇與顯示
    selected_map_station = st.selectbox("快速定位站點：", ["顯示全圖"] + list(ALL_STATIONS.keys()))
    
    map_center = [22.6280, 120.3014] if selected_map_station == "顯示全圖" else ALL_STATIONS[selected_map_station]
    
    # 高級感地圖切換：CartoDB Positron (乾淨白)
    m = folium.Map(location=map_center, zoom_start=13, tiles='CartoDB positron')
    
    # 繪製列車
    positions = get_live_data(token)
    for train in positions:
        pos = train.get('TrainPosition', {})
        lat, lon = pos.get('PositionLat'), pos.get('PositionLon')
        if lat and lon:
            color = 'red' if train.get('Direction') == 0 else 'blue'
            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color=color, icon='train', prefix='fa')
            ).add_to(m)
            
    folium_static(m, width=None) # width=None 讓地圖自適應容器

with col2:
    st.subheader("📊 站牌即時資訊")
    selected_board = st.selectbox("選擇查詢車站：", list(ALL_STATIONS.keys()))
    
    if token:
        arrival_data = get_station_arrival(token, selected_board)
        
        if arrival_data:
            for info in arrival_data:
                dest = info.get('DestinationStationName', {}).get('Zh_tw', '未知')
                gap = info.get('EstimateTime', 0)
                status = "即時進站" if gap <= 1 else f"約 {gap} 分鐘"
                
                st.markdown(f'''
                <div class="arrival-card">
                    <small>往 {dest} 方向</small><br>
                    <span class="time-highlight">{status}</span>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.warning("暫無到站預估資料")

st.caption(f"最後更新時間: {datetime.datetime.now().strftime('%H:%M:%S')}")
import time
time.sleep(30)
st.rerun()
