import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import math

# 1. 高雄輕軌全線 38 站精確座標 (微調座標以對齊底圖)
ALL_STATIONS = {
    "籬仔內": [22.5978, 120.3236], "凱旋瑞田": [22.5969, 120.3168], "前鎮之星": [22.5986, 120.3094],
    "凱旋中華": [22.6006, 120.3023], "夢時代": [22.5961, 120.3045], "經貿園區": [22.6015, 120.3012],
    "軟體園區": [22.6062, 120.3013], "高雄展覽館": [22.6105, 120.2995], "旅運中心": [22.6133, 120.2974],
    "光榮碼頭": [22.6178, 120.2952], "真愛碼頭": [22.6214, 120.2923], "駁二大義": [22.6193, 120.2863],
    "駁二蓬萊": [22.6202, 120.2809], "哈瑪星": [22.6220, 120.2885], "壽山公園": [22.6253, 120.2798],
    "文武聖殿": [22.6300, 120.2790], "鼓山區公所": [22.6373, 120.2797], "鼓山": [22.6418, 120.2831],
    "馬卡道": [22.6493, 120.2858], "台鐵美術館": [22.6535, 120.2866], "內惟藝術中心": [22.6575, 120.2884],
    "美術館東": [22.6582, 120.2931], "聯合醫院": [22.6579, 120.2965], "龍華國小": [22.6571, 120.2996],
    "愛河之心": [22.6565, 120.3028], "新上國小": [22.6562, 120.3075], "灣仔內": [22.6558, 120.3150],
    "鼎山街": [22.6555, 120.3204], "高雄高工": [22.6528, 120.3255], "樹德家商": [22.6480, 120.3298],
    "科工館": [22.6425, 120.3324], "聖功醫院": [22.6360, 120.3315], "凱旋公園": [22.6300, 120.3255],
    "衛生局": [22.6225, 120.3258], "五權國小": [22.6163, 120.3256], "凱旋武昌": [22.6110, 120.3255],
    "凱旋二聖": [22.6053, 120.3252], "輕軌機廠": [22.6001, 120.3250]
}

# 核心站點清單 (顯示大字標籤)
CORE_DISPLAY = ["台鐵美術館", "哈瑪星", "駁二蓬萊", "旅運中心", "夢時代", "愛河之心"]

st.set_page_config(page_title="高雄輕軌監測", layout="wide")

# 2. 修改字體為 DotGothic16 像素字體
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DotGothic16&display=swap');
    
    html, body, [class*="css"], .stMarkdown {
        font-family: 'DotGothic16', sans-serif !important;
    }
    .leaflet-div-icon div {
        font-family: 'DotGothic16', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("👾 高雄輕軌即時監測 (像素風格)")

# 3. 藍色與綠色提示框
st.info("💡 圖例：🔴 順行 (外圈) | 🔵 逆行 (內圈)")
st.success("📢 系統提示：已校準全線座標並更換 DotGothic16 字體。")

# 邏輯：找出最近站名
def get_nearest_station(lat, lon):
    min_dist = float('inf')
    nearest_name = "行駛中 (靠近鼓山/美術館路段)"
    for name, coords in ALL_STATIONS.items():
        # 計算歐幾里得距離
        dist = math.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
        if dist < min_dist:
            min_dist = dist
            nearest_name = f"輕軌{name}站"
    # 如果距離最近站點太遠(約超過300公尺)，顯示路段中
    if min_dist > 0.003:
        return "行駛於站點區間"
    return nearest_name

# API 抓取 (延用成功代碼)
def get_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
    return requests.post(auth_url, data=data).json().get('access_token')

def get_data(token):
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=30&$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(api_url, headers=headers)
    return res.json().get('LivePositions', [])

# 4. 地圖初始化
m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)

# 繪製站點標籤 (綠色粗體字)
for name, coords in ALL_STATIONS.items():
    if name in CORE_DISPLAY:
        folium.Marker(
            location=coords,
            icon=folium.DivIcon(
                html=f'<div style="font-size: 16pt; color: #1b5e20; white-space: nowrap; font-weight: bold; text-shadow: 2px 2px 3px white;">{name}</div>'
            )
        ).add_to(m)

# 列車處理
try:
    token = get_token()
    positions = get_data(token)
    update_time = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime('%H:%M:%S')

    for train in positions:
        pos = train.get('TrainPosition', {})
        lat, lon = pos.get('PositionLat'), pos.get('PositionLon')
        if lat and lon:
            direction = train.get('Direction', 0)
            train_color = 'red' if direction == 0 else 'blue'
            
            # 精準計算最近站點
            current_nearest = get_nearest_station(lat, lon)
            
            popup_html = f"""
            <div style="width: 160px; font-family: 'DotGothic16', sans-serif;">
                <b style="font-size: 12pt;">站牌：</b><br>{current_nearest}<br>
                <b>方向：</b>{"順行 (外圈)" if direction==0 else "逆行 (內圈)"}<br>
                <b>更新：</b>{update_time}
            </div>
            """
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=200),
                icon=folium.Icon(color=train_color, icon='train', prefix='fa')
            ).add_to(m)
except:
    st.warning("資料更新中...")

folium_static(m)
st.write(f"最後更新時間: {update_time}")

import time
time.sleep(30)
st.rerun()
