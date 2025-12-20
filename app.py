import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與字體注入
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+P+One&family=Kiwi+Maru:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    .mochiy-font {
        font-family: 'Mochiy Pop P One', sans-serif !important;
        font-weight: normal !important;
        color: #2e7d32;
    }
    .main-title { font-size: 52px; margin-bottom: 25px; }
    .side-title { font-size: 26px; margin-bottom: 15px; display: block; }
    
    html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, div, span, label, .stSelectbox {
        font-family: 'Kiwi Maru', serif !important;
        font-weight: normal !important;
    }

    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: #0d47a1; }
    .legend-box { background-color: #f5f5f5; border: 1px solid #ddd; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.95em; }

    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 18px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 12px; 
    }
    .dir-tag {
        display: inline-block; padding: 3px 10px; border-radius: 5px; 
        font-size: 0.85em; margin-bottom: 8px; color: white;
    }
    /* 抵達時間顏色：#4D0000 (一般), #FF0000 (即將抵達), 取消粗體 */
    .time-normal { font-size: 1.6em; color: #4D0000; font-weight: normal !important; }
    .time-urgent { font-size: 1.6em; color: #FF0000; font-weight: normal !important; }
</style>
''', unsafe_allow_html=True)

# 2. 基本函數
LRT_STATIONS = ["籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"]

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei'))

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- UI ---
st.markdown('<div class="mochiy-font main-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="info-box">💡 <b>系統提示：</b> 已強化順逆雙向掃描邏輯，解決順行資料缺失問題。</div>', unsafe_allow_html=True)
st.markdown('<div class="legend-box">📍 <b>圖例：</b> <span style="color:#2e7d32;">● 順行 (外圈)</span> | <span style="color:#1565c0;">● 逆行 (內圈)</span></div>', unsafe_allow_html=True)

token = get_token()
map_time, board_time = "讀取中...", "讀取中..."
col1, col2 = st.columns([7.5, 2.5])

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
            map_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
        except: map_time = "失敗"
    folium_static(m, height=600, width=1000)

with col2:
    st.markdown('<span class="mochiy-font side-title">📊 站牌即時資訊</span>', unsafe_allow_html=True)
    sel_st = st.selectbox("選擇查詢車站：", LRT_STATIONS)
    
    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", 
                                headers={'Authorization': f'Bearer {token}'}, timeout=10)
            if resp.status_code == 200:
                all_data = resp.json()
                search_key = "美術館" if "美術館" in sel_st else sel_st
                # 強化過濾邏輯：確保 Direction 0 與 1 同時受檢
                valid_data = [b for b in all_data if search_key in b.get('StationName', {}).get('Zh_tw', '') and b.get('EstimateTime') is not None]
                
                if valid_data:
                    # 排序：先看時間
                    valid_data.sort(key=lambda x: x.get('EstimateTime', 0))
                    for item in valid_data:
                        d_code = item.get('Direction')
                        d_text = "順行 (外圈)" if d_code == 0 else "逆行 (內圈)"
                        b_color = "#2e7d32" if d_code == 0 else "#1565c0"
                        est = int(item.get('EstimateTime'))
                        
                        # 顏色邏輯：≤ 2分用紅色，其餘用深褐色
                        t_class = "time-urgent" if est <= 2 else "time-normal"
                        t_text = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                        
                        st.markdown(f'''
                        <div class="arrival-card" style="border-left: 10px solid {b_color};">
                            <div class="dir-tag" style="background-color:{b_color};">{d_text}</div>
                            <div class="{t_class}">狀態：{t_text}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                    board_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    st.info(f"⏳ 站點「{sel_st}」目前暫無預估列車")
            else: st.error("API 回應異常")
        except: board_time = "讀取失敗"

st.markdown(f'<hr><div style="color:gray; font-size:0.85em;">📍 地圖更新：{map_time} | 🕒 站牌更新：{board_time}</div>', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
