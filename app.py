import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import math

# 1. 核心站點座標
CORE_STATIONS = {
    "台鐵美術館": [22.6535, 120.2866],
    "夢時代": [22.5961, 120.3045],
    "旅運中心": [22.6133, 120.2974],
    "駁二蓬萊": [22.6202, 120.2809],
    "哈瑪星": [22.6220, 120.2885],
    "愛河之心": [22.6565, 120.3028]
}

# 輔助函數：計算兩點距離 (找出最近站點)
def get_nearest_station(lat, lon):
    min_dist = float('inf')
    nearest_name = "輕軌路段"
    for name, coords in CORE_STATIONS.items():
        dist = math.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
        if dist < min_dist:
            min_dist = dist
            nearest_name = name
    return nearest_name

# 2. 網頁設定與雲端字體
st.set_page_config(page_title="高雄輕軌監測", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚂 高雄輕軌即時位置監測")

# --- 新增對話框區 ---
# 藍色對話框：圖標意義
st.info("💡 圖例說明：🔴 紅色圖標為「順行 (外圈)」 | 🔵 藍色圖標為「逆行 (內圈)」")

# 綠色對話框：自定義文字 (你可以在這裡改字)
st.success("📢 系統提示：目前顯示主要核心站點，地圖每 30 秒自動更新一次。")
# ------------------

# 3. 側邊欄控制
station_options = ["顯示全圖 (預設)"] + list(CORE_STATIONS.keys())
selected_station = st.sidebar.selectbox("快速切換至站點：", station_options)

# 設定地圖中心點
if selected_station == "顯示全圖 (預設)":
    map_center = [22.6280, 120.3014]
    map_zoom = 13
else:
    map_center = CORE_STATIONS[selected_station]
    map_zoom = 16

# 4. 取得資料
def get_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
    return requests.post(auth_url, data=data).json().get('access_token')

def get_data(token):
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=30&$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(api_url, headers=headers)
    return res.json().get('LivePositions', [])

# 5. 初始化地圖
m = folium.Map(location=map_center, zoom_start=map_zoom)

# 繪製 6 個核心站點標籤
for name, coords in CORE_STATIONS.items():
    folium.Marker(
        location=coords,
        icon=folium.DivIcon(
            html=f'<div style="font-size: 14pt; color: #1b5e20; white-space: nowrap; font-weight: bold; text-shadow: 2px 2px 4px white;">{name}</div>'
        )
    ).add_to(m)

# 執行抓取與繪製
try:
    token = get_token()
    positions = get_data(token)
    now_dt = datetime.datetime.now() + datetime.timedelta(hours=8)
    update_time_str = now_dt.strftime('%H:%M:%S')

    for train in positions:
        pos = train.get('TrainPosition', {})
        lat, lon = pos.get('PositionLat'), pos.get('PositionLon')
        
        if lat and lon:
            direction = train.get('Direction', 0)
            train_color = 'red' if direction == 0 else 'blue'
            dir_text = "順行 (外圈)" if direction == 0 else "逆行 (內圈)"
            
            # 💡 修正站牌名稱：找出這台車現在最靠近哪一站
            current_nearest = get_nearest_station(lat, lon)
            
            popup_html = f"""
            <div style="width: 150px; font-family: 'Noto Sans TC', sans-serif; line-height: 1.6;">
                <b style="color: #333;">站牌：</b> {current_nearest}<br>
                <b style="color: #333;">方向：</b> {dir_text}<br>
                <b style="color: #333;">更新：</b> {update_time_str}
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=200),
                icon=folium.Icon(color=train_color, icon='train', prefix='fa')
            ).add_to(m)

except Exception as e:
    st.error(f"連線更新中...")

folium_static(m)
st.write(f"最後更新時間 (台灣): {update_time_str}")

# 每 30 秒重整
import time
time.sleep(30)
st.rerun()
