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

# 3. 定義抓取 Token 的函數
def get_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    data = {
        'grant_type': 'client_credentials', 
        'client_id': CLIENT_ID, 
        'client_secret': CLIENT_SECRET
    }
    res = requests.post(auth_url, data=data)
    return res.json().get('access_token')

# 4. 定義抓取資料的函數 (具備自動備援機制)
def get_data(token):
    # 優先嘗試：高雄市路徑
    urls = [
        'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/City/Kaohsiung?$top=50&$format=JSON',
        'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=50&$format=JSON'
    ]
    
    headers = {'Authorization': f'Bearer {token}'}
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                # 偵測回傳格式是直接列表還是藏在 LivePositions 裡
                positions = data if isinstance(data, list) else data.get('LivePositions', [])
                if positions: # 如果這個路徑抓得到車，就直接回傳
                    return positions
        except Exception:
            continue
    return [] # 全部都抓不到才回傳空列表

# 5. 主程式執行
try:
    token = get_token()
    positions = get_data(token)
except Exception as e:
    st.error(f"連線發生錯誤: {e}")
    positions = []

# 6. 建立地圖
# 高雄中心座標
m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
train_count = 0

# 繪製列車標記
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

# 7. 智慧警告框
if train_count == 0:
    st.warning("⚠️ 目前地圖上無即時列車資訊。請檢查：1. 是否為營運時段(07-22) 2. TDX權限是否開通 3. 系統是否維護中。")
else:
    st.success(f"✅ 目前偵測到 {train_count} 台輕軌列車運行中。")

# 顯示地圖
folium_static(m)

# 8. 顯示台灣時區更新時間
now = datetime.datetime.now() + datetime.timedelta(hours=8)
st.write(f"最後更新時間 (台灣): {now.strftime('%H:%M:%S')}")

# 9. 每 30 秒自動重新整理
time.sleep(30)
st.rerun()
