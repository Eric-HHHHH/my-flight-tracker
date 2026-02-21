import streamlit as st
import pandas as pd
import time
from datetime import datetime
from FlightRadar24 import FlightRadar24API

st.set_page_config(page_title="Flight Radar Dashboard", layout="wide")
fr_api = FlightRadar24API()

def get_flight_status(flight_no):
    try:
        # 搜尋航班，FlightRadar24 的搜尋非常精準
        flights = fr_api.get_flights(flight_number=flight_no)
        
        if not flights:
            return {"航班": flight_no, "狀態": "🔍 未起飛或無資訊", "預計抵達": "-", "最後更新": datetime.now().strftime("%H:%M:%S")}
        
        # 取得最相關的一個航班資訊
        flight = flights[0]
        details = fr_api.get_flight_details(flight)
        
        # 解析狀態與抵達時間
        status_text = details.get('status', {}).get('text', '未知')
        # 取得預計抵達時間 (通常為 Unix Timestamp，轉換為當地時間)
        eta_ts = details.get('time', {}).get('estimated', {}).get('arrival')
        if eta_ts:
            eta = datetime.fromtimestamp(eta_ts).strftime("%H:%M")
        else:
            eta = "確認中"

        # 判斷有無延誤 (簡單邏輯判斷)
        if "Delayed" in status_text:
            status = f"⚠️ {status_text}"
        else:
            status = f"✅ {status_text}"

        return {
            "航班": flight_no, 
            "狀態": status, 
            "預計抵達": eta, 
            "最後更新": datetime.now().strftime("%H:%M:%S")
        }
    except Exception:
        return {"航班": flight_no, "狀態": "🔌 連線異常", "預計抵達": "-", "最後更新": datetime.now().strftime("%H:%M:%S")}

# --- UI 介面 ---
st.title("✈️ 專業版航班監控 Dashboard")

if "run" not in st.session_state: st.session_state.run = False

with st.sidebar:
    st.header("控制台")
    # 預設放入 Eric 常用的航班編號或示範編號
    inputs = st.text_area("航班編號 (每行一個)", "CI705\nBR225\nBR281").split('\n')
    flights_list = [f.strip().upper() for f in inputs if f.strip()][:10]
    
    col1, col2 = st.columns(2)
    if col1.button("🚀 開始監控"): st.session_state.run = True
    if col2.button("🛑 停止"): st.session_state.run = False
    
    st.info(f"當前位置：菲律賓宿霧\n自動更新頻率：10 分鐘")

# --- 執行監控 ---
placeholder = st.empty()
if st.session_state.run:
    while st.session_state.run:
        with st.spinner("正在同步全球航班數據..."):
            data = [get_flight_status(f) for f in flights_list]
            df = pd.DataFrame(data)
            
        with placeholder.container():
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.success(f"數據同步完成。下一次更新時間：{datetime.now().strftime('%H:%M:%S')} (10分鐘後)")
        
        # 倒數計時並允許隨時暫停
        for _ in range(600):
            if not st.session_state.run: break
            time.sleep(1)
        if st.session_state.run:
            st.rerun()
else:
    st.info("請點擊左側「開始監控」以獲取即時數據。")
