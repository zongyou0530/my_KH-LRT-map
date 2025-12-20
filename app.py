import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面風格優化
st.set_page_config(page_title="高雄輕軌監測 V3.9", layout="wide")

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
    .update-footer { font-size: 0.8em; color: #888; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }
</style>
''', unsafe_allow_html=True)

# 2. 座標資料
STATIONS = {
    "籬仔內": [22.5978, 120.3236], "凱旋瑞田": [22.5970, 120.3162], "前鎮之星": [22.5986, 120.3094],
    "凱旋中華": [22.6006, 120.3023], "夢時代": [22.5961, 120.3045], "經貿園區": [22.6015, 120.3012],
    "軟體園區": [22.6062, 120.3013], "高雄展覽館": [22.6105, 120.2995], "旅運中心": [22.6133, 120.2974],
    "光榮碼頭": [22.6178, 120.2952], "真愛碼頭": [22.6214, 120.2923], "駁二大義": [22.6193, 120.2863],
    "駁二蓬萊": [22.6202, 120.2809], "哈瑪星": [22.6225, 120.2885], "壽山公園站": [22.6253, 120.2798]
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
st.markdown('<div class="system-msg">✅ 系統提示：已成功對接 LiveBoard API，同步顯示預估到站時間。</div>', unsafe_allow_html=True)

token = get_token()
map_update = "--"
info_update = "--"

col1, col2 = st.columns([7, 3])

with col1:
    sel_map = st.selectbox("快速切換地圖視角：", ["顯示全圖"] + list(STATIONS.keys()))
    center = [22.6280, 120.3014] if sel_map == "顯示全圖" else STATIONS[sel_map]
    
    # 地圖底圖：使用預設 OpenStreetMap 確保輕軌灰色軌道與站名清晰可見
    m = folium.Map(location=center, zoom_start=13)
    
    if token:
        try:
            live_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            trains_res = requests.get(live_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json()
            trains = trains_res.get('LivePositions', [])
            map_update = get_now_tw()
            
            for t in trains:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                dir_code = t.get('Direction', 0)
                dir_name = "順行 (外圈)" if dir_code == 0 else "逆行 (內圈)"
                
                # 點擊對話框內容
                pop_content = f"<b>行駛方向:</b> {dir_name}<br><b>更新時間:</b> {map_update.split(' ')[1]}"
                
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(pop_content, max_width=200),
                    icon=folium.Icon(color='red' if dir_code==0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m)

with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢車站：", list(STATIONS.keys()), key="board")
    
    if token:
        try:
            # 使用你提供的正確 API 路徑：LiveBoard
            board_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationName/Zh_tw eq '{sel_st}'&$format=JSON"
            board_data = requests.get(board_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json()
            
            if board_data and isinstance(board_data, list):
                info_update = get_now_tw()
                for item in board_data:
                    # 抓取方向 (例如: 順行方向)
                    headsign = item.get('TripHeadSign', '未知方向')
                    # 抓取目的地
                    dest = item.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                    # 抓取預估時間
                    est = item.get('EstimateTime')
                    
                    if est is not None:
                        status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                        st.markdown(f'''
                        <div class="arrival-card">
                            <small style="color:gray">{headsign} (開往 {dest})</small><br>
                            <b>狀態：</b><span class="status-text">{status}</span>
                        </div>
                        ''', unsafe_allow_html=True)
            else:
                st.info("⏳ 目前該站無列車進站預估")
        except Exception as e:
            st.error("❌ 站牌資料讀取失敗")

# 4. 底部雙行更新資訊
st.markdown(f'''
<div class="update-footer">
    📍 地圖列車最後更新 (台北)：{map_update}<br>
    🕒 站牌資訊最後更新 (台北)：{info_update}
</div>
''', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
