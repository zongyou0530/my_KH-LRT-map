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
st.set_page_config(page_title="高雄輕軌即時位置地圖", layout="wide", initial_sidebar_state="collapsed")

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
    
    /* 標題區樣式 */
    .header-title {{ font-family: 'MyHand', sans-serif !important; font-size: 48px !important; color: #a5d6a7; text-align: center; line-height: 1.0; margin-bottom: 0px; }}
    .sub-author {{ font-family: 'MyHand', sans-serif !important; font-size: 22px !important; color: #81c784; text-align: center; margin-bottom: 15px; opacity: 0.9; }}
    .legend-container {{ font-family: 'Zen Maru Gothic', sans-serif !important; background-color: #1a1d23; border: 1px solid #30363d; border-radius: 15px; padding: 4px 12px; text-align: center; margin: 0 auto 15px auto; width: fit-content; font-size: 13px; color: #cccccc; }}
    
    /* 進站卡片一體化設計 */
    .board-container {{
        background-color: #1a1d23;
        border: 2px solid #30363d;
        border-radius: 15px;
        padding: 0px;
        margin-bottom: 15px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }}
    .board-header {{
        background-color: #30363d;
        color: #ffd54f;
        font-family: 'Zen Maru Gothic', sans-serif;
        font-size: 16px;
        font-weight: bold;
        padding: 8px 15px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .board-content {{
        padding: 20px 15px;
        text-align: center;
        border-bottom: 1px solid #30363d;
    }}
    .board-content:last-child {{ border-bottom: none; }}
    
    /* 時間顏色控制 */
    .time-red {{ font-family: 'MyHand', sans-serif !important; font-size: 42px; color: #ff5252 !important; text-shadow: 0 0 10px rgba(255,82,82,0.3); }}
    .time-yellow {{ font-family: 'MyHand', sans-serif !important; font-size: 42px; color: #ffd54f !important; }}
    
    .label-round {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #81c784; font-size: 14px; margin-bottom: 8px; }}
    .status-text {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #718096; font-size: 12px; margin-top: 4px; line-height: 1.5; }}
</style>
""", unsafe_allow_html=True)

# --- B. 核心車站資料庫 (C1-C37) ---
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

def get_token():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        r = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                         data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk})
        return r.json().get('access_token')
    except: return None

# 初始化
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc else None
token = get_token()

# 標題區
st.markdown('<div class="header-title">高雄輕軌即時位置地圖</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-author">Zongyou X gemini</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🚄 即時車輛 | 🔴 目前位置</div>', unsafe_allow_html=True)

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
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color='green', icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=800)

with col_info:
    st_names = list(LRT_STATIONS.keys())
    best_idx = 0
    if u_pos:
        best_st = min(st_names, key=lambda n: math.sqrt((u_pos[0]-LRT_STATIONS[n][0])**2 + (u_pos[1]-LRT_STATIONS[n][1])**2))
        best_idx = st_names.index(best_st)

    st.markdown('<div class="label-round">🚉 車站選擇 (已自動定位)</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("", st_names, index=best_idx, label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    # --- 優化後的看板區域 ---
    board_html = '<div class="board-container"><div class="board-header">📅 即將進站時刻</div>'
    
    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                                headers={'Authorization': f'Bearer {token}'}).json()
            if b_res and len(b_res) > 0:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    if est <= 1:
                        time_class, msg = "time-red", "即時進站"
                    else:
                        time_class, msg = "time-yellow", f"約 {est} 分鐘"
                    
                    board_html += f'<div class="board-content"><div class="{time_class}">{msg}</div></div>'
            else:
                board_html += '<div class="board-content"><div style="font-family:MyHand; font-size:24px; color:#718096;">目前無班次資訊</div></div>'
        except:
            board_html += '<div class="board-content"><div style="font-family:MyHand; font-size:24px; color:#718096;">連線檢查中...</div></div>'
    
    board_html += '</div>'
    st.markdown(board_html, unsafe_allow_html=True)

    # 時間與座標
    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div class="status-text">🕒 最後更新時間：{now.strftime("%Y/%m/%d %H:%M:%S")}</div>', unsafe_allow_html=True)
    if u_pos:
        st.markdown(f'<div class="status-text">🛰️ 目前讀取座標：{u_pos[0]:.4f}, {u_pos[1]:.4f}</div>', unsafe_allow_html=True)

# --- D. 作者留言與日誌區 ---
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
col_msg, col_log = st.columns([1, 1.2])

with col_msg:
    original_msg = "資料由 TDX 提供，拜託大家不要一直開著 我點數會不夠" 
    st.markdown(f'''<div class="board-container" style="padding:15px; text-align:left;">
                <div class="label-round">✍️ 作者留言</div>
                <div style="font-family:MyHand; font-size: 20px;">{original_msg}</div>
                </div>''', unsafe_allow_html=True)

with col_log:
    st.markdown(f"""<div class="board-container" style="padding:15px; text-align:left;">
                <div class="label-round">📦 系統更新紀錄</div>
                <div class="status-text" style="color:#cbd5e0;">
                • <b>介面進化：</b>整合標籤與看板資訊，提升視覺統一感。<br>
                • <b>顯色系統：</b>即時進站紅色強調，一般班次黃色區分。<br>
                • <b>效能優化：</b>減少不必要的標記，提升移動端載入速度。</div>
                • <b>Summery&Assistance : gemini</b></div>
                </div>""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
