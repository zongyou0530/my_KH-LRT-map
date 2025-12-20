import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與「雙重字體」注入
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+P+One&family=Kiwi+Maru:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    /* 標題：Mochiy Pop P One (不加粗) */
    .mochiy-font {
        font-family: 'Mochiy Pop P One', sans-serif !important;
        font-weight: normal !important;
        color: #1a237e;
    }
    
    /* 內文：Kiwi Maru */
    html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, div, span, label, .stSelectbox {
        font-family: 'Kiwi Maru', serif !important;
    }

    .main-title { font-size: 42px; margin-bottom: 20px; }
    .side-title { font-size: 24px; margin-bottom: 15px; display: block; }
    
    /* 對話框樣式 */
    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 12px; border-radius: 10px; margin-bottom: 10px; }
    .guide-box { background-color: #f1f8e9; border: 1px solid #c5e1a5; padding: 12px; border-radius: 10px; margin-bottom: 25px; }
    
    /* 站牌卡片 */
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 18px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 12px; border-left: 8px solid #2e7d32;
    }
    .status-text { font-size: 1.5em; font-weight: bold; color: #d32f2f; }
</style>
''', unsafe_allow_html=True)

# 2. 基本資料
LRT_STATIONS = ["籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"]

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei'))

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- UI 開始 ---
st.markdown('<div class="mochiy-font main-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)

st.markdown('<div class="info-box">💡 系統提示：內文已切換為 Kiwi Maru 字體，並嘗試強化美術館站點匹配。</div>', unsafe_allow_html=True)
st.markdown('<div class="guide-box">🎮 操作指南：點擊地圖上的列車圖標可查看行駛資訊。</div>', unsafe_allow_html=True)

token = get_token()
map_time = "讀取中..."
board_time = "讀取中..."

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
                pop_html = f"<div style='font-family: Kiwi Maru;'>方向：{d_name}<br>同步時間：{get_now_tw().strftime('%H:%M:%S')}</div>"
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(pop_html, max_width=150),
                    icon=folium.Icon(color='red' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
            map_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
        except: map_time = "地圖資料獲取失敗"
    folium_static(m)

# --- 右側：站牌 ---
with col2:
    st.markdown('<span class="mochiy-font side-title">📊 站牌即時資訊</span>', unsafe_allow_html=True)
    sel_st = st.selectbox("選擇查詢車站：", LRT_STATIONS)
    
    if token:
        try:
            all_board_url = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON"
            resp = requests.get(all_board_url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
            
            if resp.status_code == 200:
                all_data = resp.json()
                
                # 針對「美術館」這類容易出錯的站名做關鍵字匹配
                search_key = "美術館" if "美術館" in sel_st else sel_st
                valid_data = [b for b in all_data if search_key in b.get('StationName', {}).get('Zh_tw', '') and b.get('EstimateTime') is not None]
                
                if valid_data:
                    for item in valid_data:
                        dest = item.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                        est = item.get('EstimateTime')
                        status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                        
                        st.markdown(f'''
                        <div class="arrival-card">
                            <div style="font-size:0.9em; color:#666;">往 {dest}</div>
                            <b>狀態：</b><span class="status-text">{status}</span>
                        </div>
                        ''', unsafe_allow_html=True)
                    board_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    st.info(f"⏳ 站點「{sel_st}」目前暫無預估列車")
                    board_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
            else:
                st.error("站牌資料暫時無法讀取")
        except:
            board_time = "讀取失敗"

# 底部兩行更新時間
st.markdown(f'''
<hr style="margin-top:30px;">
<div style="color:gray; font-size:0.85em; line-height:1.8;">
    📍 地圖列車位置最後更新時間：{map_time}<br>
    🕒 站牌到站資訊最後更新時間：{board_time}
</div>
''', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
