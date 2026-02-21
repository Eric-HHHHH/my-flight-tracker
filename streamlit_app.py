import streamlit as st
import pandas as pd
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Flight Tracker", layout="wide")

# --- 輕量化抓取函數 ---
def get_flight_data(flight_no):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    url = f"https://www.google.com/search?q={flight_no}+flight+status&hl=zh-TW"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 尋找關鍵資訊 (Google 結構特徵)
        # 這裡會根據 Google 的結構嘗試抓取時間與狀態
        status = "偵測中"
        arrival = "搜尋中"
        
        # 簡單解析邏輯 (針對 Google 搜尋結果)
        text = soup.get_text()
        if "準時" in text: status = "✅ 準時"
        elif "延誤" in text: status = "⚠️ 延誤"
        elif "已抵達" in text: status = "🏁 已抵達"
        
        return {"航班": flight_no, "狀態": status, "最後更新": datetime.now().strftime("%H:%M:%S")}
    except:
        return {"航班": flight_no, "狀態": "連線超時", "最後更新": "-"}

# --- UI 介面 ---
st.title("✈️ 實時航班監控")

if "run" not in st.session_state: st.session_state.run = False

with st.sidebar:
    st.header("設定")
    inputs = st.text_area("輸入航班 (每行一個)", "CI705\nBR225").split('\n')
    flights = [f.strip().upper() for f in inputs if f.strip()][:10]
    
    col1, col2 = st.columns(2)
    if col1.button("▶️ Start"): st.session_state.run = True
    if col2.button("⏸️ Pause"): st.session_state.run = False

# --- 執行迴圈 ---
placeholder = st.empty()
if st.session_state.run:
    while st.session_state.run:
        data = [get_flight_data(f) for f in flights]
        df = pd.DataFrame(data)
        with placeholder.container():
            st.table(df)
            st.caption(f"下次自動更新：{datetime.now().strftime('%H:%M:%S')} (每10分鐘更新一次)")
        
        # 倒數 600 秒
        for _ in range(600):
            if not st.session_state.run: break
            time.sleep(1)
        st.rerun()
else:
    st.info("請點擊左側 Start 開始監控")
