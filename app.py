import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import time
import datetime

# 設定網頁標題
st.set_page_config(page_title="高雄輕軌即時位置")
st.title("🚂 高雄輕軌即時位置監測")

# 從 Streamlit 的 Secrets 讀取金鑰
CLIENT_ID = st.secrets["TDX_CLIENT_ID"]
CLIENT_SECRET = st.secrets["TDX_CLIENT_SECRET"]

def get_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    data = {'grant_type': 'client_credentials', 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
    res = requests.post(auth_url, data=data)
    return res.json().get('access_token')

def get_data(token):
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=30&$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(api_url, headers=headers)
    return res.json().get('LivePositions', [])

# 執行抓取
try:
    token = get_token()
    positions = get_data(token)
except:
    positions = []

# 建立地圖
m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)

# --- 防呆機制與繪製標記 ---
if not positions:
    st.warning("⚠️ 目前 API 未回傳即時列車位置（可能為非營運時段，請於 07:00-22:00 間查看）。")
else:
    for train in positions:
        lat = train.get('PositionLat')
        lon = train.get('PositionLon')
        if lat and lon:
            folium.Marker(
                location=[lat, lon],
                popup=f"車號: {train.get('TrainNo', '未知')}",
                icon=folium.Icon(color='red', icon='train', prefix='fa')
            ).add_to(m)

# 顯示地圖
folium_static(m)

# --- 台灣時區時間顯示 ---
now = datetime.datetime.now() + datetime.timedelta(hours=8)
current_time = now.strftime("%H:%M:%S")
st.write(f"最後更新時間 (台灣): {current_time}")

# 30秒後自動重整
time.sleep(30)
st.rerun()
