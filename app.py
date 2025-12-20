import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與精美樣式
st.set_page_config(page_title="高雄輕軌監測 V4.0", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
    html, body, [data-testid="stAppViewContainer"] { font-family: "Zen Maru Gothic", sans-serif !important; }
    h1 { font-family: "Dela Gothic One", cursive !important; font-weight: 400 !important; color: #2c3e50; }
    .legend-box { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 12px; border-radius: 8px; margin-bottom: 15px; }
    .arrival-card { 
        background-color: #ffffff; border-radius: 8px; padding: 12px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 10px; border-left: 5px solid #2e7d32; 
    }
    .status-text { font-size: 1.2em; font-weight: 800; color: #d32f2f; }
    .update-footer { font-size: 0.8em; color: #666; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }
</style>
''', unsafe_allow_html=True)

# 2. 全線 38 站點座標資料 (完整版)
ALL_STATIONS = {
    "籬仔內": [22.5978, 120.3236], "凱旋瑞田": [22.5970, 120.3162], "前鎮之星": [22.5986, 120.3094],
    "凱旋中華": [22.6006, 120.3023], "夢時代": [22.5961, 120.3045], "經貿園區": [22.6015, 120.3012],
    "軟體園區": [22.6062, 120.3013], "高雄展覽館": [22.6105, 120.2995], "旅運中心": [22.6133, 120.2974],
    "光榮碼頭": [22.6178, 120.2952], "真愛碼頭": [22.6214, 120.2923], "駁二大義": [22.6193, 120.2863],
    "駁二蓬萊": [22.6202, 120.2809], "哈瑪星": [22.6225, 120.2885], "壽山公園站": [22.6253, 120.2798],
    "文武聖殿": [22.6300, 120.2800], "鼓山區公所": [22.6360, 120.2830], "鼓山": [22.6410, 120.2840],
    "馬卡道": [22.6480, 120.2850], "台鐵美術館": [22.6537, 120.2863], "內惟藝術中心": [22.6575, 120.2884],
    "美術館": [22.6590, 120.2930], "聯合醫院": [22.6570, 120.2980], "龍華國小": [22.6560, 120.3010],
    "愛河之心": [22.6565, 120.3028], "新上國小": [22.6570, 120.3100], "灣仔內": [22.6530, 120.3180],
    "鼎山街": [22.6510, 120.3230], "高雄高工": [22.6470, 120.3270], "樹德家商": [22.6420, 120.3300],
    "科工館": [22.6380, 120.3330], "聖功醫院": [22.6320, 120.3320], "凱旋公園": [22.6280, 120.3310],
    "衛生局": [22.6210, 120.3300], "五權國小": [22.6150, 120.3300], "凱旋武昌": [22.6100, 120.3290],
    "凱旋二聖": [22.6050, 120.3270], "輕軌機廠": [22.6010, 120.3250]
}

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')

def get_token():
    try:
        data = {
            'grant_type': 'client_credentials', 
            'client_id': st.secrets["TDX_CLIENT_ID"], 
            'client_secret': st.secrets["TDX_CLIENT_SECRET"]
        }
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- 介面呈現 ---
st.title("🚂 高雄輕軌即時位置監測")

st.markdown('<div class="legend-box">💡 <b>圖例：</b>🔴 順行 (外圈) | 🔵 逆行 (內圈) | ⚪ 固定站點<br><b>操作：</b>點擊地圖上的列車圖標可查看詳細編號與方向。</div>', unsafe_allow_html=True)

token = get_token()
map_update = "--"
info_update = "--"

col1, col2 = st.columns([7, 3])

with col1:
    selected_station = st.selectbox("快速切換地圖視角：", ["顯示全圖"] + list(ALL_STATIONS.keys()))
    center = [22.6280, 120.3014] if selected_station == "顯示全圖" else ALL_STATIONS[selected_station]
    zoom_val = 13 if selected_station == "顯示全圖" else 16
    
    m = folium.Map(location=center, zoom_start=zoom_val)
    
    # A. 標註所有固定站點
    for name, loc in ALL_STATIONS.items():
        folium.CircleMarker(
            location=loc, radius=4, color="#95a5a6", fill=True, 
            fill_color="white", popup=name, tooltip=name
        ).add_to(m)
    
    # B. 標註即時列車位置
    if token:
        try:
            live_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            trains = requests.get(live_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json().get('LivePositions', [])
            map_update = get_now_tw()
            
            for t in trains:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                dir_code = t.get('Direction', 0)
                train_id = t.get('TrainNo', '未知')
                dir_name = "順行 (外圈)" if dir_code == 0 else "逆行 (內圈)"
                
                # 彈出對話框
                pop_html = f"<b>列車編號:</b> {train_id}<br><b>行駛方向:</b> {dir_name}"
                
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(pop_html, max_width=200),
                    tooltip=f"列車 {train_id}",
                    icon=folium.Icon(color='red' if dir_code==0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m)

with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st_info = st.selectbox("選擇查詢車站：", list(ALL_STATIONS.keys()), key="board_sel")
    
    if token:
        try:
            # 使用 LiveBoard API
            board_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationName/Zh_tw eq '{sel_st_info}'&$format=JSON"
            board_data = requests.get(board_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json()
            
            if board_data and isinstance(board_data, list) and len(board_data) > 0:
                info_update = get_now_tw()
                for item in board_data:
                    headsign = item.get('TripHeadSign', '未知方向')
                    dest = item.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                    est = item.get('EstimateTime')
                    
                    if est is not None:
                        status_val = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                        st.markdown(f'''
                        <div class="arrival-card">
                            <small style="color:gray">{headsign} (開往 {dest})</small><br>
                            <b>狀態：</b><span class="status-text">{status_val}</span>
                        </div>
                        ''', unsafe_allow_html=True)
            else:
                st.info(f"⏳ 「{sel_st_info}」目前無預估進站資訊")
        except:
            st.error("站牌資料連線中...")

# 4. 底部資訊
st.markdown(f'''
<div class="update-footer">
    📍 地圖更新時間：{map_update}<br>
    🕒 站牌更新時間：{info_update}
</div>
''', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
