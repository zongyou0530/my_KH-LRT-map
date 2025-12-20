import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime

# 1. 頁面基本設定
st.set_page_config(page_title="高雄輕軌即時監測 VERSE 3-3", layout="wide")

# CSS 修復：確保標題不加粗，圖例與看板樣式美化
st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
    html, body, [data-testid="stAppViewContainer"] { font-family: "Zen Maru Gothic", sans-serif !important; }
    h1 { font-family: "Dela Gothic One", cursive !important; font-weight: 400 !important; color: #2c3e50; margin-bottom: 0px !important; }
    
    /* 藍色圖例框 */
    .legend-box {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 10px 0px 20px 0px;
        font-size: 0.95em;
    }
    /* 電子看板卡片 */
    .arrival-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        margin-bottom: 10px;
        border-left: 5px solid #1b5e20;
    }
    .time-val { color: #d32f2f; font-weight: 800; font-size: 1.2em; }
</style>
''', unsafe_allow_html=True)

# 2. 站點資料 (包含所有站點以防看板切換錯誤)
STATIONS = {
    "哈瑪星": [22.6225, 120.2885], "愛河之心": [22.6565, 120.3028], "台鐵美術館": [22.6537, 120.2863],
    "夢時代": [22.5961, 120.3045], "旅運中心": [22.6133, 120.2974], "駁二蓬萊": [22.6202, 120.2809],
    "駁二大義": [22.6193, 120.2863], "光榮碼頭": [22.6178, 120.2952], "高雄展覽館": [22.6105, 120.2995]
}

# --- API 函數 (增加嚴格防錯) ---
def get_token():
    try:
        auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post(auth_url, data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

def get_live_data(token):
    if not token: return []
    try:
        api_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
        headers = {'Authorization': f'Bearer {token}'}
        return requests.get(api_url, headers=headers, timeout=5).json().get('LivePositions', [])
    except: return []

def get_arrival(token, name):
    if not token: return []
    try:
        api_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/RealTimeArrival/KLRT?$filter=StationName/Zh_tw eq '{name}'&$format=JSON"
        headers = {'Authorization': f'Bearer {token}'}
        return requests.get(api_url, headers=headers, timeout=5).json()
    except: return []

# --- 介面呈現 ---
st.title("🚂 高雄輕軌即時位置監測")

# 1. 恢復：藍色對話框 (圖例說明)
st.markdown('''
<div class="legend-box">
    💡 <b>圖例說明：</b><br>
    🔴 <b>順行 (外圈)：</b> 往 凱旋公園 ➔ 愛河之心 ➔ 哈瑪星 方向<br>
    🔵 <b>逆行 (內圈)：</b> 往 哈瑪星 ➔ 愛河之心 ➔ 凱旋公園 方向
</div>
''', unsafe_allow_html=True)

# 2. 恢復：綠色系統提示
st.success("✅ VERSE 3-3：已修復 API 導致的崩潰問題，底圖切換為 Voyager 以顯示路線。")

token = get_token()
col1, col2 = st.columns([7, 3])

with col1:
    sel_map = st.selectbox("快速定位站點：", ["顯示全圖"] + list(STATIONS.keys()))
    center = [22.6280, 120.3014] if sel_map == "顯示全圖" else STATIONS[sel_map]
    
    # 地圖底圖：使用 Voyager 確保能看到鐵路線，且有簡約感
    m = folium.Map(location=center, zoom_start=13, tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', attr='CartoDB')
    
    # 放置列車圖標
    trains = get_live_data(token)
    for t in trains:
        try:
            lat = t['TrainPosition']['PositionLat']
            lon = t['TrainPosition']['PositionLon']
            direct = t.get('Direction', 0)
            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color='red' if direct==0 else 'blue', icon='train', prefix='fa')
            ).add_to(m)
        except: continue # 就算某一輛車資料錯了，也不要影響整張地圖

    folium_static(m, width=None)

with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇站點看板：", list(STATIONS.keys()))
    
    arrivals = get_arrival(token, sel_st)
    if arrivals:
        for info in arrivals:
            # 極其嚴格的欄位抓取，避免 AttributeError
            dest_obj = info.get('DestinationStationName', {})
            dest_name = dest_obj.get('Zh_tw', '端點站') if isinstance(dest_obj, dict) else "端點站"
            
            time_gap = info.get('EstimateTime', '--')
            status = "即時進站" if str(time_gap).isdigit() and int(time_gap) <= 1 else f"約 {time_gap} 分鐘"
            
            st.markdown(f'''
            <div class="arrival-card">
                <small style="color:gray">開往：{dest_name}</small><br>
                <b>{status}</b>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.write("⏳ 目前無列車預估資訊")

st.caption(f"最後更新：{datetime.datetime.now().strftime('%H:%M:%S')}")

import time
time.sleep(30)
st.rerun()
