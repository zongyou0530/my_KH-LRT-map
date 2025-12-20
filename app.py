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
    .mochiy-font {
        font-family: 'Mochiy Pop P One', sans-serif !important;
        font-weight: normal !important;
        color: #2e7d32;
    }
    .main-title { font-size: 42px; margin-bottom: 20px; } /* 手機端標題稍微調小避免跑版 */
    .side-title { font-size: 24px; margin-bottom: 10px; display: block; }
    
    html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, div, span, label {
        font-family: 'Kiwi Maru', serif !important;
        font-weight: normal !important;
    }

    /* 藍色對話框 */
    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 12px; border-radius: 10px; margin-bottom: 10px; color: #0d47a1; font-size: 0.9em; }
    
    /* 站牌卡片 */
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 15px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 10px; 
    }
    .dir-tag {
        display: inline-block; padding: 2px 8px; border-radius: 5px; 
        font-size: 0.8em; margin-bottom: 5px; color: white;
    }
    .time-normal { font-size: 1.5em; color: #4D0000; font-weight: normal !important; }
    .time-urgent { font-size: 1.5em; color: #FF0000; font-weight: normal !important; }

    /* 優化選單字體與間距 */
    .stSelectbox label { font-size: 1.1em !important; color: #333; }
</style>
''', unsafe_allow_html=True)

# 2. 定義站點清單 (依照路線順序)
LRT_STATIONS = [
    "C1 籬仔內", "C2 凱旋瑞田", "C3 前鎮之星", "C4 凱旋中華", "C5 夢時代", "C6 經貿園區", 
    "C7 軟體園區", "C8 高雄展覽館", "C9 旅運中心", "C10 光榮碼頭", "C11 真愛碼頭", "C12 駁二大義", 
    "C13 駁二蓬萊", "C14 哈瑪星", "C15 壽山公園", "C16 文武聖殿", "C17 鼓山區公所", "C18 鼓山", 
    "C19 馬卡道", "C20 台鐵美術館", "C21A 內惟藝術中心", "C21 美術館", "C22 聯合醫院", "C23 龍華國小", 
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

# --- UI 開始 ---
st.markdown('<div class="mochiy-font main-title">高雄輕軌即時監測</div>', unsafe_allow_html=True)
st.markdown('<div class="info-box">💡 <b>手機模式：</b> 已移除手動輸入，請直接點擊下方選單選擇車站。</div>', unsafe_allow_html=True)

token = get_token()
map_time, board_time = "讀取中...", "讀取中..."
col1, col2 = st.columns([7.2, 2.8]) # 稍微調整比例符合手機橫向觀看

# --- 左側：地圖 ---
with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token:
        try:
            live_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                                    headers={'Authorization': f'Bearer {token}'}, timeout=8).json()
            for t in live_res.get('LivePositions', []):
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                d_name = "順行 (外圈)" if t.get('Direction') == 0 else "逆行 (內圈)"
                pop_html = f"<div style='font-family: Kiwi Maru;'>方向：{d_name}<br>更新：{get_now_tw().strftime('%H:%M:%S')}</div>"
                folium.Marker(
                    [lat, lon], popup=folium.Popup(pop_html, max_width=150),
                    icon=folium.Icon(color='green' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
            map_time = get_now_tw().strftime('%H:%M:%S')
        except: map_time = "更新中..."
    folium_static(m, height=500, width=1000)

# --- 右側：站牌 (純選單模式) ---
with col2:
    st.markdown('<span class="mochiy-font side-title">🚉 選擇車站</span>', unsafe_allow_html=True)
    # 使用選單取代輸入框，並移除輸入歷史紀錄干擾
    sel_st_full = st.selectbox("請由下方選擇車站：", LRT_STATIONS, index=19) # 預設選台鐵美術館
    sel_st = sel_st_full.split(" ")[1] # 取得純站名如「台鐵美術館」

    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", 
                                headers={'Authorization': f'Bearer {token}'}, timeout=10)
            if resp.status_code == 200:
                all_data = resp.json()
                # 解決順行缺失問題：針對關鍵字進行模糊比對
                target = "美術館" if "美術館" in sel_st else sel_st
                valid_data = [b for b in all_data if target in b.get('StationName', {}).get('Zh_tw', '') and b.get('EstimateTime') is not None]
                
                if valid_data:
                    valid_data.sort(key=lambda x: x.get('EstimateTime', 0))
                    for item in valid_data:
                        d_code = item.get('Direction')
                        d_text = "順行 (外圈)" if d_code == 0 else "逆行 (內圈)"
                        b_color = "#2e7d32" if d_code == 0 else "#1565c0"
                        est = int(item.get('EstimateTime'))
                        
                        # 依照時間設定顏色：≤2分為鮮紅，其餘為深褐
                        t_class = "time-urgent" if est <= 2 else "time-normal"
                        t_text = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                        
                        st.markdown(f'''
                        <div class="arrival-card" style="border-left: 10px solid {b_color};">
                            <div class="dir-tag" style="background-color:{b_color};">{d_text}</div>
                            <div class="{t_class}">狀態：{t_text}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    board_time = get_now_tw().strftime('%H:%M:%S')
                else:
                    st.info(f"⏳ 「{sel_st}」目前暫無列車預估")
            else: st.warning("📡 API 暫時繁忙...")
        except: board_time = "連線重試中..."

st.markdown(f'<div style="color:gray; font-size:0.8em; margin-top:20px;">📍 地圖更新：{map_time} | 🕒 站牌更新：{board_time}</div>', unsafe_allow_html=True)

time.sleep(30)
st.rerun()
