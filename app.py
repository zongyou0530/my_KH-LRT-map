import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+P+One&family=Kiwi+Maru:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    .mochiy-font { font-family: 'Mochiy Pop P One', sans-serif !important; color: #2e7d32; }
    html, body, [data-testid="stAppViewContainer"], p, div, span, label {
        font-family: 'Kiwi Maru', serif !important;
        font-weight: normal !important;
    }
    /* 藍色對話框 */
    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 15px; border-radius: 10px; margin-bottom: 20px; color: #0d47a1; }
    
    /* 站牌卡片樣式 */
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 15px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 10px solid #ccc;
    }
    .dir-tag { display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 0.8em; margin-bottom: 5px; color: white; }
    .time-normal { font-size: 1.5em; color: #4D0000; }
    .time-urgent { font-size: 1.5em; color: #FF0000; }
</style>
''', unsafe_allow_html=True)

# 2. 車站清單
LRT_STATIONS = [
    "C1 籬仔內", "C2 凱旋瑞田", "C3 前鎮之星", "C4 凱旋中華", "C5 夢時代", "C6 經貿園區", 
    "C7 軟體園區", "C8 高雄展覽館", "C9 旅運中心", "C10 光榮碼頭", "C11 真愛碼頭", "C12 駁二大義", 
    "C13 駁二蓬萊", "C14 哈瑪星", "C15 壽山公園", "C16 文武聖殿", "C17 鼓山區公所", "C18 鼓山", 
    "C19 馬卡道", "C20 台鐵美術館", "C21A 內維藝術中心", "C21 美術館", "C22 聯合醫院", "C23 龍華國小", 
    "C24 愛河之心", "C25 新上國小", "C26 灣仔內", "C27 鼎山街", "C28 高雄高工", "C29 樹德家商", 
    "C30 科工館", "C31 聖功醫院", "C32 凱旋公園", "C33 衛生局", "C34 五權國小", "C35 凱旋武昌", 
    "C36 凱旋二聖", "C37 輕軌機廠"
]

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei'))

@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

st.markdown('<div class="mochiy-font" style="font-size:42px;">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="info-box">💡 <b>強制修復：</b> 已手動重連順逆向資料鏈結。若地圖有綠車，右側應會同步出現綠色卡片。</div>', unsafe_allow_html=True)

token = get_token()
col1, col2 = st.columns([7, 3])

# --- 地圖 ---
with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_pos.get('LivePositions', []):
                folium.Marker(
                    [t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']],
                    icon=folium.Icon(color='green' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m, height=520, width=950)

# --- 站牌 ---
with col2:
    st.markdown('<span class="mochiy-font" style="font-size:24px;">🚉 選擇車站</span>', unsafe_allow_html=True)
    sel_st_full = st.selectbox("請選擇：", LRT_STATIONS, index=19)
    # 關鍵：提取純名稱，例如 "台鐵美術館"
    target_name = sel_st_full.split(" ")[1]

    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", headers={'Authorization': f'Bearer {token}'})
            all_data = resp.json()
            
            # --- 強制搜尋邏輯 ---
            # 不分方向，只要站名包含關鍵字就全抓
            matched = [d for d in all_data if target_name in d.get('StationName', {}).get('Zh_tw', '')]
            
            if matched:
                matched.sort(key=lambda x: x.get('EstimateTime', 999))
                for item in matched:
                    d_code = item.get('Direction') # 0:順行, 1:逆行
                    d_label = "順行 (外圈)" if d_code == 0 else "逆行 (內圈)"
                    d_color = "#2e7d32" if d_code == 0 else "#1565c0"
                    est = int(item.get('EstimateTime', 0))
                    
                    t_style = "time-urgent" if est <= 2 else "time-normal"
                    t_msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card" style="border-left-color: {d_color};">
                        <div class="dir-tag" style="background-color: {d_color};">{d_label}</div>
                        <div class="{t_style}">狀態：{t_msg}</div>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.write("暫無預估資訊")
        except: st.error("連線異常")

time.sleep(30)
st.rerun()
