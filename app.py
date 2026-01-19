import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import base64
import os
import time
import datetime
import pytz
import math
from streamlit_js_eval import get_geolocation

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體與視覺樣式 ---
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{hand_base64}) format('opentype');
    }}
    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}
    .block-container {{ padding-top: 5rem !important; }}
    .header-title {{ font-family: 'MyHand', sans-serif !important; font-size: 48px !important; color: #a5d6a7; text-align: center; line-height: 1.1; margin-bottom: 10px; }}
    .legend-container {{ font-family: 'Zen Maru Gothic', sans-serif !important; background-color: #1a1d23; border: 1px solid #30363d; border-radius: 15px; padding: 4px 12px; text-align: center; margin: 0 auto 15px auto; width: fit-content; font-size: 13px; color: #cccccc; }}
    .info-card {{ background-color: #1a1d23; border: 1px solid #30363d; border-radius: 10px; padding: 10px 15px; margin-bottom: 8px; }}
    .dir-label {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #ffd54f; font-size: 15px; font-weight: bold; margin: 10px 0 5px 0; border-left: 4px solid #ffd54f; padding-left: 8px; }}
    .label-round {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #81c784; font-size: 14px; margin-bottom: 2px; }}
    .content-hand {{ font-family: 'MyHand', sans-serif !important; font-size: 26px; }}
    .status-text {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #718096; font-size: 12px; margin-top: 4px; line-height: 1.5; }}
</style>
""", unsafe_allow_html=True)

# --- B. 核心全線車站清單 (確保選單完整) ---
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

# 輔助計算函數
def get_dist(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def get_token():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        r = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                         data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk})
        return r.json().get('access_token')
    except: return None

# --- C. 初始化位置與資料 ---
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc else None
token = get_token()

st.markdown('<div class="header-title">高雄輕軌<br>全線即時監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3.5])

with col_map:
    m = folium.Map(location=u_pos if u_pos else [22.6593, 120.2868], zoom_start=15)
    if u_pos:
        folium.CircleMarker(u_pos, radius=7, color='white', weight=2, fill=True, fill_color='red', fill_opacity=1).add_to(m)
    if token:
        try:
            pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                             headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos if isinstance(pos, list) else pos.get('LivePositions', [])
            for t in trains:
                c = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color=c, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=800)

with col_info:
    # 智慧自動選站：如果有座標，自動找出最近的站名
    st_names = list(LRT_STATIONS.keys())
    best_idx = 0
    if u_pos:
        best_st = min(st_names, key=lambda n: get_dist(u_pos, LRT_STATIONS[n]))
        best_idx = st_names.index(best_st)

    st.markdown('<div class="label-round">🚉 全線車站選擇 (已自動定位最近站)</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("", st_names, index=best_idx, label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    if token:
        try:
            b = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                            headers={'Authorization': f'Bearer {token}'}).json()
            if isinstance(b, list) and len(b) > 0:
                d0 = [i for i in b if i.get('Direction') == 0]
                d1 = [i for i in b if i.get('Direction') == 1]
                
                # 容錯模式：分不出來就全顯示
                fb = False
                if not d0 and not d1: 
                    d0 = b[:1]
                    fb = True

                def draw(data, title, is_fb=False):
                    st.markdown(f'<div class="dir-label">{"📅 即將進站" if is_fb else title}</div>', unsafe_allow_html=True)
                    if not data:
                        st.markdown('<div class="info-card"><div class="content-hand" style="font-size:16px; color:#718096;">暫無即時資訊</div></div>', unsafe_allow_html=True)
                    else:
                        for item in sorted(data, key=lambda x: x.get('EstimateTime', 999))[:1]:
                            est = int(item.get('EstimateTime', 0))
                            dest = item.get('DestinationStationName', {}).get('Zh_tw', '終點站')
                            msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                            st.markdown(f'''<div class="info-card"><div class="content-hand" style="color:{"#ff5252" if est <= 2 else "#ffffff"} !important;">{msg}</div>
                                        <div style="font-size:12px; color:#718096;">往 {dest}</div></div>''', unsafe_allow_html=True)
                if fb: draw(d0, "", True)
                else:
                    draw(d0, "🟢 順行方向")
                    draw(d1, "🔵 逆行方向")
        except: pass

    # --- 修正時間與座標顯示 ---
    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div class="status-text">🕒 最後更新：{now.strftime("%Y/%m/%d %H:%M:%S")}</div>', unsafe_allow_html=True)
    if u_pos:
        st.markdown(f'<div class="status-text">🛰️ 目前位置：{u_pos[0]:.4f}, {u_pos[1]:.4f}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-text">⚠️ 座標獲取失敗，請重新整理或授權 GPS</div>', unsafe_allow_html=True)

# 底部留言
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
col_l, col_r = st.columns([1, 1.2])
with col_l:
    st.markdown('<div class="info-card"><div class="label-round">✍️ 開發筆記</div><div class="content-hand" style="font-size: 18px;">成功解決非同步定位造成的選單缺失問題。</div></div>', unsafe_allow_html=True)
with col_r:
    st.markdown(f"""<div class="info-card"><div class="label-round">📦 技術進度</div><div class="status-text" style="color:#cbd5e0;">
    • <b>座標連動：</b>即時偵測使用者位置並鎖定最近車站。<br>
    • <b>全線解鎖：</b>C1-C37 車站選單完整呈現，不再遺漏。<br>
    • <b>標準時戳：</b>西元年月日顯示，符合專業監測標準。</div></div>""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
