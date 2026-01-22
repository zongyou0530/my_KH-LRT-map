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

# 1. 頁面基本配置
st.set_page_config(page_title="高雄輕軌監測系統", layout="wide", initial_sidebar_state="collapsed")

# --- A. 視覺樣式 (改用普通字串避免 f-string 大括號衝突) ---
style_css = """
<style>
    .stApp { background-color: #0e1117; color: white; }
    header { visibility: hidden; }
    .header-title { font-family: sans-serif; font-size: 42px !important; color: #a5d6a7; text-align: center; line-height: 1.1; font-weight: bold; }
    .sub-author { font-size: 22px !important; color: #888888; text-align: center; margin-bottom: 20px; }
    .legend-container { background-color: #1a1d23; border: 1px solid #30363d; border-radius: 20px; padding: 5px 15px; text-align: center; margin: 0 auto 15px auto; width: fit-content; font-size: 14px; }
    
    /* 紅點雷達樣式 */
    .radar-container { position: relative; width: 40px; height: 40px; display: flex; justify-content: center; align-items: center; }
    .radar-dot { width: 14px; height: 14px; background: #ff5252; border: 2px solid white; border-radius: 50%; z-index: 9999; }
    .radar-pulse { position: absolute; width: 14px; height: 14px; background: rgba(255, 82, 82, 0.5); border-radius: 50%; animation: pulse-ani 2s infinite; }
    @keyframes pulse-ani { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(5); opacity: 0; } }

    .board-container { background-color: #1a1d23; border: 1px solid #30363d; border-radius: 12px; overflow: hidden; margin-bottom: 10px; }
    .board-header { background-color: #252930; color: #ffd54f; font-size: 14px; font-weight: bold; padding: 6px 12px; }
    .board-content { padding: 10px; text-align: center; border-bottom: 1px solid #30363d; }
    .time-red { font-size: 32px; color: #ff5252 !important; font-weight: bold; }
    .time-yellow { font-size: 32px; color: #ffd54f !important; font-weight: bold; }
    .status-text { color: #718096; font-size: 12px; }
    .label-round { color: #81c784; font-size: 14px; }
</style>
"""
st.markdown(style_css, unsafe_allow_html=True)

# --- B. 核心數據 (全車站) ---
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

# 獲取定位
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc and user_loc.get('coords') else None
token = get_token()

# 標題 (使用換行標記)
st.markdown('<div class="header-title">高雄輕軌<br>即時位置地圖</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-author">Zongyou X Gemini</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🟢 順行 | 🔵 逆行 | 🔴 目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3.5])

with col_map:
    # 預設位置設在美術館站中心
    m = folium.Map(location=u_pos if u_pos else [22.6593, 120.2868], zoom_start=15)
    
    # 1. 顯示輕軌車輛 (先畫車，紅點才會在上面)
    if token:
        try:
            pos_data = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos_data if isinstance(pos_data, list) else pos_data.get('LivePositions', [])
            for t in trains:
                dir_val = t.get('Direction', 0)
                t_color = 'green' if dir_val == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], icon=folium.Icon(color=t_color, icon='train', prefix='fa')).add_to(m)
        except: pass

    # 2. 顯示紅點定位 (最後畫，確保置頂)
    if u_pos:
        folium.Marker(
            location=u_pos,
            icon=folium.DivIcon(
                icon_size=(40,40), icon_anchor=(20,20),
                html='<div class="radar-container"><div class="radar-pulse"></div><div class="radar-dot"></div></div>'
            )
        ).add_to(m)
        
    folium_static(m, height=480, width=800)

with col_info:
    st_names = list(LRT_STATIONS.keys())
    best_idx = 0
    if u_pos:
        best_st = min(st_names, key=lambda n: math.sqrt((u_pos[0]-LRT_STATIONS[n][0])**2 + (u_pos[1]-LRT_STATIONS[n][1])**2))
        best_idx = st_names.index(best_st)

    st.markdown('<div class="label-round">🚉 車站選擇 (自動定位)</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("", st_names, index=best_idx, label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    # 看板
    board_html = '<div class="board-container"><div class="board-header">📅 即將進站時刻</div>'
    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", headers={'Authorization': f'Bearer {token}'}).json()
            if b_res and len(b_res) > 0:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    t_class, msg = ("time-red", "即時進站") if est <= 1 else ("time-yellow", f"約 {est} 分鐘")
                    board_html += f'<div class="board-content"><div class="{t_class}">{msg}</div></div>'
            else:
                board_html += '<div class="board-content"><div style="color:#718096;">目前無班次資訊</div></div>'
        except: pass
    board_html += '</div>'
    st.markdown(board_html, unsafe_allow_html=True)

    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div class="status-text">🕒 最後更新：{now.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)
    if u_pos:
        st.markdown(f'<div class="status-text">🛰️ 目前座標：{u_pos[0]:.4f}, {u_pos[1]:.4f}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-text" style="color:#ff5252;">⚠️ 未取得 GPS 定位</div>', unsafe_allow_html=True)

# --- D. 底部留言板 ---
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
col_msg, col_log = st.columns([1, 1])
with col_msg:
    st.markdown('<div class="board-container"><div class="board-header">✍️ 作者留言</div><div style="padding:15px; font-size:18px;">資料由 TDX 提供，拜託大家不要一直開著，我點數會不夠。</div></div>', unsafe_allow_html=True)
with col_log:
    st.markdown('<div class="board-container"><div class="board-header">📦 系統更新紀錄 (v1.2.8)</div><div style="padding:15px; color:#cbd5e0; font-size:11px;">• 穩定性回歸：修復 v1.2.7 CSS 衝突導致的黑屏問題。<br>• 標題校正：實現換行與作者灰色顯示。<br>• 渲染順序：確保紅點最後繪製以維持置頂。</div></div>', unsafe_allow_html=True)

time.sleep(30)
st.rerun()
