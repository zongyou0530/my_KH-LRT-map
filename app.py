import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime

# 1. 高雄輕軌 C1-C37 全線站點座標資料
STATIONS = {
    "顯示全圖 (預設)": [22.6280, 120.3014, 13],
    "C1 籬仔內": [22.5978, 120.3236, 16], "C2 凱旋瑞田": [22.5969, 120.3168, 16],
    "C3 前鎮之星": [22.5986, 120.3094, 16], "C4 凱旋中華": [22.6006, 120.3023, 16],
    "C5 夢時代": [22.5961, 120.3045, 16], "C6 經貿園區": [22.6015, 120.3012, 16],
    "C7 軟體園區": [22.6062, 120.3013, 16], "C8 高雄展覽館": [22.6105, 120.2995, 16],
    "C9 旅運中心": [22.6133, 120.2974, 16], "C10 光榮碼頭": [22.6178, 120.2952, 16],
    "C11 真愛碼頭": [22.6214, 120.2923, 16], "C12 駁二大義": [22.6193, 120.2863, 16],
    "C13 駁二蓬萊": [22.6202, 120.2809, 16], "C14 哈瑪星": [22.6220, 120.2885, 16],
    "C15 壽山公園": [22.6253, 120.2798, 16], "C16 文武聖殿": [22.6300, 120.2790, 16],
    "C17 鼓山區公所": [22.6373, 120.2797, 16], "C18 鼓山": [22.6418, 120.2831, 16],
    "C19 馬卡道": [22.6493, 120.2858, 16], "C20 臺鐵美術館": [22.6535, 120.2866, 16],
    "C21A 內惟藝術中心": [22.6575, 120.2884, 16], "C21 美術館東": [22.6582, 120.2931, 16],
    "C22 聯合醫院": [22.6579, 120.2965, 16], "C23 龍華國小": [22.6571, 120.2996, 16],
    "C24 愛河之心": [22.6565, 120.3028, 16], "C25 新上國小": [22.6562, 120.3075, 16],
    "C26 灣仔內": [22.6558, 120.3150, 16], "C27 鼎山街": [22.6555, 120.3204, 16],
    "C28 高雄高工": [22.6528, 120.3255, 16], "C29 樹德家商": [22.6480, 120.3298, 16],
    "C30 科工館": [22.6425, 120.3324, 16], "C31 聖功醫院": [22.6360, 120.3315, 16],
    "C32 凱旋公園": [22.6300, 120.3255, 16], "C33 衛生局": [22.6225, 120.3258, 16],
    "C34 五權國小": [22.6163, 120.3256, 16], "C35 凱旋武昌": [22.6110, 120.3255, 16],
    "C36 凱旋二聖": [22.6053, 120.3252, 16], "C37 輕軌機廠": [22.6001, 120.3250, 16]
}

st.set_page_config(page_title="高雄輕軌全線監測", layout="wide")
st.title("🚂 高雄輕軌即時位置監測 (全線版)")

# 2. 側邊欄控制
st.sidebar.header("📍 地圖控制面板")
selected_station = st.sidebar.selectbox("快速切換至站點：", list(STATIONS.keys()))
auto_refresh = st.sidebar.checkbox("自動更新 (30秒)", value=True)

zoom_target = STATIONS[selected_station]

# 3. 取得 Token 與資料
def get_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    data = {
        'grant_type': 'client_credentials', 
        'client_id': st.secrets["TDX_CLIENT_ID"], 
        'client_secret': st.secrets["TDX_CLIENT_SECRET"]
    }
    return requests.post(auth_url, data=data).json().get('access_token')

def get_data(token):
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=50&$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(api_url, headers=headers)
    data = res.json()
    return data.get('LivePositions', []) if isinstance(data, dict) else []

# 4. 初始化地圖
m = folium.Map(location=[zoom_target[0], zoom_target[1]], zoom_start=zoom_target[2])

# 繪製所有站點與站名
for name, coords in STATIONS.items():
    if name != "顯示全圖 (預設)":
        # 畫站名
        folium.Marker(
            location=[coords[0], coords[1]],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 9pt; color: #2e7d32; white-space: nowrap; text-shadow: 1px 1px 2px white;"><b>{name}</b></div>'
            )
        ).add_to(m)
        # 畫站點圓圈
        folium.CircleMarker(
            location=[coords[0], coords[1]],
            radius=3, color='green', fill=True, fill_color='green'
        ).add_to(m)

# 抓取列車資料
try:
    token = get_token()
    positions = get_data(token)
    train_count = 0
    
    for train in positions:
        pos = train.get('TrainPosition', {})
        lat, lon = pos.get('PositionLat'), pos.get('PositionLon')
        
        if lat and lon:
            # 方向判斷 (Direction 0: 外圈順時針, 1: 內圈逆時針)
            direction = train.get('Direction', 0)
            train_color = 'red' if direction == 0 else 'blue'
            dir_text = "順行 (外圈)" if direction == 0 else "逆行 (內圈)"
            
            folium.Marker(
                location=[lat, lon],
                popup=f"車號: {train.get('TripID')}<br>方向: {dir_text}",
                tooltip=f"列車 {train.get('TripID')} ({dir_text})",
                icon=folium.Icon(color=train_color, icon='train', prefix='fa')
            ).add_to(m)
            train_count += 1

    if train_count > 0:
        st.sidebar.success(f"目前偵測到 {train_count} 台列車")
        st.info("💡 圖例：🔴 紅色為順行(外圈) | 🔵 藍色為逆行(內圈)")
    else:
        st.warning("⚠️ 目前地圖上無即時列車資訊。")

except Exception as e:
    st.error(f"連線異常: {e}")

# 顯示地圖
folium_static(m)

# 5. 時間與自動更新
now = datetime.datetime.now() + datetime.timedelta(hours=8)
st.write(f"最後更新時間: {now.strftime('%H:%M:%S')}")

if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()
