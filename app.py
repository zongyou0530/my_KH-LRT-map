import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與字體強制注入 (Mochiy Pop P One)
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Mochiy+Pop+P+One&display=swap" rel="stylesheet">
<style>
    /* 標題專用字體 */
    .super-title {
        font-family: 'Mochiy Pop P One', sans-serif !important;
        font-size: 42px !important;
        font-weight: bold !important;
        color: #1a237e;
        margin-top: -20px;
        margin-bottom: 20px;
    }
    
    /* 全域字體設定 */
    div, span, p, h1, h2, h3 {
        font-family: 'Mochiy Pop P One', sans-serif !important;
    }

    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 12px; border-radius: 10px; margin-bottom: 10px; }
    .guide-box { background-color: #f1f8e9; border: 1px solid #c5e1a5; padding: 12px; border-radius: 10px; margin-bottom: 25px; }
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 20px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 15px; border-left: 10px solid #2e7d32;
    }
    .status-text { font-size: 1.8em; font-weight: 900; color: #d32f2f; }
</style>
''', unsafe_allow_html=True)

# 2. 基本資料
LRT_STATIONS = ["籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"]

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei'))

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=10)
        return res.json().get('access_token')
    except Exception as e:
        return None

# --- UI 開始 ---
st.markdown('<div class="super-title">高雄輕軌即時位置監測</div>', unsafe_allow_html=True)

st.markdown('<div class="info-box">💡 <b>系統提示：</b> 已更新標題字體為 Mochiy Pop P One，並加強站牌 API 容錯。</div>', unsafe_allow_html=True)
st.markdown('<div class="guide-box">🎮 <b>操作指南：</b> 點擊地圖上的列車圖標可查看行駛資訊。</div>', unsafe_allow_html=True)

token = get_token()
map_time = "尚未更新"
board_time = "尚未更新"

col1, col2 = st.columns([7, 3])

# --- 左側：地圖 ---
with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token:
        try:
            live_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                                    headers={'Authorization': f'Bearer {token}'}, timeout=10).json()
            for t in live_res.get('LivePositions', []):
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                d_name = "順行 (外圈)" if t.get('Direction') == 0 else "逆行 (內圈)"
                pop_html = f"<b>方向：</b>{d_name}<br><b>同步時間：</b>{get_now_tw().strftime('%H:%M:%S')}"
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(pop_html, max_width=150),
                    icon=folium.Icon(color='red' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
            map_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
        except: map_time = "地圖資料獲取失敗"
    folium_static(m)

# --- 右側：站牌 (強化版) ---
with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢車站：", LRT_STATIONS)
    
    board_placeholder = st.empty()
    
    if token:
        try:
            # 改用 eq (等於) 進行精準匹配，增加 API 穩定性
            api_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationName/Zh_tw eq '{sel_st}'&$format=JSON"
            resp = requests.get(api_url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
            
            if resp.status_code == 200:
                boards = resp.json()
                valid_data = [b for b in boards if b.get('EstimateTime') is not None]
                
                with board_placeholder.container():
                    if valid_data:
                        for item in valid_data:
                            dest = item.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                            est = item.get('EstimateTime')
                            status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                            
                            st.markdown(f'''
                            <div class="arrival-card">
                                <div style="color:#5c6bc0; font-weight:bold;">往 {dest}</div>
                                <b>狀態：</b><span class="status-text">{status}</span>
                            </div>
                            ''', unsafe_allow_html=True)
                        board_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        st.warning(f"⏳ 站點「{sel_st}」目前暫無預估列車")
                        board_time = get_now_tw().strftime('%Y-%m-%d %H:%M:%S')
            else:
                board_placeholder.error("API 伺服器回應錯誤")
        except Exception as e:
            board_placeholder.error(f"站牌資訊讀取失敗，請檢查網路")
            board_time = "讀取失敗"

# 底部兩行更新時間
st.markdown(f'''
<hr>
<div style="color:gray; font-size:0.85em; line-height:1.6;">
    📍 地圖列車位置最後更新時間：{map_time}<br>
    🕒 站牌到站資訊最後更新時間：{board_time}
</div>
''', unsafe_allow_html=True)

# 自動重新整理
import time
time.sleep(30)
st.rerun()
