import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime

# 1. 頁面風格設定
st.set_page_config(page_title="高雄輕軌監測 VERSE 3-5", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
    html, body, [data-testid="stAppViewContainer"] { font-family: "Zen Maru Gothic", sans-serif !important; }
    h1 { font-family: "Dela Gothic One", cursive !important; font-weight: 400 !important; color: #2c3e50; }
    .legend-box { background-color: #e3f2fd; border-left: 5px solid #2196f3; padding: 12px; border-radius: 5px; margin-bottom: 15px; }
    .arrival-card { background-color: #ffffff; border-radius: 8px; padding: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 5px solid #2e7d32; }
    .status-text { font-size: 1.1em; font-weight: 700; color: #d32f2f; }
    .update-footer { font-size: 0.85em; color: #666; line-height: 1.5; margin-top: 20px; }
</style>
''', unsafe_allow_html=True)

# 2. 全線座標
STATIONS = {
    "哈瑪星": [22.6225, 120.2885], "愛河之心": [22.6565, 120.3028], "台鐵美術館": [22.6537, 120.2863],
    "夢時代": [22.5961, 120.3045], "旅運中心": [22.6133, 120.2974], "駁二大義": [22.6193, 120.2863],
    "駁二蓬萊": [22.6202, 120.2809], "壽山公園": [22.6253, 120.2798], "前鎮之星": [22.5986, 120.3094]
}

# --- API 工具 ---
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

def fetch_tdx(url, token):
    if not token: return None
    try:
        headers = {'Authorization': f'Bearer {token}'}
        return requests.get(url, headers=headers, timeout=5).json()
    except: return None

# --- 介面開始 ---
st.title("🚂 高雄輕軌即時位置監測")

# 恢復藍色圖標說明框
st.markdown('<div class="legend-box">💡 <b>圖例說明：</b>🔴 順行 (外圈) | 🔵 逆行 (內圈)</div>', unsafe_allow_html=True)

token = get_token()
col1, col2 = st.columns([7, 3])

# 地圖更新時間與站牌更新時間初始化
map_time = "--:--:--"
info_time = "--:--:--"

with col1:
    sel_map = st.selectbox("快速定位站點：", ["顯示全圖"] + list(STATIONS.keys()))
    center = [22.6280, 120.3014] if sel_map == "顯示全圖" else STATIONS[sel_map]
    
    # 使用標準 OpenStreetMap 確保路線站名清晰
    m = folium.Map(location=center, zoom_start=13)
    
    train_data = fetch_tdx('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', token)
    if train_data:
        map_time = datetime.datetime.now().strftime('%H:%M:%S')
        for t in train_data:
            try:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                folium.Marker([lat, lon], icon=folium.Icon(color='red' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
            except: continue
    
    folium_static(m)

with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢站點：", list(STATIONS.keys()), key="arrival_sel")
    
    # 解析你截圖中的 StationArrival 結構 (包含 Inbound/Outbound)
    arrival_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/RealTimeArrival/KLRT?$filter=StationName/Zh_tw eq '{sel_st}'&$format=JSON"
    arrival_data = fetch_tdx(arrival_url, token)
    
    if arrival_data:
        info_time = datetime.datetime.now().strftime('%H:%M:%S')
        for info in arrival_data:
            # 分別處理順行與逆行
            for direction in ['Inbound', 'Outbound']:
                dir_data = info.get(direction)
                if dir_data and 'EstimateTime' in dir_data:
                    est = dir_data['EstimateTime']
                    dest = "順行方向" if direction == 'Inbound' else "逆行方向"
                    status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card">
                        <small style="color:gray">{dest}</small><br>
                        狀態：<span class="status-text">{status}</span>
                    </div>
                    ''', unsafe_allow_html=True)
    else:
        st.warning("⏳ 該站目前無即時進站預估")

# 3. 雙行更新時間標籤
st.markdown(f'''
<div class="update-footer">
    📍 地圖位置更新時間：{map_time}<br>
    🕒 站牌資訊更新時間：{info_time}
</div>
''', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
