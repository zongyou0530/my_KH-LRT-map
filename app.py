import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time
import base64
import os

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

# --- 時間邏輯 ---
tz = pytz.timezone('Asia/Taipei')
now = datetime.datetime.now(tz)
# 營運時間：06:30 ~ 22:30
is_running = (now.hour > 6 or (now.hour == 6 and now.minute >= 30)) and (now.hour < 22 or (now.hour == 22 and now.minute <= 30))
now_str = now.strftime('%Y-%m-%d %H:%M:%S')

# --- 字體載入 ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode()
        font_css = f'''
        @font-face {{ font-family: 'ZongYouFont'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 52px; color: #1a531b; margin-bottom: 5px; }}
        .custom-subtitle {{ font-family: 'ZongYouFont' !important; font-size: 32px; color: #2e7d32; margin-bottom: 10px; }}
        .time-header {{ background-color: #2e7d32; color: white; padding: 2px 10px; border-radius: 4px; font-size: 1.1em; display: inline-block; font-family: 'ZongYouFont' !important; }}
        .time-val {{ font-family: 'ZongYouFont' !important; font-size: 2.2em; color: #4D0000; margin-top: 5px; }}
        '''
    except: pass

# 2. 注入 CSS
st.markdown(f'''
<style>
    {font_css}
    html, body, [data-testid="stAppViewContainer"] {{ font-family: 'Kiwi Maru', serif; }}
    .author-msg {{ background-color: #fff3e0; border-left: 5px solid #ff9800; padding: 12px; border-radius: 5px; margin-bottom: 15px; color: #e65100; }}
    .legend-box {{ background-color: #f1f8e9; border: 1px solid #c5e1a5; padding: 10px; border-radius: 8px; color: #33691e; font-size: 0.9em; }}
    .warning-box {{ background-color: #fffde7; border: 2px solid #fdd835; padding: 15px; border-radius: 8px; color: #827717; text-align: center; margin-bottom: 20px; }}
    .arrival-card {{ background-color: #ffffff; border-radius: 10px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 10px solid #2e7d32; }}
    .update-box {{ background-color: #eeeeee; padding: 15px; border-radius: 8px; color: #616161; font-size: 0.85em; margin-top: 50px; border: 1px dashed #bdbdbd; }}
    /* 強制按鈕寬度一致且不彈出鍵盤 */
    .stButton>button {{ width: 100% !important; border-radius: 10px !important; height: 45px; }}
</style>
''', unsafe_allow_html=True)

# 3. 資料定義
STATION_MAP = {
    "C1": "C1 籬仔內", "C2": "C2 凱旋瑞田", "C3": "C3 前鎮之星", "C4": "C4 凱旋中華", "C5": "C5 夢時代",
    "C6": "C6 經貿園區", "C7": "C7 軟體園區", "C8": "C8 高雄展覽館", "C9": "C9 旅運中心", "C10": "C10 光榮碼頭",
    "C11": "C11 真愛碼頭", "C12": "C12 駁二大義", "C13": "C13 駁二蓬萊", "C14": "C14 哈瑪星", "C15": "C15 壽山公園",
    "C16": "C16 文武聖殿", "C17": "C17 鼓山區公所", "C18": "C18 鼓山", "C19": "C19 馬卡道", "C20": "C20 台鐵美術館",
    "C21A": "C21A 內維中心", "C21": "C21 美術館", "C22": "C22 聯合醫院", "C23": "C23 龍華國小", "C24": "C24 愛河之心",
    "C25": "C25 新上國小", "C26": "C26 灣仔內", "C27": "C27 鼎山街", "C28": "C28 高雄高工", "C29": "C29 樹德家商",
    "C30": "C30 科工館", "C31": "C31 聖功醫院", "C32": "C32 凱旋公園", "C33": "C33 衛生局", "C34": "C34 五權國小",
    "C35": "C35 凱旋武昌", "C36": "C36 凱旋二聖", "C37": "C37 輕軌機廠"
}

# --- UI 開始 ---
st.markdown('<div class="custom-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)

# A. 非營運提示
if not is_running:
    st.markdown('<div class="warning-box">⚠️ ⚠️ 提醒：目前為非營運時段（營運時間：06:30 - 22:30）。資料將暫停更新或顯示舊資訊。</div>', unsafe_allow_html=True)

# B. 作者留言與圖例
col_msg, col_leg = st.columns([1, 1])
with col_msg:
    st.markdown('<div class="author-msg">✍️ <b>作者留言：</b><br>這是一個實驗性質的輕軌站點監測，若有誤差請見諒。</div>', unsafe_allow_html=True)
with col_leg:
    st.markdown('<div class="legend-box">📍 <b>地圖標示：</b><br>🟢 順行 (外圈) | 🔵 逆行 (內圈)</div>', unsafe_allow_html=True)

# C. 主內容
col_map, col_info = st.columns([7, 3])

@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

token = get_token()

with col_map:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token and is_running:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_pos.get('LivePositions', []):
                d_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], icon=folium.Icon(color=d_color, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=950)

with col_info:
    st.markdown('<div class="custom-subtitle">🚉 選擇車站</div>', unsafe_allow_html=True)
    
    # 使用按鈕格取代 Selectbox，徹底解決打字問題
    with st.container():
        st.write("請直接點選下方站點編號：")
        grid_cols = st.columns(4)
        station_keys = list(STATION_MAP.keys())
        
        # 紀錄選中的站點
        if 'selected_st' not in st.session_state:
            st.session_state.selected_st = 'C20'
            
        for idx, sid in enumerate(station_keys):
            if grid_cols[idx % 4].button(sid, key=f"btn_{sid}"):
                st.session_state.selected_st = sid
        
        target_id = st.session_state.selected_st
        st.success(f"目前顯示：{STATION_MAP[target_id]}")

    # 列車抵達資訊
    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", headers={'Authorization': f'Bearer {token}'})
            matched = [d for d in resp.json() if d.get('StationID') == target_id and d.get('EstimateTime') is not None]
            if matched:
                matched.sort(key=lambda x: x.get('EstimateTime', 999))
                for item in matched:
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'''
                    <div class="arrival-card">
                        <div class="time-header">輕軌預計抵達</div>
                        <div class="time-val">{msg}</div>
                    </div>''', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 資料更新中")
    
    st.markdown(f'<p style="font-size:0.8em; color:#999; margin-top:10px;">🕒 更新：{now.strftime("%H:%M:%S")}</p>', unsafe_allow_html=True)

# D. 更新摘要移至最下方
st.markdown(f'''
<div class="update-box">
    <b>📋 版本更新紀錄 (V5.1)</b><br>
    • <b>徹底解決鍵盤彈出</b>：將選擇框改為按鈕矩陣，使用者點擊編號即可切換，無需打字。<br>
    • <b>夜間營運偵測</b>：自動檢測當前時間，於非營運時段顯示黃色警示。<br>
    • <b>作者留言板</b>：於最上方新增作者專屬留言區與地圖圖例說明。<br>
    • <b>更新時間下放</b>：將技術性版本紀錄移至網頁最底部。
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
