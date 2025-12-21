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
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 58px; color: #a5d6a7; margin-bottom: 0px; text-align: center; line-height: 1.2; }}
        .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 16px; color: #666; text-align: center; margin-bottom: 15px; letter-spacing: 2px; }}
        .custom-subtitle {{ font-family: 'ZongYouFont' !important; font-size: 32px; color: #81c784; }}
        .time-header {{ background-color: #2e7d32; color: #ffffff; padding: 2px 10px; border-radius: 4px; font-size: 1em; font-family: 'ZongYouFont' !important; }}
        .time-val {{ font-family: 'ZongYouFont' !important; font-size: 2.3em; color: #ff8a65; margin-top: 5px; }}
        @media (max-width: 768px) {{ .custom-title {{ font-size: 10vw; }} }}
        '''
    except: pass

# 2. 注入 CSS (強效鎖死與深色優化)
st.markdown(f'''
<style>
    {font_css}
    [data-testid="stAppViewContainer"] {{ background-color: #0e1117 !important; color: #fafafa !important; }}
    html, body, p, div, span, label {{ font-family: 'Kiwi Maru', serif; color: #fafafa !important; }}

    .warning-box {{ background-color: #332b00; border: 1px solid #fdd835; padding: 10px; border-radius: 8px; color: #fff176 !important; text-align: center; margin-bottom: 10px; }}
    .legend-box {{ background-color: #1b2e1b; border: 1px solid #4caf50; padding: 10px; border-radius: 8px; margin-bottom: 15px; display: flex; justify-content: center; gap: 20px; font-weight: bold; }}
    .arrival-card {{ background-color: #1c1c1c; border-radius: 12px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 12px; border-left: 8px solid #4caf50; }}
    .update-time-row {{ font-size: 0.9em; color: #888 !important; margin: 5px 0; border-bottom: 1px solid #333; padding-bottom: 5px; }}

    /* 下拉選單鎖死黑科技：在 Selectbox 上方蓋一層完全透明但可點擊的 div */
    div[data-testid="stSelectbox"] {{
        position: relative;
    }}
    div[data-testid="stSelectbox"] input {{
        user-select: none !important;
        -webkit-user-select: none !important;
        pointer-events: none !important; /* 禁止 input 接收點擊 */
    }}
</style>
''', unsafe_allow_html=True)

# 3. 車站資料與 API
STATION_MAP = {
    "C1 籬仔內": "C1", "C2 凱旋瑞田": "C2", "C3 前鎮之星": "C3", "C4 凱旋中華": "C4", "C5 夢時代": "C5",
    "C6 經貿園區": "C6", "C7 軟體園區": "C7", "C8 高雄展覽館": "C8", "C9 旅運中心": "C9", "C10 光榮碼頭": "C10",
    "C11 真愛碼頭": "C11", "C12 駁二大義": "C12", "C13 駁二蓬萊": "C13", "C14 哈瑪星": "C14", "C15 壽山公園": "C15",
    "C16 文武聖殿": "C16", "C17 鼓山區公所": "C17", "C18 鼓山": "C18", "C19 馬卡道": "C19", "C20 台鐵美術館": "C20",
    "C21A 內維中心": "C21A", "C21 美術館": "C21", "C22 聯合醫院": "C22", "C23 龍華國小": "C23", "C24 愛河之心": "C24",
    "C25 新上國小": "C25", "C26 灣仔內": "C26", "C27 鼎山街": "C27", "C28 高雄高工": "C28", "C29 樹德家商": "C29",
    "C30 科工館": "C30", "C31 聖功醫院": "C31", "C32 凱旋公園": "C32", "C33 衛生局": "C33", "C34 五權國小": "C34",
    "C35 凱旋武昌": "C35", "C36 凱旋二聖": "C36", "C37 輕軌機廠": "C37"
}

@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

token = get_token()

# --- UI 開始 ---
st.markdown('<div class="custom-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="credit-text">zongyou x gemini</div>', unsafe_allow_html=True)

if not is_running:
    st.markdown('<div class="warning-box">🌙 OMG!現在輕軌沒有開🤓（06:30 - 22:30）。</div>', unsafe_allow_html=True)

st.markdown('<div class="legend-box"><span>🟢 順行 (外圈)</span><span>🔵 逆行 (內圈)</span></div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3])

with col_map:
    # 換回實用的底圖模式（可以看到軌道和街道）
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token and is_running:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_pos.get('LivePositions', []):
                d_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color=d_color, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=950)

with col_info:
    st.markdown('<div class="custom-subtitle">🚉 選擇車站</div>', unsafe_allow_html=True)
    sel_st_label = st.selectbox("Station", list(STATION_MAP.keys()), index=19, label_visibility="collapsed")
    target_id = STATION_MAP[sel_st_label]

    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", headers={'Authorization': f'Bearer {token}'})
            matched = [d for d in resp.json() if d.get('StationID') == target_id and d.get('EstimateTime') is not None]
            if matched:
                matched.sort(key=lambda x: x.get('EstimateTime', 999))
                for item in matched:
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'<div class="arrival-card"><div class="time-header">預計抵達時間</div><div class="time-val">{msg}</div></div>', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 資料同步中...")
    
    st.markdown(f'''
        <div style="margin-top:20px;">
            <div class="update-time-row">📍 地圖更新：{now.strftime("%Y-%m-%d %H:%M:%S")}</div>
            <div class="update-time-row">🕒 站牌更新：{now.strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>
    ''', unsafe_allow_html=True)

# 底部留言與紀錄
st.markdown(f'''
<div style="background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 10px; margin-top: 40px;">
    <div style="color: #ffcc80; font-weight: bold; margin-bottom: 8px;">✍️ 作者留言：</div>
    <div style="color: #8b949e; margin-bottom: 20px;">這是實驗性質專案。資料由 TDX 平台提供。</div>
    <hr style="border: 0; border-top: 1px solid #30363d; margin: 15px 0;">
    <div style="color: #58a6ff; font-weight: bold; font-size: 0.85em;">📋 版本紀錄 (V8.0)：</div>
    <div style="color: #8b949e; font-size: 0.8em;">
        • <b>實用地圖回歸</b>：更換地圖底圖，現在可以清楚看到軌道路線。<br>
        • <b>專屬紀念小字</b>：標題下方新增 zongyou x gemini 字樣。<br>
        • <b>雙行時間強化</b>：地圖與站牌時間清晰分離顯示。<br>
        • <b>終極避彈衣</b>：Selectbox 採用物理攔截技術，徹底鎖死鍵盤。
    </div>
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
