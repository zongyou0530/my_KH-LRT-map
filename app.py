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
# 1. 頁面配置
# ==========================================
st.set_page_config(page_title="高雄輕軌即時監測", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. 字體與 CSS 樣式修正
# ==========================================
font_path = "ZONGYOOOOOOU1.otf"
hand_base64 = ""
if os.path.exists(font_path):
    with open(font_path, "rb") as f:
        hand_base64 = base64.b64encode(f.read()).decode()

style_html = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap');
    
    @font-face {{
        font-family: 'MyHand';
        src: url(data:font/otf;base64,{hand_base64}) format('opentype');
    }}

    /* 全域字體設定 */
    html, body, [class*="st-"], div, span, p {{
        font-family: 'Zen Maru Gothic', sans-serif;
    }}

    .hand-font {{
        font-family: 'MyHand' !important;
    }}

    .stApp {{ background-color: #0e1117; color: white; }}
    header {{ visibility: hidden; }}

    /* 標題與留言樣式 */
    .header-title {{ color: #a5d6a7; text-align: center; font-size: 42px; margin-top: 10px; }}
    .sub-author {{ font-size: 18px; color: #888; text-align: center; margin-bottom: 20px; }}
    .author-note {{ 
        background: rgba(255,255,255,0.05); 
        border-left: 4px solid #a5d6a7; 
        padding: 15px; 
        margin: 10px 0; 
        font-size: 15px; 
        border-radius: 4px;
        color: #ccd6f6;
    }}

    /* 看板樣式修正：移除多餘邊距 */
    .info-container {{ 
        background-color: #161b22; 
        border: 1px solid #30363d; 
        border-radius: 15px; 
        padding: 20px;
        margin-top: -15px; /* 抵銷 selectbox 下方的多餘空間 */
    }}

    .arrival-card {{ 
        background: #1c2128; 
        border: 1px solid #30363d; 
        border-radius: 12px; 
        padding: 15px; 
        margin-bottom: 15px; 
    }}

    .dir-label {{ font-size: 14px; color: #8b949e; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }}
    .time-container {{ display: flex; align-items: center; gap: 10px; }}
    .time-prefix, .time-unit {{ font-size: 18px; color: #eee; }}

    /* 強制手寫體套用到時間數字並發光 */
    .time-val {{
        font-family: 'MyHand' !important;
        font-size: 48px;
        line-height: 1;
        margin: 0 5px;
    }}
    .time-cw {{ color: #51cf66; text-shadow: 0 0 15px rgba(81,207,102,0.7); }}
    .time-ccw {{ color: #339af0; text-shadow: 0 0 15px rgba(51,154,240,0.7); }}

</style>
"""
st.markdown(style_html, unsafe_allow_html=True)

# ==========================================
# 3. 定義車站與功能 (與先前相同)
# ==========================================
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
                         data={'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': csk}, timeout=5)
        return r.json().get('access_token')
    except: return None

def haversine(c1, c2):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, [c1[0], c1[1], c2[0], c2[1]])
    dla, dlo = la2 - la1, lo2 - lo1
    a = math.sin(dla/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlo/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ==========================================
# 4. 主程式渲染
# ==========================================
user_loc = get_geolocation()
u_pos = [user_loc['coords']['latitude'], user_loc['coords']['longitude']] if user_loc and user_loc.get('coords') else [22.6508, 120.2825]
token = get_token()

# 標題
st.markdown('<div class="header-title hand-font">高雄輕軌即時地圖</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-author hand-font">Zongyou X Gemini</div>', unsafe_allow_html=True)

# 佈局：地圖 | 看板
col_left, col_right = st.columns([7, 3.5])

with col_left:
    m = folium.Map(location=u_pos, zoom_start=15)
    folium.CircleMarker(location=u_pos, radius=8, color='#fff', weight=2, fill=True, fill_color='#ff5252', fill_opacity=1).add_to(m)
    
    if token:
        try:
            pos_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            pos_data = requests.get(pos_url, headers={'Authorization': f'Bearer {token}'}).json()
            trains = pos_data if isinstance(pos_data, list) else pos_data.get('LivePositions', [])
            for t in trains:
                d_val = t.get('Direction', 0)
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']],
                    icon=folium.Icon(color='green' if d_val==0 else 'blue', icon='train', prefix='fa'),
                    popup=f"{'順行' if d_val==0 else '逆行'}"
                ).add_to(m)
        except: pass
    folium_static(m, height=580, width=None)

with col_right:
    # 站點選擇
    st_names = list(LRT_STATIONS.keys())
    best_st = min(st_names, key=lambda n: haversine(u_pos, LRT_STATIONS[n]))
    
    st.markdown('<p style="color:#a5d6a7; font-weight:bold; margin-bottom:5px;">📍 選擇站點 (已自動定位) </p>', unsafe_allow_html=True)
    sel_st = st.selectbox(" ", st_names, index=st_names.index(best_st), label_visibility="collapsed")
    tid = sel_st.split()[0]

    # 即時看板容器
    st.markdown('<div class="info-container">', unsafe_allow_html=True)
    st.markdown('<p style="color:#ffd54f; font-weight:bold; font-size:16px; margin-bottom:15px;">📅 即時到站看板</p>', unsafe_allow_html=True)
    
    if token:
        try:
            b_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationID eq '{tid}'&$format=JSON"
            b_res = requests.get(b_url, headers={'Authorization': f'Bearer {token}'}).json()
            
            cw_list = [i for i in b_res if "順行" in i.get('TripHeadSign', '')]
            ccw_list = [i for i in b_res if "逆行" in i.get('TripHeadSign', '')]

            # 順行顯示
            if cw_list:
                cw = min(cw_list, key=lambda x: x.get('EstimateTime', 999))
                val = int(cw.get('EstimateTime', 0))
                display_time = "進站中" if val <= 1 else val
                unit = "" if val <= 1 else "分鐘"
                st.markdown(f'''<div class="arrival-card">
                    <div class="dir-label"><span style="color:#51cf66">●</span> 順行方向</div>
                    <div class="time-container">
                        <span class="time-prefix">{"約" if val > 1 else ""}</span>
                        <span class="time-val time-cw">{display_time}</span>
                        <span class="time-unit">{unit}</span>
                    </div>
                </div>''', unsafe_allow_html=True)

            # 逆行顯示
            if ccw_list:
                ccw = min(ccw_list, key=lambda x: x.get('EstimateTime', 999))
                val = int(ccw.get('EstimateTime', 0))
                display_time = "進站中" if val <= 1 else val
                unit = "" if val <= 1 else "分鐘"
                st.markdown(f'''<div class="arrival-card">
                    <div class="dir-label"><span style="color:#339af0">●</span> 逆行方向</div>
                    <div class="time-container">
                        <span class="time-prefix">{"約" if val > 1 else ""}</span>
                        <span class="time-val time-ccw">{display_time}</span>
                        <span class="time-unit">{unit}</span>
                    </div>
                </div>''', unsafe_allow_html=True)
            
            if not cw_list and not ccw_list:
                st.markdown('<div style="color:#666; text-align:center;">目前無班次資訊</div>', unsafe_allow_html=True)
        except: st.error("讀取失敗")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 🕒 時間更新
    now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    st.markdown(f'<div style="font-size:12px; color:#555; margin-top:15px; text-align:right;">🕒 最新更新時間：{now.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)

# ==========================================
# 5. 作者留言與版本紀錄 (補回留言區)
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div class="author-note hand-font">
    <strong>💡 作者寄語：</strong><br>
    不要一直開著 TDX用量會很快用完。
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="info-container" style="margin-top:10px;">
    <p style="color:#a5d6a7; font-weight:bold; margin-bottom:5px;">📦 版本紀錄 v1.7.2</p>
    <p style="font-size:13px; color:#8b949e; line-height:1.6;">
        待寫
    </p>
</div>
""", unsafe_allow_html=True)

# 30秒自動更新
time.sleep(30)
st.rerun()
