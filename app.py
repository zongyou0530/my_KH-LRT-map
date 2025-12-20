import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import math

# 1. 座標極致對齊 (根據最新截圖微調綠色標籤點位)
ALL_STATIONS = {
    "籬仔內": [22.5978, 120.3236], "凱旋瑞田": [22.5970, 120.3162], "前鎮之星": [22.5986, 120.3094],
    "凱旋中華": [22.6006, 120.3023], "夢時代": [22.5961, 120.3045], "經貿園區": [22.6015, 120.3012],
    "軟體園區": [22.6062, 120.3013], "高雄展覽館": [22.6105, 120.2995], "旅運中心": [22.6133, 120.2974],
    "光榮碼頭": [22.6178, 120.2952], "真愛碼頭": [22.6214, 120.2923], "駁二大義": [22.6193, 120.2863],
    "駁二蓬萊": [22.6202, 120.2809], "哈瑪星": [22.6225, 120.2885], "壽山公園": [22.6253, 120.2798],
    "文武聖殿": [22.6300, 120.2790], "鼓山區公所": [22.6373, 120.2797], 
    "鼓山": [22.6415, 120.2830], "馬卡道": [22.6493, 120.2858], 
    "台鐵美術館": [22.6538, 120.2861], # 稍微上移對齊藍色車站圖示
    "內惟藝術中心": [22.6575, 120.2884],
    "美術館東": [22.6582, 120.2931], "聯合醫院": [22.6579, 120.2965], "龍華國小": [22.6571, 120.2996],
    "愛河之心": [22.6568, 120.3028], # 稍微上移對齊藍色車站圖示
    "新上國小": [22.6562, 120.3075], "灣仔內": [22.6558, 120.3150],
    "鼎山街": [22.6555, 120.3204], "高雄高工": [22.6528, 120.3255], "樹德家商": [22.6480, 120.3298],
    "科工館": [22.6425, 120.3324], "聖功醫院": [22.6360, 120.3315], "凱旋公園": [22.6300, 120.3255],
    "衛生局": [22.6225, 120.3258], "五權國小": [22.6163, 120.3256], "凱旋武昌": [22.6110, 120.3255],
    "凱旋二聖": [22.6053, 120.3252], "輕軌機廠": [22.6001, 120.3250]
}

# 設定要在地圖上永久顯示綠色站名的重要站點
CORE_DISPLAY = ["台鐵美術館", "哈瑪星", "愛河之心", "夢時代", "旅運中心"]

st.set_page_config(page_title="高雄輕軌監測", layout="wide")

# 2. 字體雙重修復：標題使用 Dela Gothic One，內文與地圖使用 Zen Maru Gothic
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet"><style>html,body,[data-testid="stAppViewContainer"],p,span,div,label,.stMarkdown{font-family:"Zen Maru Gothic",sans-serif!important;}h1{font-family:"Dela Gothic One",cursive!important;font-weight:400!important;color:"#1e1e1e"}.leaflet-container{font-family:"Zen Maru Gothic",sans-serif!important}</style>', unsafe_allow_html=True)

st.title("🚂 高雄輕軌即時位置監測")
st.caption("✅ 目前版本：Dela標題+精準對齊版") 

st.info("💡 圖例：🔴 順行 (外圈) | 🔵 逆行 (內圈)")

selected_station = st.sidebar.selectbox("快速切換至站點：", ["顯示全圖"] + list(ALL_STATIONS.keys()))

# --- 邏輯函數 ---
def get_nearest_station(lat, lon):
    min_dist = float('inf')
    nearest_name = "路段中"
    for name, coords in ALL_STATIONS.items():
        dist = math.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
        if dist < min_dist:
            min_dist = dist
            nearest_name = f"輕軌{name}站"
    return nearest_name

def get_token():
    try:
        auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        return requests.post(auth_url, data=data).json().get('access_token')
    except: return None

def get_data(token):
    if not token: return []
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=30&$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(api_url, headers=headers)
    return res.json().get('LivePositions', [])

# --- 地圖與標註 ---
map_loc = [22.6280, 120.3014] if selected_station == "顯示全圖" else ALL_STATIONS[selected_station]
zoom_lv = 13 if selected_station == "顯示全圖" else 16
m = folium.Map(location=map_loc, zoom_start=zoom_lv)

# 顯示綠色站名標籤
for name, coords in ALL_STATIONS.items():
    if name in CORE_DISPLAY:
        folium.Marker(
            location=coords,
            icon=folium.DivIcon(
                html=f'<div style="font-family: \'Zen Maru Gothic\'; font-size: 15pt; color: #1b5e20; white-space: nowrap; text-shadow: 2px 2px 3px white; font-weight: 700;">{name}</div>'
            )
        ).add_to(m)

try:
    token = get_token()
    positions = get_data(token)
    now_str = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime('%H:%M:%S')
    for train in positions:
        pos = train.get('TrainPosition', {})
        lat, lon = pos.get('PositionLat'), pos.get('PositionLon')
        if lat and lon:
            direction = train.get('Direction', 0)
            current_nearest = get_nearest_station(lat, lon)
            popup_html = f"<div style='font-family:\"Zen Maru Gothic\";'><b>站牌：</b>{current_nearest}<br><b>更新：</b>{now_str}</div>"
            folium.Marker(location=[lat, lon], popup=folium.Popup(popup_html, max_width=200),
                icon=folium.Icon(color='red' if direction==0 else 'blue', icon='train', prefix='fa')).add_to(m)
except: pass

folium_static(m)
st.write(f"最後更新時間: {now_str}")

import time
time.sleep(30)
st.rerun()
