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
    .mochiy-font { font-family: 'Mochiy Pop P One', sans-serif !important; font-weight: normal !important; color: #2e7d32; }
    .main-title { font-size: 42px; margin-bottom: 20px; }
    .side-title { font-size: 24px; margin-bottom: 10px; display: block; }
    
    html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, div, span, label {
        font-family: 'Kiwi Maru', serif !important;
        font-weight: normal !important;
    }
    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 12px; border-radius: 10px; margin-bottom: 10px; color: #0d47a1; }
    .legend-box { background-color: #f5f5f5; border: 1px solid #ddd; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; }

    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 15px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 10px; 
    }
    .dir-tag { display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 0.8em; margin-bottom: 5px; color: white; }
    
    /* 顏色修正：#4D0000 為深褐，#FF0000 為鮮紅，無加粗 */
    .time-normal { font-size: 1.5em; color: #4D0000; font-weight: normal !important; }
    .time-urgent { font-size: 1.5em; color: #FF0000; font-weight: normal !important; }
</style>
''', unsafe_allow_html=True)

# 2. 定義車站 (優化匹配邏輯)
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
st.markdown('<div class="legend-box">📍 <b>圖例：</b> <span style="color:#2e7d32;">● 順行 (外圈)</span> | <span style="color:#1565c0;">● 逆行 (內圈)</span></div>', unsafe_allow_html=True)

token = get_token()
map_time, board_time = "讀取中...", "讀取中..."
col1, col2 = st.columns([7, 3])

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
    folium_static(m, height=520, width=950)

# --- 右側：站牌 (解決順行問題的核心) ---
with col2:
    st.markdown('<span class="mochiy-font side-title">🚉 選擇車站</span>', unsafe_allow_html=True)
    sel_st_full = st.selectbox("請選擇車站：", LRT_STATIONS, index=19) # 預設 C20 台鐵美術館
    
    # 從選單提取純關鍵字 (例如：從 "C20 台鐵美術館" 提取 "美術館")
    search_target = sel_st_full.split(" ")[1]
    # 特殊處理：API 中「台鐵美術館」與「美術館」可能有重疊，我們縮減關鍵字來增加抓取率
    if "美術館" in search_target: search_target = "美術館"

    if token:
        try:
            # 撈取所有站點的進站資訊
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", 
                                headers={'Authorization': f'Bearer {token}'}, timeout=10)
            if resp.status_code == 200:
                all_raw_data = resp.json()
                
                # 強制比對邏輯：找出所有符合名稱且預估時間不為空的資料
                matched_list = []
                for entry in all_raw_data:
                    api_station_name = entry.get('StationName', {}).get('Zh_tw', '')
                    # 只要 API 站名包含我們的目標關鍵字，就抓進來
                    if search_target in api_station_name and entry.get('EstimateTime') is not None:
                        matched_list.append(entry)
                
                if matched_list:
                    # 排序：優先顯示最快抵達的車
                    matched_list.sort(key=lambda x: x.get('EstimateTime', 0))
                    
                    for item in matched_list:
                        d_code = item.get('Direction')
                        d_text = "順行 (外圈)" if d_code == 0 else "逆行 (內圈)"
                        b_color = "#2e7d32" if d_code == 0 else "#1565c0"
                        est = int(item.get('EstimateTime'))
                        
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
                    st.info(f"⏳ 「{search_target}」目前雙向皆無預估資訊")
            else: st.warning("📡 伺服器忙碌，稍後重試")
        except: board_time = "連線重試中..."

st.markdown(f'<div style="color:gray; font-size:0.8em; margin-top:20px;">📍 最後同步：{map_time} (自動重新載入中)</div>', unsafe_allow_html=True)

time.sleep(30)
st.rerun()
