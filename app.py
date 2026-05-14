import streamlit as st           # Streamlit 是網頁框架，用來快速建立監測儀表板
import requests                  # requests 是 API 串接的核心，負責向政府伺服器要資料
import folium                    # folium 是地圖工具，負責繪製地理資訊圖層
from streamlit_folium import folium_static  # 將繪製好的地圖嵌入到網頁中的橋樑
import base64                    # 用來把字體檔編碼成網頁能讀取的格式
import os                        # 用來檢查字體檔案路徑
import time                      # 負責頁面計時與延遲（自動更新用）
import datetime                  # 處理日期與時間格式
import pytz                      # 處理時區（將時間校正為台北時間）
import math                      # 提供數學函數，用來計算經緯度距離
from streamlit_js_eval import get_geolocation  # 呼叫瀏覽器的 JavaScript 來獲取使用者的 GPS 座標

# ==========================================
# 1. 頁面基礎配置
# ==========================================
# 設定網頁標題、佈局為寬版，並預設隱藏側邊欄
st.set_page_config(page_title="高雄輕軌即時資訊", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. 字體處理與 CSS 樣式 (關鍵：手寫體與發光特效)
# ==========================================
font_path = "ZONGYOOOOOOU1.otf"  # 你的手寫體檔案路徑
hand_base64 = "" 

# 將字體檔轉為 Base64 字串，以便直接嵌入 CSS 中，不需要使用者端安裝字體
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

# 定義網頁的所有視覺樣式
style_html = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    
    /* 註冊手寫體命名為 'MyHand' */
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{hand_base64}) format('opentype');
    }}

    /* 全域文字預設使用圓體 */
    html, body, [class*="st-"], div, span, p {{
        font-family: 'Zen Maru Gothic', sans-serif;
    }}

    /* 指定手寫體類別 */
    .hand-font {{
        font-family: 'MyHand' !important;
    }}

    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}

    /* 容器與卡片樣式 */
    .info-container {{ 
        background-color: #161b22; 
        border: 1px solid #30363d; 
        border-radius: 15px; 
        padding: 20px;
        margin-bottom: 15px;
    }}

    .arrival-card {{ 
        background: #1c2128; 
        border: 1px solid #30363d; 
        border-radius: 12px; 
        padding: 15px; 
        margin-bottom: 15px; 
    }}

    /* 文字樣式設定 */
    .header-title {{ color: #a5d6a7; text-align: center; font-size: 42px; margin-top: 10px; }}
    .sub-author {{ font-size: 18px; color: #888; text-align: center; margin-bottom: 20px; }}
    
    .dir-label {{ font-size: 14px; color: #8b949e; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }}
    .time-container {{ display: flex; align-items: center; gap: 10px; }}
    
    /* 看板中「約」與「分鐘」的手寫體大小 */
    .time-hand-label {{ 
        font-size: 26px; 
        color: #eee;
    }}

    /* 時間數字：手寫體 + 霓虹發光 */
    .time-val {{
        font-family: 'MyHand' !important;
        font-size: 48px;
        line-height: 1;
        margin: 0 5px;
    }}
    .time-cw {{ color: #51cf66; text-shadow: 0 0 15px rgba(81,207,102,0.7); }} 
    .time-ccw {{ color: #339af0; text-shadow: 0 0 15px rgba(51,154,240,0.7); }}

    /* 座標顯示專用樣式 */
    .loc-display {{
        font-size: 13px;
        color: #666;
        margin-top: -10px;
        margin-bottom: 15px;
        padding-left: 5px;
    }}
</style>
"""
st.markdown(style_html, unsafe_allow_html=True)

# ==========================================
# 3. 核心運算：座標、距離與 API Token
# ==========================================

# 全線 37 個站點的座標資料
LRT_STATIONS = {
    "C1 籬仔內": [22.6015, 120.3204], "C2 凱旋瑞田": [22.5969, 120.3201], "C3 前鎮之星": [22.5935, 120.3159],
    "C4 凱旋中華": [22.5947, 120.3094], "C5 夢時代": [22.5950, 120.3040], "C6 經貿園區": [22.5985, 120.3023],
    "C7 軟體園區": [22.6041, 120.3005], "C8 高雄展覽館": [22.6105, 120.2989], "C9 旅運中心": [22.6135, 120.2952],
    "C10 光榮碼頭": [22.6186, 120.2931], "C11 真愛碼頭": [22.6217, 120.2895], "C12 駁二大義": [22.6202, 120.2858],
    "C13 駁二蓬萊": [22.6203, 120.2783], "C14 哈瑪星": [22.6218, 120.2721], "C15 壽山公園": [22.6264, 120.2750],
    "C16 文武聖殿": [22.6318, 120.2780], "C17 鼓山區公所": [22.6380, 120.2785], "C18 鼓山": [22.6436, 120.2798],
    "C19 馬卡道": [22.6508, 120.2825], "C20 臺鐵美術館": [22.6565, 120.2838], "C21 美術館": [22.6593, 120.2868],
    "C22 聯合醫院": [22.6652, 120.2891], "C23 龍華國小": [22.6628, 120.2955], "C24 愛河之心": [22.6586, 120.3032],
    "C25 新上國小": [22.6581, 120.3115], "C26 灣仔內": [22.6548, 120.3193], "C27 鼎山街": [22.6515, 120.3262],
    "C28 高雄高工": [22.6480, 120.3323], "C29 樹德家商": [22.6435, 120.3341], "C30 科工館": [22.6385, 120.3355],
    "C31 聖功醫院": [22.6324, 120.3348], "C32 凱旋公園": [22.6288, 120.3322], "C33 衛生局": [22.6210, 120.3305],
    "C34 五權國小": [22.6148, 120.3294], "C35 凱旋武昌": [22.6095, 120.3283], "C36 凱旋二聖": [22.6045, 120.3265],
    "C37 輕軌機廠": [22.6025, 120.3235]
}

# API 串接步驟 1：取得通行令牌 (Token)
def get_token():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
        r = requests.post(auth_url, data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}, timeout=5)
        return r.json().get('access_token')
    except: return None

# 距離運算邏輯
def haversine(c1, c2):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, [c1[0], c1[1], c2[0], c2[1]])
    dla, dlo = la2 - la1, lo2 - lo1
    a = math.sin(dla/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlo/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ==========================================
# 4. 畫面渲染邏輯 (UI Logic)
# ==========================================

# 抓取瀏覽器 GPS 座標
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc and user_loc.get('coords') else [22.6508, 120.2825]

# 初始化 API 通行證
token = get_token()

# 標題與作者顯示
st.markdown('<div class="header-title hand-font">高雄輕軌即時監測</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-author hand-font">Zongyou X Gemini</div>', unsafe_allow_html=True)

# 佈局分欄
col_left, col_right = st.columns([7, 3.5])

# --- 左側：地圖與列車即時位置 ---
with col_left:
    m = folium.Map(location=u_pos, zoom_start=15)
    folium.CircleMarker(location=u_pos, radius=8, color='#fff', weight=2, fill=True, fill_color='#ff5252', fill_opacity=1).add_to(m)
    
    # API 串接步驟 2：獲取全線列車座標並在地圖標註
    if token:
        try:
            pos_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            pos_data = requests.get(pos_url, headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos_data if isinstance(pos_data, list) else pos_data.get('LivePositions', [])
            for t in trains:
                d_val = t.get('Direction', 0)
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']],
                    icon=folium.Icon(color='green' if d_val==0 else 'blue', icon='train', prefix='fa'),
                    popup=f"{'順行' if d_val==0 else '逆行'}"
                ).add_to(m)
        except: pass
    folium_static(m, height=580, width=None)

# --- 右側：到站看板與座標顯示 ---
with col_right:
    # 站點自動選取邏輯
    st_names = list(LRT_STATIONS.keys())
    best_st = min(st_names, key=lambda n: haversine(u_pos, LRT_STATIONS[n]))
    
    st.markdown('<p style="color:#a5d6a7; font-weight:bold; margin-bottom:5px;">📍 選擇站點 (已自動定位)</p>', unsafe_allow_html=True)
    sel_st = st.selectbox(" ", st_names, index=st_names.index(best_st), label_visibility="collapsed")
    
    # 【補回功能】讀取座標顯示
    st.markdown(f'<div class="loc-display">讀取座標：{u_pos[0]:.6f}, {u_pos[1]:.6f}</div>', unsafe_allow_html=True)
    
    tid = sel_st.split()[0]

    # 即時看板容器
    st.markdown('<div class="info-container">', unsafe_allow_html=True)
    st.markdown('<p style="color:#ffd54f; font-weight:bold; font-size:16px; margin-bottom:15px;">📅 即時到站看板</p>', unsafe_allow_html=True)
    
    # API 串接步驟 3：獲取特定車站的預估到站時間
    if token:
        try:
            b_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON"
            b_res = requests.get(b_url, headers={'Authorization': f'Bearer {token}'}).json()
            
            cw_list = [i for i in b_res if "順行" in i.get('TripHeadSign', '')]
            ccw_list = [i for i in b_res if "逆行" in i.get('TripHeadSign', '')]

            # 順行顯示
            if cw_list:
                cw = min(cw_list, key=lambda x: x.get('EstimateTime', 999))
                val = int(cw.get('EstimateTime', 0))
                display_time = "進站中" if val <= 1 else val
                unit = "" if val <= 1 else "分鐘"
                st.markdown(f'''<div class="arrival-card">
                    <div class="dir-label"><span style="color:#51cf66">●</span> 順行方向</div>
                    <div class="time-container">
                        <span class="hand-font time-hand-label">{"約" if val > 1 else ""}</span>
                        <span class="time-val time-cw">{display_time}</span>
                        <span class="hand-font time-hand-label">{unit}</span>
                    </div>
                </div>''', unsafe_allow_html=True)

            # 逆行顯示
            if ccw_list:
                ccw = min(ccw_list, key=lambda x: x.get('EstimateTime', 999))
                val = int(ccw.get('EstimateTime', 0))
                display_time = "進站中" if val <= 1 else val
                unit = "" if val <= 1 else "分鐘"
                st.markdown(f'''<div class="arrival-card">
                    <div class="dir-label"><span style="color:#339af0">●</span> 逆行方向</div>
                    <div class="time-container">
                        <span class="hand-font time-hand-label">{"約" if val > 1 else ""}</span>
                        <span class="time-val time-ccw">{display_time}</span>
                        <span class="hand-font time-hand-label">{unit}</span>
                    </div>
                </div>''', unsafe_allow_html=True)
        except: st.error("API 獲取失敗")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 顯示更新時間
    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div style="font-size:12px; color:#555; text-align:right;">🕒 更新時間：{now.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)

# ==========================================
# 5. 作者留言與版本紀錄
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)

# 作者寄語 (統一使用卡片與手寫體)
st.markdown(f"""
<div class="info-container hand-font">
    <p style="color:#ffd54f; font-weight:bold; margin-bottom:8px;">💡 作者留言：</p>
    <p style="font-size:16px; color:#ccd6f6;">不要一直開著頁面，TDX API 的用量有限。<br>😁😁</p>
</div>
""", unsafe_allow_html=True)

# 版本紀錄
st.markdown("""
<div class="info-container">
    <p style="color:#a5d6a7; font-weight:bold; margin-bottom:8px;">📦 版本紀錄 v1.7.3（sum:gemini)</p>
    <p style="font-size:13px; color:#8b949e; line-height:1.6;">
        • <b>完全修復</b>：補回遺失的座標讀取顯示功能。<br>
        • <b>字體優化</b>：確保「約」與「分鐘」完美呈現手寫體。<br>
        • <b>視覺統一</b>：作者留言區與看板樣式整合，版面更整潔。
    </p>
</div>
""", unsafe_allow_html=True)

# 自動更新 (每 30 秒)
time.sleep(30)
st.rerun()
