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

# --- 時間與營運邏輯 ---
tz = pytz.timezone('Asia/Taipei')
now = datetime.datetime.now(tz)
# 營運時間 06:30 - 22:30
is_running = (now.hour > 6 or (now.hour == 6 and now.minute >= 30)) and (now.hour < 22 or (now.hour == 22 and now.minute <= 30))

# --- 字體與 CSS 樣式 ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode()
        font_css = f'''
        @font-face {{ font-family: 'ZongYouFont'; src: url(data:font/otf;base64,{font_base64}) format('opentype'); }}
        .zong-font {{ font-family: 'ZongYouFont' !important; }}
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 48px; color: #a5d6a7; text-align: center; margin-bottom: 8px; white-space: nowrap; }}
        .credit-text {{ font-family: 'ZongYouFont' !important; font-size: 16px; color: #888; text-align: center; margin-bottom: 20px; letter-spacing: 2px; }}
        .st-label-zong {{ font-family: 'ZongYouFont' !important; font-size: 26px; color: #81c784; margin-bottom: 10px; display: flex; align-items: center; }}
        '''
    except: pass

st.markdown(f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kiwi+Maru:wght@400;500&display=swap');
    {font_css}
    html, body, [data-testid="stAppViewContainer"] {{ font-family: 'Kiwi Maru', serif; background-color: #0e1117; }}
    
    /* 纖薄卡片 */
    .paper-card {{ 
        background-color: #1a1d23; border: 1px solid #2d333b; border-left: 5px solid #4caf50;
        border-radius: 8px; padding: 8px 15px; margin-bottom: 8px;
    }}
    .green-tag-box {{
        background-color: #2e7d32; color: white !important; font-size: 15px; 
        padding: 2px 10px; border-radius: 4px; display: inline-block; margin-bottom: 4px; font-family: 'ZongYouFont' !important;
    }}
    .arrival-text {{ font-family: 'ZongYouFont' !important; font-size: 32px !important; line-height: 1.1; }}
    .urgent-red {{ color: #ff5252 !important; }}
    .calm-grey {{ color: #78909c !important; }}

    /* 區塊樣式 */
    .info-box {{ background-color: #161b22; border-radius: 10px; padding: 15px; margin-top: 15px; border: 1px solid #30363d; }}
    .update-box {{ background-color: #0d1117; border-radius: 8px; padding: 12px; font-size: 0.85em; color: #8b949e; line-height: 1.6; border: 1px solid #21262d; }}
    
    @media (max-width: 768px) {{ .custom-title {{ font-size: 32px; }} }}
</style>
''', unsafe_allow_html=True)

# 3. 數據與 API (確保 NameError 不再發生)
STATION_MAP = {{ "C1 籬仔內": "C1", "C2 凱旋瑞田": "C2", "C3 前鎮之星": "C3", "C4 凱旋中華": "C4", "C5 夢時代": "C5", "C6 經貿園區": "C6", "C7 軟體園區": "C7", "C8 高雄展覽館": "C8", "C9 旅運中心": "C9", "C10 光榮碼頭": "C10", "C11 真愛碼頭": "C11", "C12 駁二大義": "C12", "C13 駁二蓬萊": "C13", "C14 哈瑪星": "C14", "C15 壽山公園": "C15", "C16 文武聖殿": "C16", "C17 鼓山區公所": "C17", "C18 鼓山": "C18", "C19 馬卡道": "C19", "C20 台鐵美術館": "C20", "C21A 內維中心": "C21A", "C21 美術館": "C21", "C22 聯合醫院": "C22", "C23 龍華國小": "C23", "C24 愛河之心": "C24", "C25 新上國小": "C25", "C26 灣仔內": "C26", "C27 鼎山街": "C27", "C28 高雄高工": "C28", "C29 樹德家商": "C29", "C30 科工館": "C30", "C31 聖功醫院": "C31", "C32 凱旋公園": "C32", "C33 衛生局": "C33", "C34 五權國小": "C34", "C35 凱旋武昌": "C35", "C36 凱旋二聖": "C36", "C37 輕軌機廠": "C37" }}

@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

token = get_token()

# --- 介面渲染 ---
st.markdown(f'<div class="custom-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)
st.markdown(f'<div class="credit-text">zongyou x gemini</div>', unsafe_allow_html=True)

# 營運狀態警告
if not is_running:
    st.warning("⚠️ 提醒：目前為非營運時段（營運時間：06:30 - 22:30）。資料將暫停更新或顯示舊資訊。")

# 地圖標示欄
st.success("📍 地圖標示：🟢 順行 (外圈) | 🔵 逆行 (內圈)")

col_map, col_info = st.columns([7, 3])

with col_map:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token and is_running:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_pos.get('LivePositions', []):
                d_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color=d_color, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=900)

with col_info:
    st.markdown('<div class="st-label-zong">🚉 輕軌車站即時站牌</div>', unsafe_allow_html=True)
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
                    color_class = "urgent-red" if est <= 2 else "calm-grey"
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    st.markdown(f'''<div class="paper-card"><div class="green-tag-box">輕軌預計抵達時間</div><div class="arrival-text {color_class}">{msg}</div></div>''', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 資料連線中")
    
    st.markdown(f'<div style="font-size: 0.8em; color: #666; margin-top:10px;">📍 地圖更新：{now.strftime("%H:%M:%S")}<br>🕒 站牌更新：{now.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)

# 底部留言區與更新內容
st.markdown('---')
st.markdown('<div class="info-box"><b>✍️ 作者留言：</b><br>這是一個實驗性性質專案。資料由 TDX 平台提供，僅供參考。</div>', unsafe_allow_html=True)

st.markdown(f'''
<div class="update-box">
    <b>📦 版本更新紀錄 (V15.0)：</b><br>
    • <b>視覺優化</b>：標題行距調整，並強制單行顯示。<br>
    • <b>功能回歸</b>：恢復非營運警告、地圖標示圖例與留言板。<br>
    • <b>動態預警</b>：不到 2 分鐘自動轉為亮紅色字體，超過則為深灰色。<br>
    • <b>介面更名</b>：更換側邊欄標題為「輕軌車站即時站牌」。
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
