# --- 字體載入與全域 CSS ---
font_path = "ZONGYOOOOOOU1.otf"
font_css = ""
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
    except: pass

st.markdown(f'''
<style>
    /* 載入具有多種原生字重的圓體 M PLUS Rounded 1c */
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@300;400;500;700;800&display=swap');
    
    {font_css}

    /* 強制全域使用圓體並設定原生字重 (Medium 500) */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], 
    [data-testid="stMarkdownContainer"], p, span, div, select, button, label {{
        font-family: 'M PLUS Rounded 1c', sans-serif !important;
        font-weight: 500 !important;
    }}

    /* 針對特定提示框調整字重以利閱讀 */
    .stAlert p {{
        font-weight: 700 !important;
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

    /* 底部區塊比例 */
    .info-box {{ background-color: #161b22; border-radius: 10px; padding: 15px; margin-top: 15px; border: 1px solid #30363d; font-size: 0.9em; }}
    .update-box {{ background-color: #0d1117; border-radius: 8px; padding: 12px; font-size: 0.85em; color: #8b949e; line-height: 1.6; border: 1px solid #21262d; margin-top: 10px; }}
    
    @media (max-width: 768px) {{ .custom-title {{ font-size: 32px; }} }}
</style>
''', unsafe_allow_html=True)
