import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
import datetime
import pytz
import time
import base64
import os

# 1. 頁面配置
st.set_page_config(page_title="高雄輕軌監測", layout="wide")

# --- 強化版字體讀取邏輯 ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""

try:
    if os.path.exists(font_path):
        with open(font_path, "rb") as f:
            font_data = f.read()
        font_base64 = base64.b64encode(font_data).decode()
        font_css = f'''
        @font-face {{
            font-family: 'ZongYouFont';
            src: url(data:font/otf;base64,{font_base64}) format('opentype');
        }}
        .custom-title {{ font-family: 'ZongYouFont' !important; font-size: 42px; color: #2e7d32; margin-bottom: 10px; }}
        .custom-subtitle {{ font-family: 'ZongYouFont' !important; font-size: 24px; color: #333; margin-bottom: 10px; }}
        '''
    else:
        # 找不到檔案時的後備樣式
        font_css = '''
        .custom-title { font-family: sans-serif; font-size: 42px; color: #2e7d32; }
        .custom-subtitle { font-family: sans-serif; font-size: 24px; color: #333; }
        '''
except Exception as e:
    # 發生任何讀取錯誤時不中斷程式
    font_css = f"/* 字體讀取失敗: {str(e)} */"

# 2. 注入 CSS 樣式
st.markdown(f'''
<link href="https://fonts.googleapis.com/css2?family=Kiwi+Maru:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    {font_css}
    html, body, [data-testid="stAppViewContainer"], p, div, span, label {{
        font-family: 'Kiwi Maru', serif;
    }}
    .info-box {{ background-color: #e3f2fd; border: 1px solid #90caf9; padding: 10px 15px; border-radius: 8px; margin-bottom: 10px; color: #0d47a1; font-size: 0.85em; }}
    .legend-box {{ background-color: #f9f9f9; border: 1px solid #ddd; padding: 5px 12px; border-radius: 6px; margin-bottom: 15px; font-size: 0.8em; }}
    .time-header {{ background-color: #2e7d32; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; display: inline-block; margin-bottom: 3px; }}
    .arrival-card {{ background-color: #ffffff; border-radius: 8px; padding: 8px 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 6px; border-left: 5px solid #2e7d32; line-height: 1.1; }}
    .time-normal {{ font-size: 1.2em; color: #4D0000; margin: 0; font-weight: bold; }}
    .time-urgent {{ font-size: 1.2em; color: #FF0000; margin: 0; font-weight: bold; }}
    .update-time {{ font-size: 0.75em; color: #666; margin-top: 2px; }}
    div[data-baseweb="select"] input {{ readonly: true !important; caret-color: transparent !important; }}
</style>
''', unsafe_allow_html=True)

# --- 以下維持原有的 API 抓取邏輯 (省略重複部分以節省篇幅) ---
# ... (請貼回您原有的 API Token、地圖與車站顯示程式碼) ...
