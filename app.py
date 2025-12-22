import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time
import base64
import os  # 👈 這裡是重點喔！我們邀請 os 專員進來幫忙檢查字體檔案

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

# --- 時間與營運邏輯 ---
tz = pytz.timezone('Asia/Taipei')
now = datetime.datetime.now(tz)
is_running = (now.hour > 6 or (now.hour == 6 and now.minute >= 30)) and (now.hour < 22 or (now.hour == 22 and now.minute <= 30))

# --- 字體載入與全域 CSS (這裡已經幫你準備好漂亮的圓體囉) ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""

# 這裡是在溫柔地確認你有沒有把自製字體放進資料夾裡
if os.path.exists(font_path):
    try:
        with open(font_path, "rb") as f:
            font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode()
        font_css = f'''
        @font-face {{ 
            font-family: 'ZongYouFont'; 
            src: url(data:font/otf;base64,{font_base64}) format('opentype'); 
        }}
        .custom-title {{ 
            font-family: 'ZongYouFont' !important; 
            font-size: 52px; 
            color: #a5d6a7; 
            text-align: center; 
            margin-bottom: 12px; 
            white-space: nowrap; 
        }}
        .credit-text {{ 
            font-family: 'ZongYouFont' !important; 
            font-size: 16px; 
            color: #888; 
            text-align: center; 
            margin-bottom: 25px; 
            letter-spacing: 2px; 
        }}
        .st-label-zong {{ 
            font-family: 'ZongYouFont' !important; 
            font-size: 26px; 
            color: #81c784; 
            margin-bottom: 10px; 
        }}
        .green-tag-box {{
            background-color: #2e7d32; 
            color: white !important; 
            font-size: 15px; 
            padding: 2px 10px; 
            border-radius: 4px; 
            display: inline-block; 
            margin-bottom: 4px; 
            font-family: 'ZongYouFont' !important;
        }}
        .arrival-text {{ 
            font-family: 'ZongYouFont' !important; 
            font-size: 32px !important; 
            line-height: 1.1; 
        }}
        '''
    except:
        # 如果讀取失敗，我們就靜靜地跳過，不要讓 App 崩潰
        pass

# 這裡幫你把全域字體換成了有「原生字重」的圓體，看起來會很滑順喔！
st.markdown(f'''
<style>
    /* 載入具有多種原生字重的圓體 M PLUS Rounded 1c */
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@300;400;500;700;800&display=swap');
    
    {font_css}

    /* 讓整個網頁的文字都變得圓滾滾的，而且使用中黑體 (500) 比較有質感 */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], 
    [data-testid="stMarkdownContainer"], p, span, div, select, button, label {{
        font-family: 'M PLUS Rounded 1c', sans-serif !important;
        font-weight: 500 !important;
    }}

    /* 纖薄卡片比例 */
    .paper-card {{ 
        background-color: #1a1d23; 
        border: 1px solid #2d333b; 
        border-left: 5px solid #4caf50;
        border-radius: 8px; 
        padding: 8px 15px; 
        margin-bottom: 8px;
    }}
    
    .urgent-red {{ color: #ff5252 !important; }}
    .calm-grey {{ color: #78909c !important; }}

    /* 下面這些是為了讓頁面排版更舒服 */
    .info-box {{ background-color: #161b22; border-radius: 10px; padding: 15px; margin-top: 15px; border: 1px solid #30363d; font-size: 0.9em; }}
    .update-box {{ background-color: #0d1117; border-radius: 8px; padding: 12px; font-size: 0.85em; color: #8b949e; line-height: 1.6; border: 1px solid #21262d; margin-top: 10px; }}
    
    @media (max-width: 768px) {{ .custom-title {{ font-size: 32px; }} }}
</style>
''', unsafe_allow_html=True)