import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import time
import datetime

st.set_page_config(page_title="高雄輕軌即時位置")
st.title("🚂 高雄輕軌即時位置監測")

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

m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
train_count = 0 # 新增計數器

# 嘗試畫標記
for train in positions:
    lat = train.get('PositionLat')
    lon = train.get('PositionLon')
    if lat and lon:
        folium.Marker(
            location=[lat, lon],
            popup=f"車號: {train.get('TrainNo', '未知')}",
            icon=folium.Icon(color='red', icon='train', prefix='fa')
        ).add_to(m)
        train_count += 1

# --- 智慧判斷：如果地圖上沒半台車，就顯示警告 ---
if train_count == 0:
    st.warning("⚠️ 目前地圖上無即時列車資訊（可能為非營運時段 22:00-07:00 或系統更新中）。")

folium_static(m)

# 顯示正確的台灣時間
now = datetime.datetime.now() + datetime.timedelta(hours=8)
st.write(f"最後更新時間 (台灣): {now.strftime('%H:%M:%S')}")

# 自動重整
time.sleep(30)
st.rerun()
