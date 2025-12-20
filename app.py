import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime

# 1. 基礎設定
st.set_page_config(page_title="高雄輕軌監測 VERSE 3-2", layout="wide")

# CSS 優化：移除標題加粗，保留高級感
st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Zen Maru Gothic", sans-serif !important;
    }
    h1 { 
        font-family: "Dela Gothic One", cursive !important; 
        font-weight: 400 !important; /* 修正：不要加粗 */
        color: #2c3e50; 
    }
    .arrival-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        border-left: 5px solid #1b5e20;
    }
    .time-val { color: #d32f2f; font-weight: bold; font-size: 1.1em; }
</style>
''', unsafe_allow_html=True)

# 2. 座標資料 (全線)
ALL_STATIONS = {
    "哈瑪星": [22.6225, 120.2885], "愛河之心": [22.6565, 120.3028], "台鐵美術館": [22.6537, 120.2863],
    "夢時代": [22.5961, 120.3045], "旅運中心": [22.6133, 120.2974], "駁二大義": [22.6193, 120.2863],
    "籬仔內": [22.5978, 120.3236], "輕軌機廠": [22.6001, 120.3250], "凱旋二聖": [22.6053, 120.3252]
}

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
    # API 過濾器修正
    api_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/RealTimeArrival/KLRT?$filter=StationName/Zh_tw eq '{station_name}'&$format=JSON"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        res = requests.get(api_url, headers=headers)
        return res.json()
    except: return []

# --- 介面開始 ---
st.title("🚂 高雄輕軌即時監測系統")

# 恢復：綠色留言板 (系統提示)
st.success("✅ 系統提示：已修復標題字體、底圖路線顯示，並優化電子看板資料對齊。")

token = get_token()

col1, col2 = st.columns([7, 3])

with col1:
    selected_map = st.selectbox("快速定位站點：", ["顯示全圖"] + list(ALL_STATIONS.keys()))
    center = [22.6280, 120.3014] if selected_map == "顯示全圖" else ALL_STATIONS[selected_map]
    
    # 修正：改用 CartoDB Voyager，這款能顯示地圖上的交通軌道線
    m = folium.Map(location=center, zoom_start=13, tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', attr='CartoDB')
    
    # 畫出列車
    if token:
        try:
            positions = get_live_data(token)
            for train in positions:
                lat, lon = train['TrainPosition']['PositionLat'], train['TrainPosition']['PositionLon']
                color = 'red' if train.get('Direction') == 0 else 'blue'
                folium.Marker(location=[lat, lon], icon=folium.Icon(color=color, icon='train', prefix='fa')).add_to(m)
        except: pass
    
    folium_static(m)

with col2:
    st.subheader("📊 站牌即時資訊")
    selected_st = st.selectbox("選擇查詢車站：", list(ALL_STATIONS.keys()), key="board")
    
    if token:
        arrivals = get_station_arrival(token, selected_st)
        if arrivals:
            for info in arrivals:
                # 修正：針對 TDX JSON 結構進行安全讀取
                dest = info.get('DestinationStationName', {}).get('Zh_tw', '終點站')
                time_gap = info.get('EstimateTime', '--')
                status = "即時進站" if time_gap != '--' and int(time_gap) <= 1 else f"約 {time_gap} 分鐘"
                
                st.markdown(f'''
                <div class="arrival-card">
                    <small style="color:gray">往 {dest} 方向</small><br>
                    狀態：<span class="time-val">{status}</span>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.warning("目前無列車預估資訊")

st.caption(f"最後更新：{datetime.datetime.now().strftime('%H:%M:%S')}")
import time
time.sleep(30)
st.rerun()
