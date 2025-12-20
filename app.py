import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與雙字體注入
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+P+One&family=Kiwi+Maru:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    /* 標題：Mochiy Pop P One, 深綠色, 48px, 不加粗 */
    .mochiy-font {
        font-family: 'Mochiy Pop P One', sans-serif !important;
        font-weight: normal !important;
        color: #2e7d32; /* 改為深綠色 */
    }
    .main-title { font-size: 48px; margin-bottom: 20px; }
    .side-title { font-size: 26px; margin-bottom: 15px; display: block; }
    
    /* 內文：Kiwi Maru */
    html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, div, span, label, .stSelectbox {
        font-family: 'Kiwi Maru', serif !important;
    }

    /* 對話框與卡片樣式 */
    .info-box { background-color: #e8f5e9; border: 1px solid #c8e6c9; padding: 12px; border-radius: 10px; margin-bottom: 10px; }
    .guide-box { background-color: #f1f8e9; border: 1px solid #c5e1a5; padding: 12px; border-radius: 10px; margin-bottom: 25px; }
    
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 18px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 12px; 
        border-left: 10px solid #2e7d32;
    }
    .dir-tag {
        display: inline-block; padding: 2px 8px; border-radius: 4px; 
        font-size: 0.8em; margin-bottom: 5px; color: white;
    }
    .status-text { font-size: 1.6em; font-weight: bold; color: #d32f2f; }
</style>
''', unsafe_allow_html=True)

# 2. 資料處理函數
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

st.markdown('<div class="info-box">✅ <b>系統更新：</b> 標題已改為深綠色並加大，進站資訊現已標註「順行/逆行」。</div>', unsafe_allow_html=True)

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
                    [lat, lon],
                    popup=folium.Popup(pop_html, max_width=150),
                    icon=folium.Icon(color='green' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
            map_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
        except: map_time = "地圖資料獲取失敗"
    folium_static(m)

# --- 右側：站牌 (強化方向辨識) ---
with col2:
    st.markdown('<span class="mochiy-font side-title">📊 站牌即時資訊</span>', unsafe_allow_html=True)
    sel_st = st.selectbox("選擇查詢車站：", LRT_STATIONS)
    
    if token:
        try:
            all_board_url = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON"
            resp = requests.get(all_board_url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
            
            if resp.status_code == 200:
                all_data = resp.json()
                search_key = "美術館" if "美術館" in sel_st else sel_st
                valid_data = [b for b in all_data if search_key in b.get('StationName', {}).get('Zh_tw', '') and b.get('EstimateTime') is not None]
                
                if valid_data:
                    # 排序：先按方向，再按時間
                    valid_data.sort(key=lambda x: (x.get('Direction', 0), x.get('EstimateTime', 0)))
                    
                    for item in valid_data:
                        dir_code = item.get('Direction')
                        dir_text = "順行 (外圈)" if dir_code == 0 else "逆行 (內圈)"
                        bg_color = "#2e7d32" if dir_code == 0 else "#1565c0"
                        
                        est = item.get('EstimateTime')
                        status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                        
                        st.markdown(f'''
                        <div class="arrival-card">
                            <div class="dir-tag" style="background-color:{bg_color};">{dir_text}</div>
                            <div style="font-size:0.9em; color:#666;">終點站：籬仔內</div>
                            <b>狀態：</b><span class="status-text">{status}</span>
                        </div>
                        ''', unsafe_allow_html=True)
                    board_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    st.info(f"⏳ 站點「{sel_st}」目前暫無預估列車")
                    board_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
            else: st.error("資料抓取失敗")
        except: board_time = "讀取失敗"

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
