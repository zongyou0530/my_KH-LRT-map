import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import math

# 1. 高雄輕軌全線完整站點資料 (C1-C37, C1)
ALL_STATIONS = {
    "輕軌籬仔內站": [22.6010, 120.3195], "輕軌凱旋瑞田站": [22.5970, 120.3159],
    "輕軌前鎮之星站": [22.5934, 120.3116], "輕軌凱旋中華站": [22.5916, 120.3056],
    "輕軌夢時代站": [22.5961, 120.3045], "輕軌經貿園區站": [22.6011, 120.3023],
    "輕軌軟體園區站": [22.6053, 120.3005], "輕軌高雄展覽館站": [22.6105, 120.2995],
    "輕軌旅運中心站": [22.6133, 120.2974], "輕軌光榮碼頭站": [22.6190, 120.2933],
    "輕軌真愛碼頭站": [22.6218, 120.2905], "輕軌駁二大義站": [22.6200, 120.2858],
    "輕軌駁二蓬萊站": [22.6202, 120.2809], "輕軌哈瑪星站": [22.6220, 120.2885],
    "輕軌壽山公園站": [22.6262, 120.2842], "輕軌文武聖殿站": [22.6311, 120.2831],
    "輕軌鼓山區公所站": [22.6371, 120.2835], "輕軌鼓山站": [22.6416, 120.2844],
    "輕軌馬卡道站": [22.6483, 120.2855], "輕軌台鐵美術館站": [22.6535, 120.2866],
    "輕軌美術館東站": [22.6567, 120.2901], "輕軌聯合醫院站": [22.6575, 120.2949],
    "輕軌龍華國小站": [22.6578, 120.2997], "輕軌愛河之心站": [22.6565, 120.3028],
    "輕軌新上國小站": [22.6558, 120.3082], "輕軌灣仔內站": [22.6532, 120.3138],
    "輕軌鼎山街站": [22.6496, 120.3195], "輕軌高雄高工站": [22.6464, 120.3235],
    "輕軌樹德家商站": [22.6425, 120.3278], "輕軌科工館站": [22.6375, 120.3312],
    "輕軌聖功醫院站": [22.6331, 120.3338], "輕軌凱旋公園站": [22.6293, 120.3333],
    "輕軌衛生局站": [22.6216, 120.3308], "輕軌五權國小站": [22.6158, 120.3303],
    "輕軌凱旋武昌站": [22.6110, 120.3283], "輕軌凱旋二聖站": [22.6053, 120.3248],
    "輕軌輕軌機廠站": [22.6022, 120.3223]
}

# 網頁配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")
# 修改字體的 CSS 區塊
st.markdown("""
    <style>
    /* 1. 從 Google Fonts 引用新字體 (這裡換成圓體) */
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700&display=swap');

    /* 2. 套用到全網頁 */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'M PLUS Rounded 1c', sans-serif;
    }

    /* 3. 針對地圖內的站名標籤也要統一 (如果是 DivIcon 繪製的) */
    .leaflet-div-icon {
        font-family: 'M PLUS Rounded 1c', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)
st.title("🚂 高雄輕軌即時位置監測")

# 對話框區
st.info("💡 圖例說明：🔴 紅色為「順行 (外圈)」 | 🔵 藍色為「逆行 (內圈)」")
st.success("📢 系統提示：目前導入全線 38 站資訊，偵測更精準。地圖每 30 秒自動更新。")

# 側邊欄
selected_station = st.sidebar.selectbox("快速切換至站點：", ["顯示全圖"] + list(ALL_STATIONS.keys()))

# 邏輯函數
def get_nearest_station(lat, lon):
    min_dist = float('inf')
    nearest_name = "輕軌路段"
    for name, coords in ALL_STATIONS.items():
        dist = math.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
        if dist < min_dist:
            min_dist = dist
            nearest_name = name
    return nearest_name

# 取得資料
def get_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
    return requests.post(auth_url, data=data).json().get('access_token')

def get_data(token):
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=30&$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(api_url, headers=headers)
    return res.json().get('LivePositions', [])

# 地圖初始化
m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)

# 繪製站點 (綠色大字僅顯示核心大站，避免過於雜亂)
CORE_DISPLAY = ["台鐵美術館", "哈瑪星", "駁二蓬萊", "旅運中心", "夢時代", "愛河之心"]
for name, coords in ALL_STATIONS.items():
    short_name = name.replace("輕軌", "").replace("站", "")
    if short_name in CORE_DISPLAY:
        folium.Marker(
            location=coords,
            icon=folium.DivIcon(
                html=f'<div style="font-size: 14pt; color: #1b5e20; white-space: nowrap; font-weight: bold; text-shadow: 2px 2px 4px white;">{short_name}</div>'
            )
        ).add_to(m)

# 處理列車位置
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
            # 💡 核心修正：從 38 個站中找出最精準的目前位置
            current_nearest = get_nearest_station(lat, lon)
            
            popup_html = f"""
            <div style="width: 150px; font-family: 'Noto Sans TC', sans-serif;">
                <b>目前靠近：</b><br><span style="color:blue;">{current_nearest}</span><br>
                <b>運行方向：</b>{"順行 (外圈)" if direction==0 else "逆行 (內圈)"}<br>
                <b>更新時間：</b>{update_time_str}
            </div>
            """
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=200),
                icon=folium.Icon(color=train_color, icon='train', prefix='fa')
            ).add_to(m)
    st.write(f"✅ 成功偵測到 {len(positions)} 台列車！資料獲取正常。")
except:
    st.warning("目前地圖上無即時列車資訊。")

folium_static(m)

import time
time.sleep(30)
st.rerun()
