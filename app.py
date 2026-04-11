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

# 1. 頁面配置 (這行必須在最前面)
st.set_page_config(page_title="高雄輕軌監測系統", layout="wide", initial_sidebar_state="collapsed")

# --- 🔐 密碼保護區 ---
def password_entered():
    """檢查輸入的密碼是否正確"""
    if st.session_state["pwd"] == "5533":
        st.session_state["password_correct"] = True
        del st.session_state["pwd"]  # 刪除暫存密碼避免洩漏
    else:
        st.session_state["password_correct"] = False

def check_password():
    """驗證密碼，若正確則回傳 True"""
    if st.session_state.get("password_correct", False):
        return True
    
    # 顯示密碼輸入框
    st.markdown("<h2 style='text-align:center;'>🔒 私人情報屋</h2>", unsafe_allow_html=True)
    st.text_input("請輸入密碼以進入系統", type="password", on_change=password_entered, key="pwd")
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 密碼錯誤，請再試一次。")
    
    return False

# 如果密碼沒過，就停止執行後面的程式碼
if not check_password():
    st.stop()

# --- 🔓 通過檢查後顯示的內容 ---

# --- A. 字體與視覺樣式 ---
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

style_html = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');

    @font-face {
        font-family: 'MyHand';
        src: url(data:font/otf;base64,""" + hand_base64 + """) format('opentype');
    }
    
    html, body, [class*="st-"], div, span, p {
        font-family: 'Zen Maru Gothic', sans-serif !important;
    }

    .hand-font {
        font-family: 'MyHand', sans-serif !important;
    }

    .stApp { background-color: #0e1117; color: white; }
    header { visibility: hidden; }
    
    .header-title { font-size: 38px; color: #a5d6a7; text-align: center; line-height: 1.1; margin-top: 5px; }
    .sub-author { font-size: 18px; color: #888888; text-align: center; margin-bottom: 5px; }
    .legend-bar { background-color: #1a1d23; border: 1px solid #30363d; border-radius: 20px; padding: 4px 12px; text-align: center; margin: 0 auto 10px auto; width: fit-content; font-size: 13px; }
    
    .arrival-card {
        background: rgba(45, 51, 59, 0.7);
        border: 1px solid #444c56;
        border-radius: 10px;
        padding: 8px 12px;
        margin: 6px 0;
        text-align: center;
    }
    
    .time-val { font-size: 26px; font-weight: bold; margin: 0; }
    .time-red { color: #ff6b6b; }
    .time-yellow { color: #ffd54f; }
    .status-info { color: #8b949e; font-size: 12px; margin-top: 3px; }

    .info-container { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 12px; margin-bottom: 10px; }
    .info-header { color: #ffd54f; font-size: 14px; font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #30363d; padding-bottom: 4px; }
</style>
"""
st.markdown(style_html, unsafe_allow_html=True)

# --- B. 核心資料庫 ---
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

# 定位獲取
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc and user_loc.get('coords') else [22.6508, 120.2825]
token = get_token()

# 標題與說明
st.markdown('<div class="header-title hand-font">高雄輕軌<br>即時位置地圖</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-author hand-font">Zongyou X Gemini</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-bar">🟢 順行 | 🔵 逆行 | 🔴 目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3.5])

with col_map:
    m = folium.Map(location=u_pos, zoom_start=15)
    folium.CircleMarker(
        location=u_pos, radius=8, color='#ffffff', fill=True, fill_color='#ff5252', fill_opacity=0.9, popup='目前位置'
    ).add_to(m)
    
    if token:
        try:
            pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos if isinstance(pos, list) else pos.get('LivePositions', [])
            for t in trains:
                dir_val = t.get('Direction', 0)
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                    icon=folium.Icon(color='green' if dir_val==0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m, height=450, width=800)

with col_info:
    st_names = list(LRT_STATIONS.keys())
    best_st = min(st_names, key=lambda n: math.sqrt((u_pos[0]-LRT_STATIONS[n][0])**2 + (u_pos[1]-LRT_STATIONS[n][1])**2))
    
    st.markdown('<div style="color:#81c784; font-size:13px; margin-bottom:4px;">🚉 車站選擇</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("", st_names, index=st_names.index(best_st), label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    st.markdown('<div style="color:#ffd54f; font-size:14px; font-weight:bold; margin-top: 5px;">📅 即將進站時刻</div>', unsafe_allow_html=True)
    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", headers={'Authorization': f'Bearer {token}'}).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    t_class, msg = ("time-red", "即時進站") if est <= 1 else ("time-yellow", f"約 {est} 分鐘")
                    st.markdown(f'<div class="arrival-card"><div class="hand-font time-val {t_class}">{msg}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="arrival-card" style="font-size:14px; color:#8b949e;">目前無班次</div>', unsafe_allow_html=True)
        except: pass

    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div class="status-info">🕒 最後更新：{now.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="status-info">🛰️ 讀取座標：{u_pos[0]:.4f}, {u_pos[1]:.4f}</div>', unsafe_allow_html=True)

# --- D. 作者留言區 ---
st.markdown('<div style="height:5px;"></div>', unsafe_allow_html=True)
c_msg, c_log = st.columns(2)
with c_msg:
    st.markdown('<div class="info-container"><div class="info-header">✍️ 作者留言</div><div class="hand-font" style="font-size:17px;">資料由 TDX 提供，拜託大家不要一直開著，我點數會不夠。</div></div>', unsafe_allow_html=True)
with c_log:
    st.markdown('<div class="info-container"><div class="info-header">📦 系統更新紀錄 (v1.4.0)</div><div style="font-size:12px; color:#8b949e;">• 安全升級：新增密碼鎖功能。<br>• 介面微縮：時刻表卡片與座標顯示共存。</div></div>', unsafe_allow_html=True)

time.sleep(30)
st.rerun()
