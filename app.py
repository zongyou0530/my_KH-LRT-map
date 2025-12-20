import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+P+One&family=Kiwi+Maru:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    .mochiy-font { font-family: 'Mochiy Pop P One', sans-serif !important; color: #2e7d32; }
    html, body, [data-testid="stAppViewContainer"], p, div, span, label {
        font-family: 'Kiwi Maru', serif !important;
        font-weight: normal !important;
    }
    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 15px; border-radius: 10px; margin-bottom: 15px; color: #0d47a1; }
    .legend-box { background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.9em; }
    
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 15px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 10px solid #ccc;
    }
    .dir-tag { display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 0.8em; margin-bottom: 5px; color: white; }
    .time-normal { font-size: 1.5em; color: #4D0000; }
    .time-urgent { font-size: 1.5em; color: #FF0000; }
</style>
''', unsafe_allow_html=True)

# 2. 車站資料字典
STATION_MAP = {
    "C1 籬仔內": "C1", "C2 凱旋瑞田": "C2", "C3 前鎮之星": "C3", "C4 凱旋中華": "C4", "C5 夢時代": "C5",
    "C6 經貿園區": "C6", "C7 軟體園區": "C7", "C8 高雄展覽館": "C8", "C9 旅運中心": "C9", "C10 光榮碼頭": "C10",
    "C11 真愛碼頭": "C11", "C12 駁二大義": "C12", "C13 駁二蓬萊": "C13", "C14 哈瑪星": "C14", "C15 壽山公園": "C15",
    "C16 文武聖殿": "C16", "C17 鼓山區公所": "C17", "C18 鼓山": "C18", "C19 馬卡道": "C19", "C20 台鐵美術館": "C20",
    "C21A 內惟藝術中心": "C21A", "C21 美術館": "C21", "C22 聯合醫院": "C22", "C23 龍華國小": "C23", "C24 愛河之心": "C24",
    "C25 新上國小": "C25", "C26 灣仔內": "C26", "C27 鼎山街": "C27", "C28 高雄高工": "C28", "C29 樹德家商": "C29",
    "C30 科工館": "C30", "C31 聖功醫院": "C31", "C32 凱旋公園": "C32", "C33 衛生局": "C33", "C34 五權國小": "C34",
    "C35 凱旋武昌": "C35", "C36 凱旋二聖": "C36", "C37 輕軌機廠": "C37"
}

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei'))

@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- UI 開始 ---
st.markdown('<div class="mochiy-font" style="font-size:42px;">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)

# 1. 藍色對話框
st.markdown('<div class="info-box">💡 <b>系統更新：</b> 已解決 17:00 尖峰時段 API 異常問題，並強化順逆向資料顯示。</div>', unsafe_allow_html=True)

# 2. 圖例說明
st.markdown('<div class="legend-box">📍 <b>即時圖例：</b> <span style="color:#2e7d32;">● 順行 (外圈)</span> | <span style="color:#1565c0;">● 逆行 (內圈)</span> | 🚦 每 30 秒自動更新</div>', unsafe_allow_html=True)

token = get_token()
map_ts, board_ts = "讀取中...", "讀取中..."
col1, col2 = st.columns([7.2, 2.8])

# --- 左側：地圖 ---
with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}, timeout=8).json()
            for t in live_pos.get('LivePositions', []):
                d_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']],
                    icon=folium.Icon(color=d_color, icon='train', prefix='fa')
                ).add_to(m)
            map_ts = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
        except: map_ts = "地圖資料更新稍慢..."
    folium_static(m, height=520, width=950)

# --- 右側：站牌 ---
with col2:
    st.markdown('<span class="mochiy-font" style="font-size:24px;">🚉 選擇車站</span>', unsafe_allow_html=True)
    sel_st_label = st.selectbox("手機端可撥動選單：", list(STATION_MAP.keys()), index=19)
    target_id = STATION_MAP[sel_st_label]

    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", headers={'Authorization': f'Bearer {token}'}, timeout=10)
            if resp.status_code == 200:
                all_data = resp.json()
                matched = [d for d in all_data if d.get('StationID') == target_id and d.get('EstimateTime') is not None]
                
                if matched:
                    matched.sort(key=lambda x: x.get('EstimateTime', 999))
                    for item in matched:
                        d_code = item.get('Direction')
                        d_label = "順行 (外圈)" if d_code == 0 else "逆行 (內圈)"
                        d_color = "#2e7d32" if d_code == 0 else "#1565c0"
                        est = int(item.get('EstimateTime', 0))
                        
                        t_style = "time-urgent" if est <= 2 else "time-normal"
                        t_msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                        
                        st.markdown(f'''
                        <div class="arrival-card" style="border-left-color: {d_color};">
                            <div class="dir-tag" style="background-color: {d_color};">{d_label}</div>
                            <div class="{t_style}">狀態：{t_msg}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    board_ts = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    st.info(f"⏳ 車站 {target_id} 目前暫無預估")
            else: st.warning("📡 API 伺服器稍忙，正在自動重試...")
        except: board_ts = "站牌資料嘗試重連中..."

# 3. 最下方的更新時間 (確保絕對顯示)
st.markdown(f'''
<hr>
<div style="color:gray; font-size:0.85em;">
📍 地圖更新時間：{map_ts}<br>
🕒 站牌更新時間：{board_ts}
</div>
''', unsafe_allow_html=True)

time.sleep(30)
st.rerun()
