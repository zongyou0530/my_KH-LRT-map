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
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 55px; color: #81c784; margin-bottom: 10px; text-align: center; white-space: nowrap; overflow: hidden; }}
        .custom-subtitle {{ font-family: 'ZongYouFont' !important; font-size: 32px; color: #a5d6a7; }}
        .time-header {{ background-color: #2e7d32; color: #ffffff; padding: 2px 10px; border-radius: 4px; font-size: 1em; font-family: 'ZongYouFont' !important; }}
        .time-val {{ font-family: 'ZongYouFont' !important; font-size: 2.2em; color: #ffab91; margin-top: 5px; }}
        @media (max-width: 768px) {{ .custom-title {{ font-size: 8vw; }} }}
        '''
    except: pass

# 2. 注入 CSS (深色模式與鍵盤盾牌)
st.markdown(f'''
<style>
    {font_css}
    /* 全域深色背景 */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: #121212 !important;
        color: #e0e0e0 !important;
    }}
    html, body, p, div, span, label {{ font-family: 'Kiwi Maru', serif; color: #e0e0e0 !important; }}

    /* 頂部說明區塊 */
    .warning-box {{ background-color: #332b00; border: 1px solid #fdd835; padding: 10px; border-radius: 8px; color: #fff176 !important; text-align: center; margin-bottom: 10px; }}
    .legend-box {{ background-color: #1b2e1b; border: 1px solid #4caf50; padding: 8px; border-radius: 8px; font-size: 0.9em; margin-bottom: 15px; display: flex; justify-content: center; gap: 20px; }}
    
    /* 抵達時間卡片 */
    .arrival-card {{ background-color: #1e1e1e; border-radius: 12px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 12px; border-left: 8px solid #4caf50; }}
    
    /* 下拉選單鎖死鍵盤 (隱形盾牌法) */
    div[data-testid="stSelectbox"] > div {{
        position: relative;
    }}
    /* 在 input 上方蓋一個透明層，攔截 focus 事件 */
    div[data-testid="stSelectbox"] input {{
        pointer-events: none !important;
    }}

    /* 底部區塊 */
    .footer-box {{ background-color: #1a1a1a; border: 1px solid #333; padding: 20px; border-radius: 10px; margin-top: 40px; }}
    .update-time {{ font-size: 0.85em; color: #999 !important; margin: 4px 0; }}
    
    /* 地圖邊界修正 */
    .stFolium {{ border: 2px solid #333; border-radius: 10px; overflow: hidden; }}
</style>
''', unsafe_allow_html=True)

# 3. 資料與 API
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

# A. 提示與圖例
if not is_running:
    st.markdown('<div class="warning-box">🌙 目前為非營運時段（06:30 - 22:30）</div>', unsafe_allow_html=True)

st.markdown('<div class="legend-box"><span>🟢 順行 (外圈)</span><span>🔵 逆行 (內圈)</span></div>', unsafe_allow_html=True)

# B. 主區域
col_map, col_info = st.columns([7, 3])

with col_map:
    # 深色模式地圖建議使用 CartoDB dark_matter，但保留原始風格以免看不清站點
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13, tiles="cartodbpositron")
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
    sel_st_label = st.selectbox("車站選擇器", list(STATION_MAP.keys()), index=19, label_visibility="collapsed")
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
    
    # 更新時間兩行顯示
    st.markdown(f'''
        <div style="margin-top:20px;">
            <div class="update-time">📍 地圖更新：{now_str}</div>
            <div class="update-time">🕒 站牌更新：{now_str}</div>
        </div>
    ''', unsafe_allow_html=True)

# C. 底部區塊
st.markdown(f'''
<div class="footer-box">
    <div style="color: #ffcc80; font-weight: bold; margin-bottom: 8px;">✍️ 作者留言：</div>
    <div style="color: #bbb; margin-bottom: 20px;">這是一個專為高雄輕軌設計的監測系統。資料由 TDX 平台提供，僅供即時參考。</div>
    <hr style="border: 0; border-top: 1px solid #444; margin: 15px 0;">
    <div style="color: #81c784; font-weight: bold; margin-bottom: 5px;">📋 版本紀錄 (V7.0)：</div>
    <div style="color: #999; font-size: 0.9em;">
        • <b>全網深色模式</b>：質感黑金配色，保護雙眼。<br>
        • <b>標題單行縮放</b>：大標題確保在手機端不換行。<br>
        • <b>雙行時間顯示</b>：📍地圖與🕒站牌時間清晰分離。<br>
        • <b>鍵盤強效鎖死</b>：CSS 攔截機制，徹底解決手機彈出鍵盤困擾。
    </div>
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
