import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 初始化與風格
st.set_page_config(page_title="高雄輕軌監測 V3.8", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
    html, body, [data-testid="stAppViewContainer"] { font-family: "Zen Maru Gothic", sans-serif !important; }
    h1 { font-family: "Dela Gothic One", cursive !important; font-weight: 400 !important; color: #2c3e50; }
    .legend-box { background-color: #e3f2fd; border-left: 5px solid #2196f3; padding: 12px; border-radius: 5px; margin-bottom: 15px; }
    .system-msg { background-color: #e8f5e9; border-left: 5px solid #4caf50; padding: 10px; border-radius: 5px; margin-bottom: 15px; font-size: 0.9em; color: #2e7d32; }
    .arrival-card { 
        background-color: #ffffff; border-radius: 8px; padding: 15px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 12px; border-left: 6px solid #2e7d32; 
    }
    .status-text { font-size: 1.3em; font-weight: 800; color: #d32f2f; }
    .update-footer { font-size: 0.8em; color: #888; margin-top: 20px; line-height: 1.8; }
</style>
''', unsafe_allow_html=True)

# 2. 基本資料
STATIONS = {
    "哈瑪星": [22.6225, 120.2885], "愛河之心": [22.6565, 120.3028], "台鐵美術館": [22.6537, 120.2863],
    "夢時代": [22.5961, 120.3045], "旅運中心": [22.6133, 120.2974], "駁二大義": [22.6193, 120.2863],
    "內惟藝術中心": [22.6575, 120.2884], "凱旋瑞田": [22.5970, 120.3162], "籬仔內": [22.5978, 120.3236],
    "光榮碼頭": [22.6186, 120.2931], "真愛碼頭": [22.6218, 120.2913]
}

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- 介面呈現 ---
st.title("🚂 高雄輕軌即時位置監測")

st.markdown('<div class="legend-box">💡 <b>圖例說明：</b>🔴 順行 (外圈) | 🔵 逆行 (內圈) | 點擊列車可看詳細資訊</div>', unsafe_allow_html=True)
st.markdown('<div class="system-msg">✅ 系統提示：已修復 API 欄位對接，並加入圖標點擊彈出對話框。</div>', unsafe_allow_html=True)

token = get_token()
map_update = "--"
info_update = "--"

col1, col2 = st.columns([7, 3])

with col1:
    sel_map = st.selectbox("快速切換至站點：", ["顯示全圖"] + list(STATIONS.keys()))
    center = [22.6280, 120.3014] if sel_map == "顯示全圖" else STATIONS[sel_map]
    
    # 使用預設底圖確保路線清楚
    m = folium.Map(location=center, zoom_start=13)
    
    if token:
        try:
            # 列車位置 API
            live_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            trains = requests.get(live_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json().get('LivePositions', [])
            map_update = get_now_tw()
            
            for t in trains:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                dir_code = t.get('Direction', 0)
                dir_str = "順行 (外圈)" if dir_code == 0 else "逆行 (內圈)"
                train_id = t.get('TrainNo', '未知編號')
                
                # 加入 Popup 對話框內容
                pop_html = f"<b>列車編號:</b> {train_id}<br><b>行駛方向:</b> {dir_str}"
                
                folium.Marker(
                    [lat, lon], 
                    popup=folium.Popup(pop_html, max_width=200),
                    icon=folium.Icon(color='red' if dir_code==0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m)

with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢站點：", list(STATIONS.keys()), key="board")
    
    if token:
        try:
            # 【關鍵修正】使用 RealTimeArrival 才能對接你截圖中的欄位
            arrival_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/RealTimeArrival/KLRT?$filter=StationName/Zh_tw eq '{sel_st}'&$format=JSON"
            arrivals = requests.get(arrival_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json()
            
            if arrivals and isinstance(arrivals, list):
                info_update = get_now_tw()
                for item in arrivals:
                    # 對接截圖欄位：DestinationStationName -> Zh_tw
                    dest = item.get('DestinationStationName', {}).get('Zh_tw', '未知方向')
                    # 對接截圖欄位：EstimateTime
                    est = item.get('EstimateTime')
                    
                    if est is not None:
                        status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                        st.markdown(f'''
                        <div class="arrival-card">
                            <small style="color:gray">開往：{dest}</small><br>
                            <b>狀態：</b><span class="status-text">{status}</span>
                        </div>
                        ''', unsafe_allow_html=True)
            else:
                st.info("⏳ 該站點目前無列車預估資訊")
        except:
            st.error("❌ 站牌資料連線異常")

st.markdown(f'''
<div class="update-footer">
    🌍 地圖列車更新：{map_update} (台北時間)<br>
    🕒 站牌資訊更新：{info_update} (台北時間)
</div>
''', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
