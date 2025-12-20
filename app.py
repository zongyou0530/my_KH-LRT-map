import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time

# 1. 頁面配置與精簡化樣式
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+P+One&family=Kiwi+Maru:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    .mochiy-font { font-family: 'Mochiy Pop P One', sans-serif !important; color: #2e7d32; }
    html, body, [data-testid="stAppViewContainer"], p, div, span, label {
        font-family: 'Kiwi Maru', serif !important;
    }
    /* 藍色留言板 */
    .info-box { 
        background-color: #e3f2fd; border: 1px solid #90caf9; 
        padding: 10px 15px; border-radius: 8px; margin-bottom: 10px; color: #0d47a1; font-size: 0.9em;
    }
    /* 圖例說明 */
    .legend-box { 
        background-color: #f9f9f9; border: 1px solid #ddd; 
        padding: 5px 12px; border-radius: 6px; margin-bottom: 15px; font-size: 0.85em;
    }
    /* 小巧的綠背景標題 */
    .time-header {
        background-color: #2e7d32; color: white; padding: 3px 10px;
        border-radius: 4px; font-size: 0.85em; display: inline-block; margin-bottom: 5px;
    }
    /* 精緻卡片樣式 */
    .arrival-card { 
        background-color: #ffffff; border-radius: 8px; padding: 10px 15px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 8px;
        border-left: 6px solid #2e7d32; line-height: 1.2;
    }
    .time-normal { font-size: 1.3em; color: #4D0000; margin: 0; }
    .time-urgent { font-size: 1.3em; color: #FF0000; margin: 0; }
    
    /* 修正選單不跳鍵盤 */
    [data-baseweb="select"] input { readonly: true !important; }
</style>
''', unsafe_allow_html=True)

# 2. 車站資料
STATION_MAP = {
    "C1 籬仔內": "C1", "C2 凱旋瑞田": "C2", "C3 前鎮之星": "C3", "C4 凱旋中華": "C4", "C5 夢時代": "C5",
    "C6 經貿園區": "C6", "C7 軟體園區": "C7", "C8 高雄展覽館": "C8", "C9 旅運中心": "C9", "C10 光榮碼頭": "C10",
    "C11 真愛碼頭": "C11", "C12 駁二大義": "C12", "C13 駁二蓬萊": "C13", "C14 哈瑪星": "C14", "C15 壽山公園": "C15",
    "C16 文武聖殿": "C16", "C17 鼓山區公所": "C17", "C18 鼓山": "C18", "C19 馬卡道": "C19", "C20 台鐵美術館": "C20",
    "C21A 內維藝術中心": "C21A", "C21 美術館": "C21", "C22 聯合醫院": "C22", "C23 龍華國小": "C23", "C24 愛河之心": "C24",
    "C25 新上國小": "C25", "C26 灣仔內": "C26", "C27 鼎山街": "C27", "C28 高雄高工": "C28", "C29 樹德家商": "C29",
    "C30 科工館": "C30", "C31 聖功醫院": "C31", "C32 凱旋公園": "C32", "C33 衛生局": "C33", "C34 五權國小": "C34",
    "C35 凱旋武昌": "C35", "C36 凱旋二聖": "C36", "C37 輕軌機廠": "C37"
}

@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- UI 開始 ---
st.markdown('<div class="mochiy-font" style="font-size:36px;">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)

# 1. 藍色留言板
st.markdown('<div class="info-box">💡 系統提示：暫時無法解決順行逆行顯示問題 請自己通靈 反正有一個是對的（50%的機率🤣）。</div>', unsafe_allow_html=True)

# 2. 圖例說明
st.markdown('<div class="legend-box">📍 <b>地圖標示：</b> <span style="color:green;">● 順行</span> | <span style="color:blue;">● 逆行</span></div>', unsafe_allow_html=True)

token = get_token()
col1, col2 = st.columns([7, 3])

with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_pos.get('LivePositions', []):
                d_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], icon=folium.Icon(color=d_color, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=500, width=950)

with col2:
    st.markdown('<div class="mochiy-font" style="font-size:20px; margin-bottom:10px;">🚉 車站即時時刻表</div>', unsafe_allow_html=True)
    
    # 這裡使用單選按鈕(Radio)或是強制不跳鍵盤的 Selectbox
    sel_st_label = st.selectbox(
        "請選擇：", 
        list(STATION_MAP.keys()), 
        index=19, 
        label_visibility="collapsed"
    )
    target_id = STATION_MAP[sel_st_label]

    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", headers={'Authorization': f'Bearer {token}'})
            all_data = resp.json()
            matched = [d for d in all_data if d.get('StationID') == target_id and d.get('EstimateTime') is not None]
            
            if matched:
                matched.sort(key=lambda x: x.get('EstimateTime', 999))
                for item in matched:
                    est = int(item.get('EstimateTime', 0))
                    t_class = "time-urgent" if est <= 2 else "time-normal"
                    t_msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card">
                        <div class="time-header">輕軌預計抵達時間</div>
                        <div class="{t_class}">{t_msg}</div>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.write("⌛ 暫無列車資訊")
        except: st.error("📡 資料更新中")

time.sleep(30)
st.rerun()
