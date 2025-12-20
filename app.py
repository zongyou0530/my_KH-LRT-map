import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime

# 1. 精簡後的 6 個常用核心站點
CORE_STATIONS = {
    "顯示全圖 (預設)": [22.6280, 120.3014, 13],
    "台鐵美術館": [22.6535, 120.2866, 16],
    "夢時代": [22.5961, 120.3045, 16],
    "旅運中心": [22.6133, 120.2974, 16],
    "駁二蓬萊": [22.6202, 120.2809, 16],
    "哈瑪星": [22.6220, 120.2885, 16],
    "愛河之心": [22.6565, 120.3028, 16]
}

# 2. 設定網頁與雲端字體 (Noto Sans TC)
st.set_page_config(page_title="高雄輕軌監測", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Sans TC', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚂 高雄輕軌即時位置監測")

# 3. 側邊欄控制
selected_station = st.sidebar.selectbox("快速切換至站點：", list(CORE_STATIONS.keys()))
zoom_target = CORE_STATIONS[selected_station]

# 4. 取得 Token 與資料 (延用你成功的邏輯)
def get_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
    return requests.post(auth_url, data=data).json().get('access_token')

def get_data(token):
    api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$top=30&$format=JSON'
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(api_url, headers=headers)
    data = res.json()
    return data.get('LivePositions', []) if isinstance(data, dict) else []

# 5. 初始化地圖
m = folium.Map(location=[zoom_target[0], zoom_target[1]], zoom_start=zoom_target[2], tiles="OpenStreetMap")

# 繪製 6 個核心站點 (綠色粗體字)
for name, coords in CORE_STATIONS.items():
    if name != "顯示全圖 (預設)":
        folium.Marker(
            location=[coords[0], coords[1]],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 14pt; color: #1b5e20; white-space: nowrap; font-weight: bold; text-shadow: 2px 2px 4px white;">{name}</div>'
            )
        ).add_to(m)

# 抓取資料並繪製列車
try:
    token = get_token()
    positions = get_data(token)
    
    # 取得現在時間 (用於對話框顯示)
    now_dt = datetime.datetime.now() + datetime.timedelta(hours=8)
    update_time_str = now_dt.strftime('%H:%M:%S')

    for train in positions:
        pos = train.get('TrainPosition', {})
        lat, lon = pos.get('PositionLat'), pos.get('PositionLon')
        
        if lat and lon:
            direction = train.get('Direction', 0)
            train_color = 'red' if direction == 0 else 'blue'
            dir_text = "順行 (外圈)" if direction == 0 else "逆行 (內圈)"
            
            # 💡 自訂美化對話框 (解決換行問題)
            popup_html = f"""
            <div style="width: 150px; font-family: 'Noto Sans TC', sans-serif; line-height: 1.6;">
                <b style="color: #333;">站牌：</b> 近 {selected_station if selected_station != '顯示全圖 (預設)' else '輕軌路線'}<br>
                <b style="color: #333;">方向：</b> {dir_text}<br>
                <b style="color: #333;">更新：</b> {update_time_str}
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=f"車號: {train.get('TripID')}",
                icon=folium.Icon(color=train_color, icon='train', prefix='fa')
            ).add_to(m)

except Exception as e:
    st.error(f"資料更新中... {e}")

# 顯示地圖
folium_static(m)
st.write(f"最後更新時間 (台灣): {update_time_str}")
