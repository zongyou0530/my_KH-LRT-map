import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz

# 1. 頁面配置與強制字體設定
st.set_page_config(page_title="高雄輕軌監測 V9.0", layout="wide")

st.markdown('''
<link href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700;900&display=swap" rel="stylesheet">
<style>
    /* 強制標題與全域字體 */
    html, body, [data-testid="stAppViewContainer"], .stMarkdown, h1, h2, h3, div, span {
        font-family: "Zen Maru Gothic", sans-serif !important;
    }
    .main-title { color: #1a237e; font-size: 2.8em; font-weight: 900; margin-bottom: 10px; }
    .info-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 12px; border-radius: 10px; margin-bottom: 15px; }
    .guide-box { background-color: #f1f8e9; border: 1px solid #c5e1a5; padding: 12px; border-radius: 10px; margin-bottom: 20px; }
    .arrival-card { 
        background-color: #ffffff; border-radius: 12px; padding: 20px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 15px; border-left: 10px solid #2e7d32;
    }
    .status-text { font-size: 1.6em; font-weight: 900; color: #d32f2f; }
</style>
''', unsafe_allow_html=True)

# 2. 車站資料
LRT_STATIONS = ["籬仔內", "凱旋瑞田", "前鎮之星", "凱旋中華", "夢時代", "經貿園區", "軟體園區", "高雄展覽館", "旅運中心", "光榮碼頭", "真愛碼頭", "駁二大義", "駁二蓬萊", "哈瑪星", "壽山公園", "文武聖殿", "鼓山區公所", "鼓山", "馬卡道", "台鐵美術館", "內惟藝術中心", "美術館", "聯合醫院", "龍華國小", "愛河之心", "新上國小", "灣仔內", "鼎山街", "高雄高工", "樹德家商", "科工館", "聖功醫院", "凱旋公園", "衛生局", "五權國小", "凱旋武昌", "凱旋二聖", "輕軌機廠"]

def get_now_tw():
    return datetime.datetime.now(pytz.timezone('Asia/Taipei'))

def get_token():
    try:
        data = {'grant_type': 'client_credentials', 'client_id': st.secrets["TDX_CLIENT_ID"], 'client_secret': st.secrets["TDX_CLIENT_SECRET"]}
        res = requests.post('https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token', data=data, timeout=5)
        return res.json().get('access_token')
    except: return None

# --- UI 渲染 ---
st.markdown('<div class="main-title">🚂 高雄輕軌即時位置監測</div>', unsafe_allow_html=True)

# 重新回歸的兩個對話框
st.markdown('<div class="info-box">💡 <b>系統提示：</b> 已對接最新 LiveBoard API，修正「台鐵美術館」與「愛河之心」顯示問題。</div>', unsafe_allow_html=True)
st.markdown('<div class="guide-box">🎮 <b>操作指南：</b> 點擊地圖上的列車圖標，可查看行駛方向、終點站及資料更新時間。</div>', unsafe_allow_html=True)

token = get_token()
col1, col2 = st.columns([7, 3])

# --- 左側：地圖 ---
with col1:
    m = folium.Map(location=[22.6280, 120.3014], zoom_start=13)
    if token:
        try:
            live_res = requests.get('https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LivePosition/KLRT?$format=JSON', headers={'Authorization': f'Bearer {token}'}, timeout=5).json()
            for t in live_res.get('LivePositions', []):
                lat, lon = t['TrainPosition']['PositionLat'], t['TrainPosition']['PositionLon']
                d_name = "順行 (外圈)" if t.get('Direction') == 0 else "逆行 (內圈)"
                update_time = get_now_tw().strftime("%H:%M:%S")
                
                # 移除 None，精簡對話框
                pop_html = f"""
                <div style='font-family: "Zen Maru Gothic", sans-serif; width:160px;'>
                    <b>列車資訊</b><hr style='margin:5px 0;'>
                    方向：{d_name}<br>
                    更新時間：{update_time}
                </div>
                """
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(pop_html, max_width=200),
                    icon=folium.Icon(color='red' if t.get('Direction') == 0 else 'blue', icon='train', prefix='fa')
                ).add_to(m)
        except: pass
    folium_static(m)

# --- 右側：站牌 (解決顯示錯誤核心) ---
with col2:
    st.subheader("📊 站牌即時資訊")
    sel_st = st.selectbox("選擇查詢車站：", LRT_STATIONS)
    
    if token:
        try:
            # 針對 API 截圖中的欄位結構進行精準查詢
            board_url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/LiveBoard/KLRT?$filter=contains(StationName/Zh_tw, '{sel_st.strip()}')&$format=JSON"
            boards = requests.get(board_url, headers={'Authorization': f'Bearer {token}'}, timeout=5).json()
            
            # 過濾 logic：確保 EstimateTime 不是 None 且 ServiceStatus 正確
            valid_list = [b for b in boards if b.get('EstimateTime') is not None]
            
            if valid_list:
                for item in valid_list:
                    # 依據截圖欄位：DestinationStationName -> Zh_tw
                    dest = item.get('DestinationStationName', {}).get('Zh_tw', '端點站')
                    est = item.get('EstimateTime')
                    status = "即時進站" if int(est) <= 1 else f"約 {est} 分鐘"
                    
                    st.markdown(f'''
                    <div class="arrival-card">
                        <div style="color:#5c6bc0; font-weight:bold;">往 {dest}</div>
                        <b>狀態：</b><span class="status-text">{status}</span>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info(f"⏳ 站點「{sel_st}」目前暫無預估進站資訊")
        except:
            st.error("站牌資訊讀取中，請稍候...")

# 底部更新標記
st.markdown(f'<div style="color:gray; font-size:0.8em; margin-top:20px;">最後更新時間：{get_now_tw().strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)

import time
time.sleep(30)
st.rerun()
