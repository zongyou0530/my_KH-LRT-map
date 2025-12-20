import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測 V5.0", layout="wide")

st.markdown('''
<style>
    .arrival-card { 
        background-color: #f8f9fa; border-radius: 8px; padding: 15px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 12px; border-left: 6px solid #2e7d32; 
    }
    .status-text { font-size: 1.3em; font-weight: bold; color: #d32f2f; }
    .update-footer { font-size: 0.85em; color: #777; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }
</style>
''', unsafe_allow_html=True)

# 2. 全線 38 站清單 (供查詢使用)
ALL_LRT_STATIONS = [
    "籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", 
    "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", 
    "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", 
    "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", 
    "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"
]

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')

def get_token():
    try:
        data = {
            'grant_type': 'client_credentials', 
            'client_id': st.secrets["TDX_CLIENT_ID"], 
            'client_secret': st.secrets["TDX_CLIENT_SECRET"]
        }
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- 資料初始化 ---
token = get_token()
st.title("🚂 高雄輕軌即時位置監測")

col1, col2 = st.columns([7, 3])

# --- 左側：即時地圖 ---
with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    
    if token:
        try:
            # 抓取即時位置
            live_url = 'https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON'
            live_res = requests.get(live_url, headers={'Authorization': f'Bearer {token}'}, timeout=5)
            trains = live_res.json().get('LivePositions', [])
            
            for t in trains:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                dir_code = t.get('Direction', 0)
                dir_name = "順行 (外圈)" if dir_code == 0 else "逆行 (內圈)"
                train_no = t.get('TrainNo', 'N/A')
                
                folium.Marker(
                    [lat, lon],
                    popup=f"<b>列車編號:</b> {train_no}<br><b>方向:</b> {dir_name}",
                    tooltip=f"車號: {train_no}",
                    icon=folium.Icon(color='red' if dir_code == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except:
            st.error("地圖資料獲取失敗")
    
    folium_static(m)

# --- 右側：站牌即時資訊 (核心修正版) ---
with col2:
    st.subheader("📊 站牌即時資訊")
    sel_station = st.selectbox("選擇查詢車站：", ALL_LRT_STATIONS)
    
    if token:
        try:
            # 關鍵修正：移除 $top=30，改用過濾器精準定位單站
            board_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=StationName/Zh_tw eq '{sel_station}'&$format=JSON"
            board_res = requests.get(board_url, headers={'Authorization': f'Bearer {token}'}, timeout=5)
            board_data = board_res.json()
            
            # 雙重過濾：確保資料存在且有「預估時間」
            valid_list = [i for i in board_data if i.get('EstimateTime') is not None]
            
            if valid_list:
                for item in valid_list:
                    dest = item.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                    est_time = item.get('EstimateTime')
                    
                    # 判斷進站狀態
                    status_text = "即時進站" if int(est_time) <= 1 else f"約 {est_time} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card">
                        <small style="color:gray">開往 {dest}</small><br>
                        <b>狀態：</b><span class="status-text">{status_text}</span>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info(f"⏳ 目前「{sel_station}」無預估進站列車")
                
        except Exception as e:
            st.warning("站牌資訊暫時無法讀取")

# 底部資訊欄
st.markdown(f'''
<div class="update-footer">
    🕒 系統最後同步時間：{get_now_tw()} (自動每 30 秒更新一次)
</div>
''', unsafe_allow_html=True)

# 5. 自動刷新
import time
time.sleep(30)
st.rerun()
