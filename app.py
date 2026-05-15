# ==========================================
# 【第一章：搬入工具箱】(Library Imports)
# 寫程式就像做菜，我們需要先準備好工具與食材。
# ==========================================

import streamlit as st           # Streamlit 是這間餐廳的「裝潢師」，負責畫網頁 UI。
import requests                  # requests 是「跑腿小哥」，負責去政府伺服器拿資料 (API)。
import folium                    # folium 是「製圖師」，專門處理地圖座標與圖層。
from streamlit_folium import folium_static  # 這是「膠水」，把製作好的地圖黏到網頁上。
import base64                    # 這是「翻譯官」，把字體檔案轉成網頁看得懂的文字編碼。
import os                        # 這是「檔案管理員」，用來檢查電腦裡有沒有那個字體檔。
import time                      # 這是「計時器」，控制程式要停多久才刷新。
import datetime                  # 這是「日曆」，記錄現在幾點幾分。
import pytz                      # 這是「時區專家」，確保時間是「台北時間」而不是國際標準時。
import math                      # 這是「數學老師」，用來算複雜的球面距離公式。
from streamlit_js_eval import get_geolocation # 這是「導航員」，透過瀏覽器向使用者要 GPS 權限。

# ==========================================
# 【第二章：網頁門面與風格】(UI & Styling)
# ==========================================

# st.set_page_config 是網頁的初始設定。
# layout="wide" 讓畫面左右拉滿，initial_sidebar_state="collapsed" 預設收起側邊欄，讓畫面乾淨。
st.set_page_config(page_title="高雄輕軌即時資訊", layout="wide", initial_sidebar_state="collapsed")

font_path = "ZONGYOOOOOOU1.otf"  # 這裡定義你的手寫字體檔案名稱
hand_base64 = ""                # 先準備一個空的盒子來放轉碼後的字體

# --- 字體處理邏輯 ---
# 為了讓每個人看到網頁都有手寫體，我們把字體檔案轉成 Base64 字串，直接「塞進」CSS 網頁樣式裡。
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        # 讀取二進位檔案並轉為 Base64 字串
        hand_base64 = base64.b64encode(f.read()).decode()

# --- CSS 魔法區 ---
# 這裡寫的是 CSS 語法，用來決定網頁的顏色、字體大小、發光效果。
style_html = f"""
<style>
    /* 從 Google 伺服器抓取免費的圓體字作為後備方案 */
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    
    /* 這裡定義我們自己的手寫體家族，名字叫 'MyHand' */
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{hand_base64}) format('opentype');
    }}

    /* 設定全網頁預設字體 */
    html, body, [class*="st-"], div, span, p {{
        font-family: 'Zen Maru Gothic', sans-serif;
    }}

    /* 當我們標註 class="hand-font" 時，強制使用手寫體 */
    .hand-font {{
        font-family: 'MyHand' !important;
    }}

    /* 深色模式外觀設定 */
    .stApp {{ background-color: #0e1117; color: white; }}
    
    /* 霓虹燈效果：這就是讓數字亮起來的祕訣 (text-shadow) */
    .time-val {{
        font-family: 'MyHand' !important;
        font-size: 48px;
        line-height: 1;
    }}
    .time-cw {{ color: #51cf66; text-shadow: 0 0 15px rgba(81,207,102,0.7); }} /* 綠光 */
    .time-ccw {{ color: #339af0; text-shadow: 0 0 15px rgba(51,154,240,0.7); }} /* 藍光 */
</style>
"""
st.markdown(style_html, unsafe_allow_html=True) # 將 CSS 注入 Streamlit

# ==========================================
# 【第三章：資料庫與數學核心】(Data & Math)
# ==========================================

# 用 Python 的「字典 (Dictionary)」存儲輕軌站點名與對應的經緯度。
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

# --- API 通行證邏輯 ---
# 政府的 TDX API 就像一扇上鎖的門，你需要先用 ID 和 Secret 換取「短期通行證 (Token)」。
def get_token():
    try:
        # 從 Streamlit Secrets 讀取你的密碼，不要直接寫在程式碼中 (安全考量)
        cid = st.secrets["TD_ID_NEW"]
        csk = st.secrets["TD_SECRET_NEW"]
        auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
        
        # POST 請求：發送身分證明給政府伺服器
        r = requests.post(auth_url, data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}, timeout=5)
        return r.json().get('access_token')
    except: 
        return None # 如果網路斷了或帳密錯了，回傳 None (代表失敗)

# --- 球面距離運算 ---
# 因為地球是圓的，兩點座標不能直接用勾股定理算，要用 Haversine 公式。
# 公式：$$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos\phi_1\cos\phi_2\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
def haversine(c1, c2):
    R = 6371.0 # 地球半徑 (公里)
    # 將角度轉為弧度
    la1, lo1, la2, lo2 = map(math.radians, [c1[0], c1[1], c2[0], c2[1]])
    dla = la2 - la1
    dlo = lo2 - lo1
    a = math.sin(dla/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlo/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ==========================================
# 【第四章：主程式運行邏輯】(Main Logic)
# ==========================================

# 1. 定位：跟瀏覽器要經緯度。如果拿不到，預設停在「馬卡道站」。
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc and user_loc.get('coords') else [22.6565, 120.2838]

# 2. 獲取 API 授權
token = get_token()

# 3. 畫面標題
st.markdown('<div class="header-title hand-font">高雄輕軌即時資訊</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-author hand-font">Zongyou X Gemini</div>', unsafe_allow_html=True)

# 4. 左右分欄 (電腦版並排，手機版會自動上下排疊)
col_left, col_right = st.columns([7, 3.5])

# --- 左側：地圖繪製 ---
with col_left:
    m = folium.Map(location=u_pos, zoom_start=15) # 創建地圖中心點
    # 標示使用者的位置 (紅色圓點)
    folium.CircleMarker(location=u_pos, radius=8, color='#fff', weight=2, fill=True, fill_color='#f51818', fill_opacity=1).add_to(m)
    
    # 這裡就是 API 串接步驟 2：獲取全線「列車位置」
    if token:
        try:
            pos_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            # 帶上 Token 向伺服器要資料
            pos_data = requests.get(pos_url, headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos_data if isinstance(pos_data, list) else pos_data.get('LivePositions', [])
            
            for t in trains:
                # 把每一台車畫在地圖上，順行綠色、逆行藍色
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']],
                    icon=folium.Icon(color='green' if t.get('Direction', 0)==0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass # 如果這部分壞掉，地圖依然可以顯示，只是沒火車
    folium_static(m, height=580, width=None)

# --- 右側：看板資訊 ---
with col_right:
    # 這裡實作「自動定位最近車站」
    st_names = list(LRT_STATIONS.keys())
    # min() 搭配我們剛寫好的 haversine 公式，找出距離最短的那一站
    best_st = min(st_names, key=lambda n: haversine(u_pos, LRT_STATIONS[n]))
    
    st.markdown('<p style="color:#a5d6a7; font-weight:bold;">📍 選擇站點(已自動定位)</p>', unsafe_allow_html=True)
    # 讓使用者也可以手動下拉選擇
    sel_st = st.selectbox("選擇站點", st_names, index=st_names.index(best_st), label_visibility="collapsed")
    st.markdown(f'<div class="loc-display">GPS 座標：{u_pos[0]:.6f}, {u_pos[1]:.6f}</div>', unsafe_allow_html=True)
    
    tid = sel_st.split()[0] # 抓出 ID (例如 C19)

    # 這裡就是 API 串接步驟 3：獲取該站點的「預估到站時間」
    if token:
        try:
            # 透過 $filter 語法，只跟伺服器拿特定車站的資料，節省流量
            b_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON"
            b_res = requests.get(b_url, headers={'Authorization': f'Bearer {token}'}).json()
            
            # 使用列表推導式 (List Comprehension) 分類順行與逆行
            cw_list = [i for i in b_res if "順行" in i.get('TripHeadSign', '')]
            ccw_list = [i for i in b_res if "逆行" in i.get('TripHeadSign', '')]

            # --- 渲染邏輯 ---
            # 我們將 API 拿到的分鐘數進行判斷，並套用 CSS 樣式顯示出來
            def show_arrival(data, label, color_class):
                if data:
                    item = min(data, key=lambda x: x.get('EstimateTime', 999))
                    val = int(item.get('EstimateTime', 0))
                    # 邏輯判斷：如果小於 1 分鐘，顯示「進站中」
                    txt = "即將進站" if val <= 1 else val
                    unit = "" if val <= 1 else "分鐘"
                    prefix = "約" if val > 1 else ""
                    st.markdown(f'''<div class="arrival-card">
                        <div class="dir-label">{label}</div>
                        <div class="time-container">
                            <span class="hand-font time-hand-label">{prefix}</span>
                            <span class="time-val {color_class}">{txt}</span>
                            <span class="hand-font time-hand-label">{unit}</span>
                        </div>
                    </div>''', unsafe_allow_html=True)

            show_arrival(cw_list, "● 順行方向", "time-cw")
            show_arrival(ccw_list, "● 逆行方向", "time-ccw")
        except: st.error("API 通訊中斷")

# ==========================================
# 【第五章：系統循環】(Automation)
# ==========================================

# 讓程式暫停 30 秒，這叫「冷卻時間」。
# 30 秒後執行 st.rerun()，整份程式碼會從第一行重新執行。
# 這樣 API 就會重新抓取，地圖上的小火車也會動，實現「即時監控」。
time.sleep(30)
st.rerun()
