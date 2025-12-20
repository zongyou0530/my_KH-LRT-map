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
    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 15px; border-radius: 10px; margin-bottom: 15px; color: #0d47a1; }
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 15px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 10px solid #ccc;
    }
    .dir-tag { display: inline-block; padding: 2px 8px; border-radius: 5px; font-size: 0.8em; margin-bottom: 5px; color: white; }
    .time-normal { font-size: 1.5em; color: #4D0000; }
    .time-urgent { font-size: 1.5em; color: #FF0000; }
</style>
''', unsafe_allow_html=True)

# 2. 車站代號與索引 (用於判斷順逆)
LRT_LIST = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C19", "C20", "C21A", "C21", "C22", "C23", "C24", "C25", "C26", "C27", "C28", "C29", "C30", "C31", "C32", "C33", "C34", "C35", "C36", "C37"]

STATION_MAP = {f"{id} {name}": id for id, name in zip(LRT_LIST, ["籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"])}

@st.cache_data(ttl=600)
def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

st.markdown('<div class="mochiy-font" style="font-size:42px;">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)
st.markdown('<div class="info-box">💡 <b>物理邏輯更新：</b> 即使 API 標籤錯誤，系統也會根據「目的地」與「車站序列」強制校正順逆行。</div>', unsafe_allow_html=True)

token = get_token()
col1, col2 = st.columns([7.2, 2.8])

with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token:
        try:
            live_pos = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}).json()
            for t in live_pos.get('LivePositions', []):
                d_color = 'green' if t.get('Direction') == 0 else 'blue'
                folium.Marker([t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']], icon=folium.Icon(color=d_color, icon='train', prefix='fa')).add_to(m)
        except: pass
    folium_static(m, height=520, width=950)

with col2:
    st.markdown('<span class="mochiy-font" style="font-size:24px;">🚉 選擇車站</span>', unsafe_allow_html=True)
    sel_st_label = st.selectbox("請選擇車站：", list(STATION_MAP.keys()), index=19)
    this_st_id = STATION_MAP[sel_st_label]

    if token:
        try:
            resp = requests.get("https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$format=JSON", headers={'Authorization': f'Bearer {token}'})
            all_data = resp.json()
            matched = [d for d in all_data if d.get('StationID') == this_st_id and d.get('EstimateTime') is not None]
            
            if matched:
                matched.sort(key=lambda x: x.get('EstimateTime', 999))
                for item in matched:
                    dest_name = item.get('DestinationStationName', {}).get('Zh_tw', '')
                    dest_id = item.get('DestinationStationID', '')
                    
                    # --- 物理判定邏輯 ---
                    # 1. 優先判定：目的地是籬仔內(C1)方向
                    if "籬仔內" in dest_name or dest_id == "C1":
                        is_clockwise = True
                    # 2. 次要判定：比較車站索引 (這站是 C20, 目的地是 C25 -> 遞增 = 順行)
                    else:
                        try:
                            this_idx = LRT_LIST.index(this_st_id)
                            dest_idx = LRT_LIST.index(dest_id)
                            is_clockwise = dest_idx > this_idx
                        except:
                            is_clockwise = False # 預防 API 資料殘缺

                    d_label = "順行 (外圈)" if is_clockwise else "逆行 (內圈)"
                    d_color = "#2e7d32" if is_clockwise else "#1565c0"
                    
                    est = int(item.get('EstimateTime', 0))
                    t_style = "time-urgent" if est <= 2 else "time-normal"
                    t_msg = "即時進站" if est <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card" style="border-left-color: {d_color};">
                        <div class="dir-tag" style="background-color: {d_color};">{d_label}</div>
                        <div class="{t_style}">狀態：{t_msg}</div>
                        <div style="font-size:0.8em; color:gray;">下一站往：{dest_name}</div>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("⌛ 暫無列車資訊")
        except: st.error("📡 讀取失敗")

time.sleep(30)
st.rerun()
