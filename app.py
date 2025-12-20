import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與進階樣式 (字體與排版)
st.set_page_config(page_title="高雄輕軌監測 V7.0", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700;900&display=swap" rel="stylesheet">
<style>
    /* 強制設定標題與全域字體 */
    [data-testid="stHeader"], .stMarkdown, h1, h2, h3, p, div, span {
        font-family: "Zen Maru Gothic", sans-serif !important;
    }
    h1 { color: #1a237e; font-weight: 900 !important; font-size: 2.5rem !important; }
    
    /* 站牌資訊卡片設計 */
    .arrival-card { 
        background-color: #ffffff; border-radius: 15px; padding: 20px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 15px; 
        border-left: 10px solid #2e7d32;
    }
    .status-text { font-size: 1.5em; font-weight: 900; color: #d32f2f; }
    .dest-info { color: #5c6bc0; font-weight: bold; margin-bottom: 5px; }
    
    /* 頂部圖例 */
    .legend-panel {
        background: linear-gradient(90deg, #e3f2fd 0%, #ffffff 100%);
        padding: 15px; border-radius: 12px; border: 1px solid #bbdefb; margin-bottom: 20px;
    }
</style>
''', unsafe_allow_html=True)

# 2. 完整 38 站清單與簡易座標 (用於繪製路線)
LRT_STATIONS = [
    "籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", 
    "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", 
    "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", 
    "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", 
    "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"
]

# 簡易路線座標 (精簡版，用於在地圖上連線)
ROUTE_PATH = [
    [22.5978, 120.3236], [22.5970, 120.3162], [22.5986, 120.3094], [22.6006, 120.3023], [22.5961, 120.3045],
    [22.6015, 120.3012], [22.6062, 120.3013], [22.6105, 120.2995], [22.6133, 120.2974], [22.6178, 120.2952],
    [22.6214, 120.2923], [22.6193, 120.2863], [22.6202, 120.2809], [22.6225, 120.2885], [22.6253, 120.2798],
    [22.6300, 120.2800], [22.6360, 120.2830], [22.6410, 120.2840], [22.6480, 120.2850], [22.6537, 120.2863],
    [22.6575, 120.2884], [22.6590, 120.2930], [22.6570, 120.2980], [22.6560, 120.3010], [22.6565, 120.3028],
    [22.6570, 120.3100], [22.6530, 120.3180], [22.6510, 120.3230], [22.6470, 120.3270], [22.6420, 120.3300],
    [22.6380, 120.3330], [22.6320, 120.3320], [22.6280, 120.3310], [22.6210, 120.3300], [22.6150, 120.3300],
    [22.6100, 120.3290], [22.6050, 120.3270], [22.6010, 120.3250], [22.5978, 120.3236]
]

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        return requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data).json().get('access_token')
    except: return None

# --- 開始渲染 ---
st.title("🚂 高雄輕軌即時位置監測")

st.markdown('''
<div class="legend-panel">
    📍 <b>即時圖例：</b> <span style="color:red">●</span> 順行 (外圈) | <span style="color:blue">●</span> 逆行 (內圈) | 🗺️ 已繪製全線軌道路線
</div>
''', unsafe_allow_html=True)

token = get_token()
col1, col2 = st.columns([7, 3])

# --- 左側：地圖與路線 ---
with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13, tiles="CartoDB positron")
    
    # 繪製輕軌路線 (PolyLine)
    folium.PolyLine(ROUTE_PATH, color="#2e7d32", weight=5, opacity=0.6).add_to(m)
    
    if token:
        try:
            live_data = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                                     headers={'Authorization': f'Bearer {token}'}).json().get('LivePositions', [])
            for t in live_data:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                d_name = "順行 (外圈)" if t.get('Direction') == 0 else "逆行 (內圈)"
                
                # 修復後的彈出視窗排版
                pop_html = f"""
                <div style='font-family: "Zen Maru Gothic", sans-serif; min-width:120px;'>
                    <b style='color:#1a237e; font-size:1.1em;'>列車 {t.get('TrainNo')}</b><br>
                    <hr style='margin:4px 0;'>
                    方向：{d_name}
                </div>
                """
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(pop_html, max_width=200),
                    tooltip=f"車號: {t.get('TrainNo')}",
                    icon=folium.Icon(color='red' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m)

# --- 右側：站牌 (修復顯示不出來的問題) ---
with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢車站：", LRT_STATIONS)
    
    if token:
        try:
            # 關鍵修正：針對站名使用 contains 以排除空白字元干擾，並確保全量抓取
            api_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=contains(StationName/Zh_tw, '{sel_st.strip()}')&$format=JSON"
            boards = requests.get(api_url, headers={'Authorization': f'Bearer {token}'}).json()
            
            # 排除沒有預估時間的無效數據
            valid_boards = [b for b in boards if b.get('EstimateTime') is not None]
            
            if valid_boards:
                for item in valid_boards:
                    dest = item.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                    est = item.get('EstimateTime')
                    status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card">
                        <div class="dest-info">🎯 開往 {dest}</div>
                        <b>狀態：</b><span class="status-text">{status}</span>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.warning(f"⏳ 「{sel_st}」目前暫無列車預估資訊")
        except:
            st.error("站牌資料載入失敗")

# 自動刷新
st.markdown(f'<div style="color:gray; font-size:0.8em; margin-top:20px;">更新時間：{datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)
import time
time.sleep(30)
st.rerun()
