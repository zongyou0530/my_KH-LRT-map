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
st.set_page_config(page_title="高雄輕軌監測系統", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體與視覺精確分工 ---
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

# 這裡精確區分：手寫體 (.hand-text) 與 系統圓體 (body)
style_css = """
<style>
    @font-face {
        font-family: 'MyHand';
        src: url(data:font/otf;base64,""" + hand_base64 + """) format('opentype');
    }
    
    /* 預設全域使用 Google 圓體風格 (Sans-serif) */
    html, body, [class*="st-"] {
        font-family: "Segoe UI", Roboto, Helvetica, Arial, "Heiti TC", "Microsoft JhengHei", sans-serif !important;
    }

    /* 只有這四個地方要用手寫體 */
    .hand-title, .hand-author, .hand-big-num, .hand-msg {
        font-family: 'MyHand' !important;
    }

    .stApp { background-color: #0e1117; color: white; }
    header { visibility: hidden; }
    
    .hand-title { font-size: 42px; color: #a5d6a7; text-align: center; line-height: 1.1; margin-top: 10px; }
    .hand-author { font-size: 22px; color: #888888; text-align: center; margin-bottom: 20px; }
    .legend-container { background-color: #1a1d23; border: 1px solid #30363d; border-radius: 20px; padding: 5px 15px; text-align: center; margin: 0 auto 15px auto; width: fit-content; font-size: 14px; }
    
    /* 紅點雷達：強制最高層級 100000 */
    .current-pos-container { position: relative; width: 50px; height: 50px; display: flex; justify-content: center; align-items: center; z-index: 100000 !important; }
    .dot-core { width: 18px; height: 18px; background-color: #ff5252; border: 2px solid #ffffff; border-radius: 50%; box-shadow: 0 0 15px rgba(255, 82, 82, 0.9); z-index: 100001; }
    .pulse-ring { position: absolute; width: 18px; height: 18px; border: 4px solid #ff5252; border-radius: 50%; background-color: rgba(255, 82, 82, 0.3); animation: radar-pulse 2s infinite ease-out; z-index: 99999; }
    @keyframes radar-pulse { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(6); opacity: 0; } }

    .board-container { background-color: #1a1d23; border: 1px solid #30363d; border-radius: 12px; overflow: hidden; margin-bottom: 10px; }
    .board-header { background-color: #252930; color: #ffd54f; font-size: 14px; font-weight: bold; padding: 6px 12px; }
    .board-content { padding: 10px; text-align: center; border-bottom: 1px solid #30363d; }
    .hand-big-num { font-size: 32px; }
    .time-red { color: #ff5252 !important; }
    .time-yellow { color: #ffd54f !important; }
    .status-text { color: #718096; font-size: 12px; }
</style>
"""
st.markdown(style_css, unsafe_allow_html=True)

# --- B. 核心資料 ---
LRT_STATIONS = {
    "C1 籬仔內": [22.6015, 120.3204], "C19 馬卡道": [22.6508, 120.2825], "C20 臺鐵美術館": [22.6565, 120.2838], "C21 美術館": [22.6593, 120.2868]
} # ... (為節省空間，其餘車站邏輯在正式運行中請保留完整清單)

def get_token():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        r = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                         data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk})
        return r.json().get('access_token')
    except: return None

# 定位獲取與「保底機制」
user_loc = get_geolocation()
if user_loc and user_loc.get('coords'):
    u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']]
    loc_msg = "🛰️ 實時 GPS 定位中"
else:
    # ⚠️ 如果抓不到定位，強制顯示在馬卡道附近，解決你看不到紅點的問題
    u_pos = [22.6508, 120.2825]
    loc_msg = "📍 抓不到 GPS (顯示預設位置)"

token = get_token()

# 標題 (手寫體)
st.markdown('<div class="hand-title">高雄輕軌<br>即時位置地圖</div>', unsafe_allow_html=True)
st.markdown('<div class="hand-author">Zongyou X Gemini</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🟢 順行 | 🔵 逆行 | 🔴 目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3.5])

with col_map:
    m = folium.Map(location=u_pos, zoom_start=15)
    # 🔴 強制畫出紅點 (無論有沒有抓到 GPS)
    folium.Marker(
        location=u_pos,
        icon=folium.DivIcon(
            icon_size=(50,50), icon_anchor=(25,25),
            html='<div class="current-pos-container"><div class="pulse-ring"></div><div class="dot-core"></div></div>'
        )
    ).add_to(m)
    
    if token:
        try:
            pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos if isinstance(pos, list) else pos.get('LivePositions', [])
            for t in trains:
                dir_val = t.get('Direction', 0)
                # 🟢 藍綠雙色車輛圖標
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color='green' if dir_val==0 else 'blue', icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=480, width=800)

with col_info:
    # 系統 UI 部分自動回歸圓體
    st.markdown('<div style="color:#81c784; font-size:14px; margin-bottom:5px;">🚉 車站選擇</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("", list(LRT_STATIONS.keys()), label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    board_html = '<div class="board-container"><div class="board-header">📅 即將進站時刻</div>'
    if token:
        try:
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", headers={'Authorization': f'Bearer {token}'}).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    t_class, msg = ("time-red", "即時進站") if est <= 1 else ("time-yellow", f"約 {est} 分鐘")
                    # 進站數字用手寫體
                    board_html += f'<div class="board-content"><div class="hand-big-num {t_class}">{msg}</div></div>'
            else:
                board_html += '<div class="board-content"><div style="font-size:18px; color:#718096;">目前無班次</div></div>'
        except: pass
    board_html += '</div>'
    st.markdown(board_html, unsafe_allow_html=True)

    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div class="status-text">🕒 更新：{now.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="status-text">{loc_msg}：{u_pos[0]:.4f}, {u_pos[1]:.4f}</div>', unsafe_allow_html=True)

# --- D. 留言與紀錄 ---
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
col_msg, col_log = st.columns([1, 1])
with col_msg:
    st.markdown('<div class="board-container"><div class="board-header">✍️ 作者留言</div><div class="hand-msg" style="padding:15px; font-size:18px;">資料由 TDX 提供，拜託大家不要一直開著，我點數會不夠。</div></div>', unsafe_allow_html=True)
with col_log:
    # 紀錄區塊用圓體，保持整潔
    st.markdown('<div class="board-container"><div class="board-header">📦 更新紀錄 (v1.2.9)</div><div style="padding:15px; color:#cbd5e0; font-size:11px;">• 紅點顯示修復：加入座標保底，確保地圖必有紅點。<br>• 字體重分配：大標與留言維持手寫，UI回歸圓體。<br>• 藍綠車標：順逆行圖標恢復正常顯示。</div></div>', unsafe_allow_html=True)

time.sleep(30)
st.rerun()
