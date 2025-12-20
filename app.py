import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import time
import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="高雄輕軌即時位置", layout="wide")
st.title("🚂 高雄輕軌即時位置監測")

# 2. 從 Streamlit Secrets 讀取金鑰
try:
    CLIENT_ID = st.secrets["TDX_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["TDX_CLIENT_SECRET"]
except Exception:
    st.error("❌ 找不到金鑰設定，請確認 Streamlit 雲端後台的 Secrets 已填寫。")
    st.stop()

# 3. 取得 Token
def get_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    data = {'grant_type': 'client_credentials', 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
    res = requests.post(auth_url, data=data)
    return res.json().get('access_token')

# 4. 取得資料 (針對你測試成功的格式優化)
def get_data(token):
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=30&$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    try:
        res = requests.get(api_url, headers=headers)
        data = res.json()
        # 根據你測試截圖的結果，資料是在 LivePositions 裡面
        if isinstance(data, dict):
            return data.get('LivePositions', [])
        return data if isinstance(data, list) else []
    except:
        return []

# 5. 執行程序
try:
    token = get_token()
    positions = get_data(token)
except:
    positions = []

# 6. 繪製地圖
m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
train_count = 0

for train in positions:
    # 針對你截圖中的 TrainPosition 結構進行讀取
    pos = train.get('TrainPosition', {})
    lat = pos.get('PositionLat')
    lon = pos.get('PositionLon')
    
    if lat and lon:
        folium.Marker(
            location=[lat, lon],
            popup=f"車號: {train.get('TripID', '未知')}",
            icon=folium.Icon(color='red', icon='train', prefix='fa')
        ).add_to(m)
        train_count += 1

# 7. 顯示結果
if train_count > 0:
    st.success(f"✅ 成功偵測到 {train_count} 台列車！資料獲取正常。")
else:
    st.warning("⚠️ 目前地圖上無即時列車資訊（API 回傳 Count 為 0）。")

folium_static(m)

# 8. 顯示台灣時間
now = datetime.datetime.now() + datetime.timedelta(hours=8)
st.write(f"最後更新時間 (台灣): {now.strftime('%H:%M:%S')}")

# 9. 每 30 秒自動重整
time.sleep(30)
st.rerun()
