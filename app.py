import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import base64
import os
import time
import datetime
import pytz
from streamlit_js_eval import get_geolocation

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體處理 ---
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

# ⚠️ CSS 徹底重寫：確保圓體與手寫體分離
st.markdown("""
<style>
    @font-face {
        font-family: 'MyHand';
        src: url(data:font/otf;base64,""" + hand_base64 + """) format('opentype');
    }
    
    /* 圓體部分：使用手機系統最漂亮的圓潤字體 */
    html, body, [class*="st-"], .round-font {
        font-family: system-ui, -apple-system, sans-serif !important;
        font-weight: 500;
    }

    /* 手寫體部分：僅限特定區域 */
    .hand-text {
        font-family: 'MyHand', sans-serif !important;
    }

    .stApp { background-color: #0e1117; color: white; }
    header { visibility: hidden; }
    
    .title-box { text-align: center; margin-bottom: 20px; }
    .main-title { font-size: 45px; color: #a5d6a7; line-height: 1.2; }
    .author-name { font-size: 20px; color: #888888; margin-top: 5px; }
    
    .legend-tag { background: #1a1d23; border: 1px solid #333; border-radius: 15px; padding: 4px 12px; font-size: 13px; margin-bottom: 15px; display: inline-block; }
    
    .info-card { background: #1a1d23; border: 1px solid #30363d; border-radius: 12px; margin-bottom: 10px; }
    .card-header { background: #252930; padding: 8px 15px; font-size: 14px; color: #ffd54f; border-radius: 12px 12px 0 0; }
    .card-body { padding: 15px; text-align: center; }
    
    .arrival-msg { font-size: 35px; }
    .text-red { color: #ff5252; }
    .text-yellow { color: #ffd54f; }
</style>
""", unsafe_allow_html=True)

# --- B. 核心邏輯 ---
LRT_STATIONS = {
    "C1 籬仔內": [22.6015, 120.3204], "C19 馬卡道": [22.6508, 120.2825], "C20 臺鐵美術館": [22.6565, 120.2838], "C21 美術館": [22.6593, 120.2868], "C22 聯合醫院": [22.6652, 120.2891]
}

def get_token():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        r = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                         data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk})
        return r.json().get('access_token')
    except: return None

# 定位保底：若無定位則固定在 C19 馬卡道
user_loc = get_geolocation()
if user_loc and user_loc.get('coords'):
    u_lat, u_lon = user_loc['coords']['latitude'], user_loc['coords']['longitude']
    u_pos = [u_lat, u_lon]
    loc_status = "🛰️ 實時 GPS 定位成功"
else:
    u_pos = [22.6508, 120.2825]
    loc_status = "📍 使用預設位置 (馬卡道站)"

token = get_token()

# 渲染標題
st.markdown(f'''<div class="title-box">
    <div class="main-title hand-text">高雄輕軌<br>即時位置地圖</div>
    <div class="author-name hand-text">Zongyou X Gemini</div>
    <div class="legend-tag">🟢順行 🔵逆行 <span style="color:#ff5252;">🔴您在此</span></div>
</div>''', unsafe_allow_html=True)

col_m, col_i = st.columns([7, 3.5])

with col_m:
    # 建立地圖
    m = folium.Map(location=u_pos, zoom_start=15, control_scale=True)
    
    # 🔴 這次改用 Folium 原生紅點標記，保證你看得到
    folium.Marker(
        location=u_pos,
        popup="您的位置",
        icon=folium.Icon(color='red', icon='user', prefix='fa')
    ).add_to(m)
    
    # 🚆 顯示輕軌車輛
    if token:
        try:
            pos_data = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos_data if isinstance(pos_data, list) else pos_data.get('LivePositions', [])
            for t in trains:
                c = 'green' if t.get('Direction', 0) == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                              icon=folium.Icon(color=c, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=450, width=800)

with col_i:
    # 下拉選單 (圓體)
    st.markdown('<div style="color:#a5d6a7; font-size:14px;">🚉 車站選單</div>', unsafe_allow_html=True)
    sel_st = st.selectbox("", list(LRT_STATIONS.keys()), label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    # 時刻表看板
    st.markdown('<div class="info-card"><div class="card-header">📅 即將進站</div>', unsafe_allow_html=True)
    if token:
        try:
            b = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", headers={'Authorization': f'Bearer {token}'}).json()
            if b:
                for item in sorted(b, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    clr = "text-red" if est <= 1 else "text-yellow"
                    st.markdown(f'<div class="card-body"><div class="arrival-msg hand-text {clr}">{msg}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card-body">目前無資訊</div>', unsafe_allow_html=True)
        except: pass
    st.markdown('</div>', unsafe_allow_html=True)

    # 狀態資訊 (圓體)
    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div style="color:#718096; font-size:12px;">🕒 更新：{now.strftime("%H:%M:%S")}<br>{loc_status}</div>', unsafe_allow_html=True)

# --- D. 底部區塊 ---
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="info-card"><div class="card-header">✍️ 作者留言</div><div class="card-body hand-text" style="font-size:18px;">資料由 TDX 提供，拜託大家不要一直開著，我點數會不夠。</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="info-card"><div class="card-header">📦 更新紀錄 (v1.3.0)</div><div style="padding:15px; font-size:12px; color:#999;">• 紅點修正：改用原生紅色圖標，解決消失問題。<br>• 字體校正：UI 採用系統圓體，看板與留言維持手寫。<br>• 穩定性：解決 CSS 衝突導致的 NameError。</div></div>', unsafe_allow_html=True)

time.sleep(30)
st.rerun()
