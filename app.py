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
# 1. 頁面配置與安全驗證
# ==========================================
st.set_page_config(page_title="高雄輕軌即時監測", layout="wide", initial_sidebar_state="collapsed")

def check_password():
    return True # 直接通過

check_password()

# ==========================================
# 2. 核心運算邏輯
# ==========================================
def haversine_distance(coord1, coord2):
    """計算球面距離"""
    R = 6371.0 
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_token():
    try:
        cid, csk = st.secrets["TD_ID_NEW"], st.secrets["TD_SECRET_NEW"]
        r = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', 
                         data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}, timeout=5)
        return r.json().get('access_token')
    except:
        return None

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
# 3. 主視覺樣式 (CSS 螢光效果)
# ==========================================
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

style_html = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    @font-face {{ font-family: 'MyHand'; src: url(data:font/otf;base64,{hand_base64}) format('opentype'); }}
    html, body, [class*="st-"], div, span, p {{ font-family: 'Zen Maru Gothic', sans-serif !important; }}
    .hand-font {{ font-family: 'MyHand', sans-serif !important; }}
    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}
    .header-title {{ color: #a5d6a7; text-align: center; font-size: 42px; margin-top: 10px; }}
    .sub-author {{ font-size: 18px; color: #888; text-align: center; margin-bottom: 10px; }}
    
    /* 順逆行看板專用樣式 */
    .arrival-card {{ background: #1c2128; border: 1px solid #30363d; border-radius: 12px; padding: 15px; margin: 10px 0; text-align: left; }}
    .dir-label {{ font-size: 14px; color: #8b949e; margin-bottom: 5px; }}
    .time-container {{ display: flex; align-items: baseline; gap: 8px; }}
    .time-prefix {{ font-size: 16px; color: #eee; }}
    .time-unit {{ font-size: 16px; color: #eee; }}
    
    /* 順行螢光綠 */
    .time-cw {{ color: #51cf66; font-size: 32px; font-weight: bold; text-shadow: 0 0 10px rgba(81,207,102,0.6); }}
    /* 逆行螢光藍 */
    .time-ccw {{ color: #339af0; font-size: 32px; font-weight: bold; text-shadow: 0 0 10px rgba(51,154,240,0.6); }}
    
    .info-container {{ background-color: #161b22; border: 1px solid #30363d; border-radius: 15px; padding: 18px; }}
</style>
"""
st.markdown(style_html, unsafe_allow_html=True)

# ==========================================
# 4. 資料與 UI 渲染
# ==========================================
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc and user_loc.get('coords') else [22.6508, 120.2825]
token = get_token()

st.markdown('<div class="header-title hand-font">高雄輕軌即時監測</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-author hand-font">Zongyou X Gemini</div>', unsafe_allow_html=True)

col_map, col_info = st.columns([7, 3.5])

with col_map:
    m = folium.Map(location=u_pos, zoom_start=15)
    folium.CircleMarker(location=u_pos, radius=9, color='#ffffff', weight=2, fill=True, fill_color='#ff5252', fill_opacity=1.0).add_to(m)
    
    if token:
        try:
            pos_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            pos_data = requests.get(pos_url, headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos_data if isinstance(pos_data, list) else pos_data.get('LivePositions', [])
            for t in trains:
                # 0: 順行(綠), 1: 逆行(藍)
                dir_val = t.get('Direction', 0) 
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], 
                    icon=folium.Icon(color='green' if dir_val==0 else 'blue', icon='train', prefix='fa'),
                    popup=f"{'順行方向' if dir_val==0 else '逆行方向'}"
                ).add_to(m)
        except: pass
    folium_static(m, height=600, width=None)

with col_info:
    st_names = list(LRT_STATIONS.keys())
    best_st = min(st_names, key=lambda n: haversine_distance(u_pos, LRT_STATIONS[n]))
    
    st.markdown('<p style="color:#a5d6a7; font-weight:bold; margin-bottom:5px;">📍 站點切換</p>', unsafe_allow_html=True)
    sel_st = st.selectbox("", st_names, index=st_names.index(best_st), label_visibility="collapsed")
    tid = sel_st.split()[0]
    
    st.markdown('<div class="info-container">', unsafe_allow_html=True)
    st.markdown('<p style="color:#ffd54f; font-weight:bold; font-size:16px; margin-bottom:10px;">📅 即時到站看板</p>', unsafe_allow_html=True)
    
    if token:
        try:
            # 💡 呼叫你找出的 LiveBoard API
            b_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON"
            b_res = requests.get(b_url, headers={'Authorization': f'Bearer {token}'}).json()
            
            if isinstance(b_res, list) and len(b_res) > 0:
                # 分類順逆行 (Pattern Recognition)
                cw_list = [i for i in b_res if "順行" in i.get('TripHeadSign', '')]
                ccw_list = [i for i in b_res if "逆行" in i.get('TripHeadSign', '')]
                
                # --- 順行顯示區 ---
                if cw_list:
                    cw = min(cw_list, key=lambda x: x.get('EstimateTime', 999))
                    t = int(cw.get('EstimateTime', 0))
                    msg = "即將進站" if t <= 1 else t
                    st.markdown(f'''<div class="arrival-card">
                        <div class="dir-label">🟢 順行方向</div>
                        <div class="time-container">
                            <span class="time-prefix">約</span>
                            <span class="hand-font time-cw">{msg}</span>
                            <span class="time-unit">{"分鐘" if t > 1 else ""}</span>
                        </div>
                    </div>''', unsafe_allow_html=True)
                
                # --- 逆行顯示區 ---
                if ccw_list:
                    ccw = min(ccw_list, key=lambda x: x.get('EstimateTime', 999))
                    t = int(ccw.get('EstimateTime', 0))
                    msg = "即將進站" if t <= 1 else t
                    st.markdown(f'''<div class="arrival-card">
                        <div class="dir-label">🔵 逆行方向</div>
                        <div class="time-container">
                            <span class="time-prefix">約</span>
                            <span class="hand-font time-ccw">{msg}</span>
                            <span class="time-unit">{"分鐘" if t > 1 else ""}</span>
                        </div>
                    </div>''', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#666; text-align:center; padding:20px;">目前無班次資訊</div>', unsafe_allow_html=True)
        except:
            st.error("資料讀取失敗")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div style="font-size:12px; color:#555; margin-top:10px;">🕒 更新於 {now.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)

# 底部留言與紀錄
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="info-container"><p style="color:#a5d6a7; font-weight:bold;">📦 版本紀錄 v1.7.0</p><p style="font-size:13px; color:#8b949e;">• 成功解析 TripHeadSign 欄位，達成順逆行獨立顯示<br>• 針對不同方向套用螢光綠/螢光藍視覺效果<br>• 優化 API 資料分類演算法</p></div>', unsafe_allow_html=True)

# 30 秒自動更新
time.sleep(30)
st.rerun()
