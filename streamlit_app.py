import streamlit as st
import pandas as pd
import time
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

st.set_page_config(page_title="Flight Tracker", layout="wide")

def get_flight_data(flight_no):
    # 模擬更真實的瀏覽器標頭，並指定語言為台灣繁體
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    url = f"https://www.google.com/search?q={flight_no}+flight+status&hl=zh-TW"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {"航班": flight_no, "狀態": "❌ 請求被阻擋", "抵達時間": "-", "最後更新": datetime.now().strftime("%H:%M:%S")}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        page_text = soup.get_text()
        
        # 1. 偵測狀態 (加強關鍵字庫)
        status = "未知"
        if any(word in page_text for word in ["準時", "On time", "Scheduled"]):
            status = "✅ 準時"
        elif any(word in page_text for word in ["延誤", "Delay"]):
            status = "⚠️ 延誤"
        elif any(word in page_text for word in ["已抵達", "Arrived", "Landed"]):
            status = "🏁 已抵達"
        elif any(word in page_text for word in ["取消", "Cancelled"]):
            status = "🚫 已取消"
        else:
            status = "🔍 搜尋中/無資訊"

        # 2. 擷取抵達時間 (使用 Regex 尋找 上午/下午 XX:XX 格式)
        # 針對 Google 搜尋結果頁面的時間格式進行匹配
        time_match = re.search(r'([上下]午\s*\d{1,2}:\d{2})', page_text)
        arrival = time_match.group(0) if time_match else "請點進網頁確認"
        
        return {
            "航班": flight_no, 
            "狀態": status, 
            "預計抵達": arrival,
            "最後更新": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        return {"航班": flight_no, "狀態": "🔌 連線錯誤", "預計抵達": "-", "最後更新": datetime.now().strftime("%H:%M:%S")}

# --- UI 介面 ---
st.title("✈️ 實時航班監控 Dashboard")

if "run" not in st.session_state: st.session_state.run = False

with st.sidebar:
    st.header("設定")
    inputs = st.text_area("輸入航班 (每行一個)", "CI705\nBR225\nBR281").split('\n')
    flights = [f.strip().upper() for f in inputs if f.strip()][:10]
    
    col1, col2 = st.columns(2)
    if col1.button("▶️ Start"): st.session_state.run = True
    if col2.button("⏸️ Pause"): st.session_state.run = False
    
    st.divider()
    st.write(f"目前監控中: {len(flights)} 個航班")

# --- 執行迴圈 ---
placeholder = st.empty()
if st.session_state.run:
    while st.session_state.run:
        with st.spinner("更新數據中..."):
            data = [get_flight_data(f) for f in flights]
            df = pd.DataFrame(data)
            
        with placeholder.container():
            # 使用更美觀的 Dataframe 顯示
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"🔄 自動更新中... 每 10 分鐘同步一次。上次同步：{datetime.now().strftime('%H:%M:%S')}")
        
        # 倒數 600 秒
        for _ in range(600):
            if not st.session_state.run: break
            time.sleep(1)
        st.rerun()
else:
    st.info("請點擊左側 Start 開始監控。目前顯示最後一次抓取的數據。")
