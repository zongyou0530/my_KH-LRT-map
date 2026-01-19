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

# 1. 頁面基礎配置：設定寬版模式與標題
st.set_page_config(page_title="高雄輕軌即時監測", layout="wide", initial_sidebar_state="collapsed")

# --- A. 字體處理邏輯 (解決網頁字體顯示問題) ---
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

# --- B. CSS 視覺化設計 (人性化 UI 排版) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{hand_base64}) format('opentype');
    }}
    /* 整體背景與容器下移，營造呼吸感 */
    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}
    .block-container {{ padding-top: 6rem !important; padding-bottom: 2rem !important; }}
    
    /* 標題與標籤樣式 */
    .header-title {{ font-family: 'MyHand', sans-serif !important; font-size: 52px !important; color: #a5d6a7; text-align: center; line-height: 1.1; margin-bottom: 10px !important; }}
    .legend-container {{ font-family: 'Zen Maru Gothic', sans-serif !important; background-color: #1a1d23; border: 1px solid #30363d; border-radius: 15px; padding: 4px 12px; text-align: center; margin: 0 auto 10px auto !important; width: fit-content; font-size: 13px; color: #cccccc; }}
    
    /* 資訊卡片與方向標籤 */
    .info-card {{ background-color: #1a1d23; border: 1px solid #30363d; border-radius: 10px; padding: 10px 15px; margin-bottom: 8px; }}
    .dir-label {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #ffd54f; font-size: 15px; font-weight: bold; margin: 10px 0 5px 0; border-left: 4px solid #ffd54f; padding-left: 8px; }}
    .label-round {{ font-family: 'Zen Maru Gothic', sans-serif !important; color: #81c784; font-size: 14px; margin-bottom: 2px; }}
    .content-hand {{ font-family: 'MyHand', sans-serif !important; font-size: 24px; }}
    .status-text-left {{ font-family: 'Zen Maru Gothic', sans-serif !important; text-align: left; color: #718096; font-size: 12px; margin-top: 2px; }}
</style>
""", unsafe_allow_html=True)

# 標題與圖例顯示
st.markdown('<div class="header-title">高雄輕軌<br>即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-container">🟢順行 | 🔵逆行 | 🔴目前位置</div>', unsafe_allow_html=True)

# --- C. 資料獲取區 (API 串接) ---
user_loc = get_geolocation()
user_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc else None

def get_tdx_token():
    """ 取得政府 TDX 平台的驗證通行證 """
    try:
        cid = st.secrets["TD_ID_NEW"]
        csk = st.secrets["TD_SECRET_NEW"]
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                           data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk})
        return res.json().get('access_token')
    except: return None

def get_live_positions(tk):
    """ 抓取全線列車即時座標 """
    try:
        res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                           headers={'Authorization': f'Bearer {tk}'}).json()
        return res if isinstance(res, list) else res.get('LivePositions', [])
    except: return []

# 主畫面排版：左 7 右 3
col_map, col_info = st.columns([7, 3.5])

# 先換好通行證
token = get_tdx_token()

with col_map:
    # 1. 建立地圖：預設中心點為高雄美術館
    center = user_pos if user_pos else [22.6593, 120.2868]
    m = folium.Map(location=center, zoom_start=15)
    
    # 2. 標記使用者位置
    if user_pos:
        folium.CircleMarker(user_pos, radius=7, color='white', weight=2, fill=True, fill_color='red', fill_opacity=1, popup="我的位置").add_to(m)
    
    # 3. 標記列車位置
    if token:
        live_data = get_live_positions(token)
        for t in live_data:
            try:
                # 判斷順逆行決定圖標顏色：0為綠色, 1為藍色
                p_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                    icon=folium.Icon(color=p_color, icon='train', prefix='fa')
                ).add_to(m)
            except: continue
    folium_static(m, height=480, width=800)

with col_info:
    st.markdown('<div class="label-round">🚉 選擇監測車站</div>', unsafe_allow_html=True)
    stations = {"C21 美術館": "C21", "C24 愛河之心": "C24", "C1 籬仔內": "C1", "C14 哈瑪星": "C14"}
    sel_st_label = st.selectbox("", list(stations.keys()), index=0, label_visibility="collapsed")
    tid = stations[sel_st_label]
    
    if token:
        try:
            # 抓取選定車站的即時看板資料
            b_res = requests.get(f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON", 
                                 headers={'Authorization': f'Bearer {token}'}).json()
            
            if isinstance(b_res, list) and len(b_res) > 0:
                # --- 救命過濾邏輯：區分順逆行 ---
                dir0 = [i for i in b_res if i.get('Direction') == 0]
                dir1 = [i for i in b_res if i.get('Direction') == 1]
                
                # 如果資料裡都沒有標註方向 (API 異常)，就把所有資料視為順行顯示，確保不空白
                if not dir0 and not dir1:
                    dir0 = b_res

                def display_board(data_list, title):
                    st.markdown(f'<div class="dir-label">{title}</div>', unsafe_allow_html=True)
                    if not data_list:
                        st.markdown('<div class="info-card"><div class="content-hand" style="font-size:16px; color:#718096;">暫無班次資訊</div></div>', unsafe_allow_html=True)
                    else:
                        # 排序時間，抓最快的一班
                        for item in sorted(data_list, key=lambda x: x.get('EstimateTime', 999))[:1]:
                            est = int(item.get('EstimateTime', 0))
                            dest = item.get('DestinationStationName', {}).get('Zh_tw', '未知')
                            msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                            # 警示紅字邏輯：2分鐘內變紅
                            text_style = 'color: #ff5252 !important;' if est <= 2 else 'color: #ffffff;'
                            st.markdown(f'''
                                <div class="info-card">
                                    <div class="content-hand" style="{text_style}">{msg}</div>
                                    <div style="font-size:12px; color:#718096; font-family: 'Zen Maru Gothic';">往 {dest} 方向</div>
                                </div>
                            ''', unsafe_allow_html=True)

                display_board(dir0, "🟢 順行方向")
                display_board(dir1, "🔵 逆行方向")
            else:
                st.markdown('<div class="info-card">目前此站無列車即時預估資訊</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"資料讀取錯誤：{e}")

    # 更新時間標籤
    now_t = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%H:%M:%S")
    st.markdown(f'<div class="status-text-left">📍 最後更新時間：{now_t}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="status-text-left">{"✅ 定位成功" if user_pos else "⚠️ 定位讀取中..."}</div>', unsafe_allow_html=True)

# --- D. 底部更新日誌與留言 ---
st.markdown('<div style="height:15px;"></div>', unsafe_allow_html=True)
col_msg, col_log = st.columns([1, 1.2])

with col_msg:
    st.markdown(f'''<div class="info-card"><div class="label-round">✍️ 開發者筆記</div><div class="content-hand" style="font-size: 18px;">
    克服了 API 資料混合的難題，現在能正確分流順逆行資訊。
    </div></div>''', unsafe_allow_html=True)

with col_log:
    st.markdown(f"""
    <div class="info-card">
        <div class="label-round">📦 核心邏輯優化紀錄</div>
        <div class="update-log-box">
            • <b>資料分流：</b> 解析 Direction 屬性，成功區分去回程看板。<br>
            • <b>容錯設計：</b> 當 API 標籤缺失時，系統會自動轉入相容模式，避免空白畫面。<br>
            • <b>即時警示：</b> 保持 EstimateTime <= 2 的紅字動態提醒功能。
        </div>
    </div>
    """, unsafe_allow_html=True)

# 休息 30 秒後重新運行，達成即時更新效果
time.sleep(30)
st.rerun()
