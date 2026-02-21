import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Flight Radar Dashboard", layout="wide")

# 強制設定為當地時區 (UTC+8)
TZ = ZoneInfo("Asia/Manila")

def get_flight_data(flight_no):
    # 使用 FlightRadar24 的內部輕量 API 端點
    url = f"https://api.flightradar24.com/common/v1/flight/list.json?query={flight_no}&fetchBy=flight&page=1&limit=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    current_time = datetime.now(TZ).strftime("%H:%M:%S")
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {"航班": flight_no, "狀態": "❌ 請求遭阻擋", "預計抵達": "-", "最後更新": current_time}
            
        data = res.json()
        # 解析 JSON 結構
        flights = data.get('result', {}).get('response', {}).get('data', [])
        
        if not flights:
            return {"航班": flight_no, "狀態": "🔍 查無近期航班", "預計抵達": "-", "最後更新": current_time}
        
        flight = flights[0]
        status_text = flight.get('status', {}).get('text', '未知')
        
        # 取得抵達時間戳記 (優先取預計 arrival，若無則取表定 arrival)
        time_data = flight.get('time', {})
        arr_ts = time_data.get('estimated', {}).get('arrival') or time_data.get('scheduled', {}).get('arrival')
        
        if arr_ts:
            # 將 Unix Timestamp 轉換為當地時間
            arr_time = datetime.fromtimestamp(arr_ts, TZ).strftime("%m-%d %H:%M")
        else:
            arr_time = "未知"
            
        # 標記延誤狀態
        if "Delayed" in status_text:
            status = f"⚠️ {status_text}"
        elif "Canceled" in status_text:
            status = f"🚫 {status_text}"
        else:
            status = f"✅ {status_text}"
            
        return {
            "航班": flight_no,
            "狀態": status,
            "預計抵達": arr_time,
            "最後更新": current_time
        }
        
    except Exception as e:
        return {"航班": flight_no, "狀態": "🔌 連線異常", "預計抵達": "-", "最後更新": current_time}

# --- UI 介面 ---
st.title("✈️ 專業版航班監控 Dashboard")

if "run" not in st.session_state: st.session_state.run = False

with st.sidebar:
    st.header("控制台")
    inputs = st.text_area("航班編號 (每行一個)", "CI705\nBR225\nBR281").split('\n')
    flights_list = [f.strip().upper() for f in inputs if f.strip()][:10]
    
    col1, col2 = st.columns(2)
    if col1.button("🚀 開始監控"): st.session_state.run = True
    if col2.button("🛑 停止"): st.session_state.run = False
    
    st.info("自動更新頻率：10 分鐘")

# --- 執行監控 ---
placeholder = st.empty()
if st.session_state.run:
    while st.session_state.run:
        with st.spinner("正在同步航班數據..."):
            data = [get_flight_data(f) for f in flights_list]
            df = pd.DataFrame(data)
            
        with placeholder.container():
            st.dataframe(df, use_container_width=True, hide_index=True)
            next_update = (datetime.now(TZ).timestamp() + 600)
            next_update_str = datetime.fromtimestamp(next_update, TZ).strftime('%H:%M:%S')
            st.success(f"數據同步完成。下一次更新時間：{next_update_str}")
        
        # 倒數 600 秒
        for _ in range(600):
            if not st.session_state.run: break
            time.sleep(1)
        if st.session_state.run:
            st.rerun()
else:
    st.info("請點擊左側「開始監控」以獲取即時數據。")
