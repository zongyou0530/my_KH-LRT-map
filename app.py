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
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 42px; color: #1a531b; margin-bottom: 10px; text-align: center; }}
        .custom-subtitle {{ font-family: 'ZongYouFont' !important; font-size: 26px; color: #2e7d32; }}
        .time-header {{ background-color: #2e7d32; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.9em; font-family: 'ZongYouFont' !important; }}
        .time-val {{ font-family: 'ZongYouFont' !important; font-size: 2em; color: #4D0000; margin-top: 5px; }}
        @media (max-width: 768px) {{ .custom-title {{ font-size: 28px; }} }}
        '''
    except: pass

# 2. 注入 CSS (含鎖死鍵盤邏輯)
st.markdown(f'''
<style>
    {font_css}
    html, body, [data-testid="stAppViewContainer"] {{ font-family: 'Kiwi Maru', serif; }}
    
    /* 區塊樣式 */
    .warning-box {{ background-color: #fffde7; border: 1px solid #fdd835; padding: 10px; border-radius: 8px; color: #827717; text-align: center; font-size: 0.85em; margin-bottom: 10px; }}
    .legend-box {{ background-color: #f1f8e9; border: 1px solid #c5e1a5; padding: 8px; border-radius: 8px; color: #33691e; font-size: 0.85em; margin-bottom: 15px; display: flex; justify-content: center; gap: 15px; }}
    .footer-box {{ background-color: #f5f5f5; border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin-top: 30px; font-size: 0.85em; }}
    .arrival-card {{ background-color: #ffffff; border-radius: 8px; padding: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 6px solid #2e7d32; }}

    /* 下拉選單鎖死鍵盤法：禁止 input 獲取焦點 */
    [data-testid="stSelectbox"] input {{
        readonly: readonly !important;
        pointer-events: none !important;
    }}
    [data-testid="stSelectbox"] div[role="button"] {{
        cursor: pointer !important;
    }}

    /* 地圖與內容間距修正 */
    .stFolium {{ margin-top: 0px !important; margin-bottom: 15px !important; z-index: 1; }}
</style>

<script>
    // 強制將所有的 selectbox input 設為 readonly，徹底防止手機彈出鍵盤
    const inputs = window.parent.document.querySelectorAll('input[aria-autocomplete="list"]');
    inputs.forEach(input => {{
        input.setAttribute('readonly', 'true');
        input.style.caretColor = 'transparent';
    }});
</script>
''', unsafe_allow_html=True)

# 3. 車站資料
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

# --- UI 開始 ---
st.markdown('<div class="custom-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)

# A. 營運提示 (僅非營運時顯示)
if not is_running:
    st.markdown('<div class="warning-box">⚠️ 提醒：目前為非營運時段（06:30 - 22:30）。</div>', unsafe_allow_html=True)

# B. 地圖標示 (置頂且簡潔)
st.markdown('<div class="legend-box"><span>📍 🟢 順行 (外圈)</span><span>🔵 逆行 (內圈)</span></div>', unsafe_allow_html=True)

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
    folium_static(m, height=450, width=950)

with col_info:
    st.markdown('<div class="custom-subtitle">🚉 選擇車站</div>', unsafe_allow_html=True)
    sel_st_label = st.selectbox("車站", list(STATION_MAP.keys()), index=19, label_visibility="collapsed")
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
                    st.markdown(f'<div class="arrival-card"><div class="time-header">預計抵達</div><div class="time-val">{msg}</div></div>', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 資料連線中")
    
    st.markdown(f'<p style="font-size:0.8em; color:#999;">🕒 更新：{now.strftime("%H:%M:%S")}</p>', unsafe_allow_html=True)

# D. 底部區塊：作者留言 + 更新摘要
st.markdown(f'''
<div class="footer-box">
    <div style="color: #e65100; font-weight: bold; margin-bottom: 10px;">✍️ 作者留言：</div>
    <div style="color: #666; margin-bottom: 20px;">這是一個實驗性質的輕軌站點監測系統。資料來源為 TDX 運輸資料流通服務，僅供參考。</div>
    <hr style="border: 0; border-top: 1px solid #ddd; margin: 10px 0;">
    <b>📋 版本紀錄 (V6.0)：</b><br>
    • <b>視覺優化</b>：縮小標題字體，解決地圖與說明重疊問題。<br>
    • <b>鍵盤鎖死</b>：強制 Selectbox 為 Readonly，防止手機彈出鍵盤。<br>
    • <b>版面重整</b>：留言區下移，地圖與站牌資訊對齊。
</div>
''', unsafe_allow_html=True)

if is_running:
    time.sleep(30)
    st.rerun()
