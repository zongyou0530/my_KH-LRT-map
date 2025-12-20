import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime

# 1. 基礎設定
st.set_page_config(page_title="高雄輕軌監測 VERSE 3-4", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
    html, body, [data-testid="stAppViewContainer"] { font-family: "Zen Maru Gothic", sans-serif !important; }
    h1 { font-family: "Dela Gothic One", cursive !important; font-weight: 400 !important; }
    .legend-box { background-color: #e3f2fd; border-left: 5px solid #2196f3; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    .arrival-card { background-color: #ffffff; border-radius: 8px; padding: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 5px solid #2e7d32; }
    .time-val { color: #d32f2f; font-weight: bold; font-size: 1.2em; }
</style>
''', unsafe_allow_html=True)

# 2. 全線站點 (確保地圖與看板可用)
STATIONS = {
    "哈瑪星": [22.6225, 120.2885], "愛河之心": [22.6565, 120.3028], "台鐵美術館": [22.6537, 120.2863],
    "夢時代": [22.5961, 120.3045], "旅運中心": [22.6133, 120.2974], "駁二大義": [22.6193, 120.2863],
    "內惟藝術中心": [22.6575, 120.2884], "凱旋瑞田": [22.5970, 120.3162], "籬仔內": [22.5978, 120.3236]
}

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data)
        return res.json().get('access_token')
    except: return None

def fetch_api(url, token):
    headers = {'Authorization': f'Bearer {token}'}
    try:
        return requests.get(url, headers=headers).json()
    except: return []

# --- 介面呈現 ---
st.title("🚂 高雄輕軌即時位置監測")

st.markdown('<div class="legend-box">💡 <b>圖例：</b>🔴 順行 (外圈) | 🔵 逆行 (內圈)</div>', unsafe_allow_html=True)
st.success("✅ VERSE 3-4 已修復 API 解析邏輯，並恢復地圖軌道路線顯示。")

token = get_token()
col1, col2 = st.columns([7, 3])

with col1:
    sel_map = st.selectbox("快速定位：", ["顯示全圖"] + list(STATIONS.keys()))
    map_loc = [22.6280, 120.3014] if sel_map == "顯示全圖" else STATIONS[sel_map]
    
    # 修正：使用具有詳細站名與路線的底圖 (OpenStreetMap 原始樣式最穩定)
    m = folium.Map(location=map_loc, zoom_start=13)
    
    if token:
        train_data = fetch_api('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', token)
        for t in train_data:
            try:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                folium.Marker([lat, lon], icon=folium.Icon(color='red' if t.get('Direction')==0 else 'blue', icon='train', prefix='fa')).add_to(m)
            except: continue
    folium_static(m)

with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇站點看板：", list(STATIONS.keys()), key="board_sel")
    
    if token:
        # 修正：TDX API 返回的是一個串列，需要安全疊代
        arrival_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/RealTimeArrival/KLRT?$filter=StationName/Zh_tw eq '{sel_st}'&$format=JSON"
        arrivals = fetch_api(arrival_url, token)
        
        if isinstance(arrivals, list) and len(arrivals) > 0:
            for info in arrivals:
                # 這裡最關鍵：安全抓取嵌套資料
                dest_name = info.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                estimate = info.get('EstimateTime', '--')
                
                # 排除過期或無效資料
                if estimate == '--': continue
                
                status = "即時進站" if int(estimate) <= 1 else f"約 {estimate} 分鐘"
                
                st.markdown(f'''
                <div class="arrival-card">
                    <small>往 {dest_name} 方向</small><br>
                    <b>狀態：</b><span class="time-val">{status}</span>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.warning("⏳ 該站目前無預估進站資訊")

st.caption(f"最後更新：{datetime.datetime.now().strftime('%H:%M:%S')}")
import time
time.sleep(30)
st.rerun()
