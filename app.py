import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與強制樣式
st.set_page_config(page_title="高雄輕軌監測 V6.0", layout="wide")

# 強制套用您要求的字體與排版樣式
st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&display=swap" rel="stylesheet">
<style>
    /* 全域字體設定 */
    html, body, [data-testid="stAppViewContainer"], .stText, p, div {
        font-family: "Zen Maru Gothic", sans-serif !important;
    }
    /* 看板卡片美化 */
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 18px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 15px; 
        border-left: 8px solid #2e7d32; line-height: 1.6;
    }
    .status-text { font-size: 1.4em; font-weight: 900; color: #d32f2f; }
    .dest-label { color: #555; font-weight: bold; font-size: 0.9em; }
    /* 頂部圖例區 */
    .info-header {
        background-color: #e3f2fd; border: 1px solid #90caf9; 
        padding: 12px; border-radius: 10px; margin-bottom: 20px;
    }
</style>
''', unsafe_allow_html=True)

# 2. 車站資料
ALL_STATIONS = [
    "籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", 
    "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", 
    "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", 
    "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", 
    "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"
]

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')

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

# --- 初始化 ---
token = get_token()
st.title("🚂 高雄輕軌即時位置監測")

# 頂部狀態列與圖例
st.markdown(f'''
<div class="info-header">
    📍 <b>圖例說明：</b> 🔴 順行 (外圈) | 🔵 逆行 (內圈) | 💡 點擊列車可查看詳細編號<br>
    ✅ <b>系統提示：</b> 已修正 API 解析邏輯，並同步台鐵美術館、愛河之心等站點資料。
</div>
''', unsafe_allow_html=True)

col1, col2 = st.columns([7, 3])

# --- 左側：即時地圖 ---
with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13, tiles="CartoDB positron")
    
    if token:
        try:
            live_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', 
                                    headers={'Authorization': f'Bearer {token}'}, timeout=5)
            trains = live_res.json().get('LivePositions', [])
            
            for t in trains:
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                dir_name = "順行 (外圈)" if t.get('Direction') == 0 else "逆行 (內圈)"
                train_id = t.get('TrainNo', '未知')
                
                # 彈出對話框排版修復
                pop_content = f"""
                <div style='font-family: "Zen Maru Gothic", sans-serif; width:150px;'>
                    <b style='color:#2c3e50;'>列車資訊</b><hr style='margin:5px 0;'>
                    編號: <b>{train_id}</b><br>
                    方向: {dir_name}
                </div>
                """
                
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(pop_content, max_width=200),
                    tooltip=f"列車 {train_id}",
                    icon=folium.Icon(color='red' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m)

# --- 右側：站牌即時資訊 (核心邏輯升級) ---
with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢車站：", ALL_STATIONS)
    
    if token:
        try:
            # 針對特殊站點（如台鐵美術館、愛河之心）進行過濾優化
            board_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=contains(StationName/Zh_tw, '{sel_st}')&$format=JSON"
            board_data = requests.get(board_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json()
            
            # 嚴格過濾掉 EstimateTime 為 None 的資料
            valid_list = [i for i in board_data if i.get('EstimateTime') is not None]
            
            if valid_list:
                for item in valid_list:
                    dest_name = item.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                    est_val = item.get('EstimateTime')
                    status_str = "即時進站" if int(est_val) <= 1 else f"約 {est_val} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card">
                        <div class="dest-label">🎯 開往 {dest_name}</div>
                        <b>狀態：</b><span class="status-text">{status_str}</span>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info(f"⏳ 目前「{sel_st}」無列車預估資訊")
        except:
            st.error("站牌資料讀取中...")

# 底部自動刷新標記
st.markdown(f'''<div style="color:#888; font-size:0.8em; margin-top:20px;">最後更新：{get_now_tw()} | 每 30 秒自動同步最新 API 數據</div>''', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
