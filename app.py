import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz # 用於處理台灣時間

# 1. 基礎設定與字體
st.set_page_config(page_title="高雄輕軌即時監測 V3.7", layout="wide")

# 強制載入字體與美化 CSS
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
    .update-footer { font-size: 0.8em; color: #888; margin-top: 30px; line-height: 1.8; border-top: 1px solid #eee; padding-top: 10px; }
</style>
''', unsafe_allow_html=True)

# 2. 定義站點 (增加更多站點以確保地圖縮放正確)
STATIONS = {
    "哈瑪星": [22.6225, 120.2885], "愛河之心": [22.6565, 120.3028], "台鐵美術館": [22.6537, 120.2863],
    "夢時代": [22.5961, 120.3045], "旅運中心": [22.6133, 120.2974], "駁二大義": [22.6193, 120.2863],
    "內惟藝術中心": [22.6575, 120.2884], "凱旋瑞田": [22.5970, 120.3162], "籬仔內": [22.5978, 120.3236]
}

def get_now_tw():
    """獲取正確的台灣時間文字"""
    tw_tz = pytz.timezone('Asia/Taipei')
    return datetime.datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- 介面呈現 ---
st.title("🚂 高雄輕軌即時位置監測")

# 恢復：藍色圖例框
st.markdown('<div class="legend-box">💡 <b>圖例說明：</b>🔴 順行 (外圈) | 🔵 逆行 (內圈)</div>', unsafe_allow_html=True)

# 恢復：綠色提示框
st.markdown('<div class="system-msg">✅ 系統提示：已修正 API 解析邏輯，並同步為台灣時間 (Asia/Taipei)。</div>', unsafe_allow_html=True)

token = get_token()
map_update = "未更新"
info_update = "未更新"

col1, col2 = st.columns([7, 3])

with col1:
    sel_map = st.selectbox("快速切換至站點：", ["顯示全圖"] + list(STATIONS.keys()))
    center = [22.6280, 120.3014] if sel_map == "顯示全圖" else STATIONS[sel_map]
    
    # 地圖底圖：回歸最原始的 OpenStreetMap (保證能看到輕軌路線圖與站名)
    m = folium.Map(location=center, zoom_start=13)
    
    if token:
        try:
            live_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            trains = requests.get(live_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json().get('LivePositions', [])
            map_update = get_now_tw()
            for t in trains:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                color = 'red' if t.get('Direction') == 0 else 'blue'
                folium.Marker([lat, lon], icon=folium.Icon(color=color, icon='train', prefix='fa')).add_to(m)
        except: pass
    
    folium_static(m)

with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢站點：", list(STATIONS.keys()), key="board")
    
    if token:
        try:
            # 針對 125632.png 截圖中的高雄輕軌 API 結構進行精準解析
            arrival_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/RealTimeArrival/KLRT?$filter=StationName/Zh_tw eq '{sel_st}'&$format=JSON"
            res = requests.get(arrival_url, headers={'Authorization': f'Bearer {token}'}, timeout=5)
            arrivals = res.json()
            
            if isinstance(arrivals, list) and len(arrivals) > 0:
                info_update = get_now_tw()
                for item in arrivals:
                    # 抓取目的地：item['DestinationStationName']['Zh_tw']
                    dest = item.get('DestinationStationName', {}).get('Zh_tw', '未知方向')
                    # 抓取預估時間：item['EstimateTime']
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
                st.info("⏳ 目前該站無列車預估資訊")
        except:
            st.error("❌ 站牌資料解析失敗，請確認 API 授權")

# 4. 底部雙行更新資訊 (改為台灣時間)
st.markdown(f'''
<div class="update-footer">
    🌍 地圖列車位置最後更新時間 (台北)：{map_update}<br>
    🕒 站牌到站資訊最後更新時間 (台北)：{info_update}
</div>
''', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
