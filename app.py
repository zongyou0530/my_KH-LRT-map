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

# ==========================================
# 1. 頁面配置與安全驗證 (暫時停用驗證，但保留程式碼)
# ==========================================
st.set_page_config(page_title="高雄輕軌即時位置", layout="wide", initial_sidebar_state="collapsed")

def check_password():
    """密碼驗證邏輯 (保留 CSS 供 UI 一致性使用)"""
    # 💡 運算思維：抽象化 (Abstraction) - 暫時簡化系統進入流程，直接回傳 True
    return True 

    # 以下程式碼被 return True 擋住，不會執行，但完整保留供日後恢復
    if st.session_state.get("password_correct", False):
        return True
    
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DotGothic16&display=swap');
            .stApp {
                font-family: 'DotGothic16', sans-serif !important;
                background-color: #0e1117;
                letter-spacing: 2.5px; /* 這裡已修復隱形字元錯誤 */
            }
        </style>
    """, unsafe_allow_html=True)
    return False

# 💡 這裡原本是 if not check_password(): st.stop()
# 我們現在確保它直接通過
check_password()

# ==========================================
# 2. 核心運算邏輯
# ==========================================
# 💡 運算思維：演算法設計 (Algorithm Design) - 使用 Haversine 公式計算球面距離
def haversine_distance(coord1, coord2):
    R = 6371.0 
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_token():
    """向 TDX 請求 API 通行證"""
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        r = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                         data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk})
        return r.json().get('access_token')
    except: return None

# 💡 運算思維：模式識別 (Pattern Recognition) - 將車站建立為標準化字典資料庫
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

# ==========================================
# 3. 主視覺樣式 (CSS)
# ==========================================
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

style_html = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&family=DotGothic16&display=swap');
    @font-face {{ font-family: 'MyHand'; src: url(data:font/otf;base64,{hand_base64}) format('opentype'); }}
    
    html, body, [class*="st-"], div, span, p {{ font-family: 'Zen Maru Gothic', sans-serif !important; }}
    .hand-font {{ font-family: 'MyHand', sans-serif !important; }}
    .stApp {{ background-color: #0e1117; color: white; letter-spacing: 1.5px; }}
    header {{ visibility: hidden; }}

    @media (min-width: 1024px) {{
        .header-title {{ font-size: 52px !important; letter-spacing: 4px; }}
    }}

    .header-title {{ color: #a5d6a7; text-align: center; margin-top: 10px; }}
    .sub-author {{ font-size: 18px; color: #888; text-align: center; margin-bottom: 20px; }}
    .legend-bar {{ background: rgba(33,38,45,0.9); border: 1px solid #30363d; border-radius: 50px; padding: 8px 25px; text-align: center; margin: 0 auto 20px auto; width: fit-content; font-size: 14px; }}
    .arrival-card {{ background: linear-gradient(135deg, #2d333b 0%, #1c2128 100%); border: 1px solid #444c56; border-radius: 18px; padding: 18px; margin: 12px 0; text-align: center; }}
    .time-val {{ font-size: 32px; font-weight: bold; }}
    .time-red {{ color: #ff6b6b; text-shadow: 0 0 10px rgba(255,107,107,0.5); }}
    .time-yellow {{ color: #ffd54f; text-shadow: 0 0 10px rgba(255,213,79,0.5); }}
    .info-container {{ background-color: #161b22; border: 1px solid #30363d; border-radius: 15px; padding: 18px; margin-bottom: 15px; }}
</style>
"""
st.markdown(style_html, unsafe_allow_html=True)

# ==========================================
# 4. 資料與位置處理
# ==========================================
# 💡 運算思維：問題拆解 (Decomposition) - 獲取當前環境變數（使用者座標與 API Token）
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc and user_loc.get('coords') else [22.6508, 120.2825]
token = get_token()

# ==========================================
# 5. UI 渲染 (地圖與看板)
# ==========================================
st.markdown('<div class="header-title hand-font">高雄輕軌即時監測</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-author hand-font">Zongyou X Gemini</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-bar">🟢 順行 | 🔵 逆行 | 🔴 目前位置</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3.5])

with col_map:
    # 💡 模式識別：移除特定底圖設定，使用 OSM 標準路網底圖以利觀察軌道細節
    m = folium.Map(location=u_pos, zoom_start=15)
    folium.CircleMarker(location=u_pos, radius=9, color='#ffffff', weight=2, fill=True, fill_color='#ff5252', fill_opacity=1.0).add_to(m)
    
    if token:
        try:
            # 💡 抽象化：從複雜的 API JSON 中只提取關鍵座標與方向資料
            pos_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            pos_data = requests.get(pos_url, headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos_data if isinstance(pos_data, list) else pos_data.get('LivePositions', [])
            for t in trains:
                dir_val = t.get('Direction', 0)
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                    icon=folium.Icon(color='green' if dir_val==0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m, height=650, width=None)

with col_info:
    # 💡 演算法設計：利用 min 函式與自定義距離公式，自動計算最近車站
    st_names = list(LRT_STATIONS.keys())
    best_st = min(st_names, key=lambda n: haversine_distance(u_pos, LRT_STATIONS[n]))
    
    st.markdown('<p style="margin-bottom:2px; font-size:15px; color:#a5d6a7; font-weight:bold;">📍 站點切換</p>', unsafe_allow_html=True)
    sel_st = st.selectbox("", st_names, index=st_names.index(best_st), label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    st.markdown('<div class="info-container">', unsafe_allow_html=True)
    st.markdown('<p style="color:#ffd54f; font-weight:bold; font-size:16px; margin-bottom:10px;">📅 即將進站時刻</p>', unsafe_allow_html=True)
    if token:
        try:
            b_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON"
            b_res = requests.get(b_url, headers={'Authorization': f'Bearer {token}'}).json()
            if b_res:
                for item in sorted(b_res, key=lambda x: x.get('EstimateTime', 999))[:2]:
                    est = int(item.get('EstimateTime', 0))
                    t_class, msg = ("time-red", "即時進站") if est <= 1 else ("time-yellow", f"約 {est} 分鐘")
                    st.markdown(f'<div class="arrival-card"><div class="hand-font time-val {t_class}">{msg}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="text-align:center; color:#888; padding:30px;">目前無班次資訊</div>', unsafe_allow_html=True)
        except: pass
    st.markdown('</div>', unsafe_allow_html=True)

    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div style="font-size:12px; color:#666;">🕒 更新：{now.strftime("%H:%M:%S")} | 🛰️ 座標：{u_pos[0]:.3f}, {u_pos[1]:.3f}</div>', unsafe_allow_html=True)

# ==========================================
# 6. 作者留言與版本紀錄 (Footer)
# ==========================================
st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="info-container"><p style="color:#a5d6a7; font-weight:bold;">✍️ 作者留言</p><p class="hand-font" style="font-size:18px;">不要開著 TDX提供的免費用量會耗盡。</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="info-container"><p style="color:#a5d6a7; font-weight:bold;">📦 系統紀錄 v1.6.3</p><p style="font-size:13px; color:#8b949e;">• 修正字距渲染錯誤與語法異常<br>• 整合運算思維 (CT) 邏輯架構於註解<br>• 恢復 OSM 標準路網圖</p></div>', unsafe_allow_html=True)

# 💡 自動化流程：設定 30 秒自動更新
time.sleep(30)
st.rerun()
