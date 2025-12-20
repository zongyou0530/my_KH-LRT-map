import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與字體強制設定
st.set_page_config(page_title="高雄輕軌即時監測", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700;900&display=swap" rel="stylesheet">
<style>
    /* 強制設定全域與標題字體 */
    html, body, [data-testid="stAppViewContainer"], .stMarkdown, h1, h2, h3 {
        font-family: "Zen Maru Gothic", sans-serif !important;
    }
    .main-title { color: #1a237e; font-size: 2.5em; font-weight: 900; margin-bottom: 20px; }
    .arrival-card { 
        background-color: #ffffff; border-radius: 10px; padding: 15px; 
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 12px; border-left: 8px solid #2e7d32;
    }
    .status-text { font-size: 1.3em; font-weight: 900; color: #d32f2f; }
</style>
''', unsafe_allow_html=True)

# 2. 車站清單
LRT_STATIONS = [
    "籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", 
    "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", 
    "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", 
    "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", 
    "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"
]

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- UI 渲染 ---
st.markdown('<div class="main-title">🚂 高雄輕軌即時位置監測</div>', unsafe_allow_html=True)

token = get_token()
col1, col2 = st.columns([7, 3])

# --- 左側：原始地圖 ---
with col1:
    # 回歸最原始的 OpenStreetMap 底圖，不加任何自繪線條以確保效能與準確
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    
    if token:
        try:
            live_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                                    headers={'Authorization': f'Bearer {token}'}, timeout=5)
            trains = live_res.json().get('LivePositions', [])
            for t in trains:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                d_name = "順行 (外圈)" if t.get('Direction') == 0 else "逆行 (內圈)"
                
                # 簡單清晰的 Popup 排版
                pop_html = f"<b>列車 {t.get('TrainNo')}</b><br>方向：{d_name}"
                
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(pop_html, max_width=150),
                    tooltip=f"車號: {t.get('TrainNo')}",
                    icon=folium.Icon(color='red' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m)

# --- 右側：站牌 (解決顯示不全問題) ---
with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢車站：", LRT_STATIONS)
    
    if token:
        try:
            # 關鍵：使用 contains 並移除可能存在的空格，增加匹配成功率
            clean_name = sel_st.strip()
            board_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=contains(StationName/Zh_tw, '{clean_name}')&$format=JSON"
            boards = requests.get(board_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json()
            
            # 過濾：只要有時間（EstimateTime）就顯示
            valid_data = [b for b in boards if b.get('EstimateTime') is not None]
            
            if valid_data:
                for item in valid_data:
                    dest = item.get('DestinationStationName', {}).get('Zh_tw', '終點站')
                    est = item.get('EstimateTime')
                    status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card">
                        <div style="color:#555;">往 {dest}</div>
                        <b>狀態：</b><span class="status-text">{status}</span>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info(f"⏳ 站點「{sel_st}」目前無預估進站列車")
        except:
            st.error("資料獲取失敗")

# 自動重新整理
st.markdown(f'<div style="color:gray; font-size:0.8em; margin-top:20px;">資料更新時間：{datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)
import time
time.sleep(30)
st.rerun()
