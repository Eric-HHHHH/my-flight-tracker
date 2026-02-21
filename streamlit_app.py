import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Flight Radar Dashboard", layout="wide")

# 設定宿霧當地時區 (UTC+8)
TZ = ZoneInfo("Asia/Manila")

def get_flight_data(flight_no):
    # 將 limit 放寬，抓取近期清單以便我們自己篩選出「下一個航班」
    url = f"https://api.flightradar24.com/common/v1/flight/list.json?query={flight_no}&fetchBy=flight&page=1&limit=10"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    current_time_str = datetime.now(TZ).strftime("%H:%M:%S")
    current_ts = datetime.now(TZ).timestamp()
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {"航班": flight_no, "狀態": "❌ 請求遭阻擋", "表定抵達": "-", "即時預計抵達": "-", "最後更新": current_time_str}
            
        data = res.json()
        flights = data.get('result', {}).get('response', {}).get('data', [])
        
        if not flights:
            return {"航班": flight_no, "狀態": "🔍 查無近期航班", "表定抵達": "-", "即時預計抵達": "-", "最後更新": current_time_str}
        
        # 尋找「當前正在飛」或「下一個表定」的航班
        target_flight = None
        for f in flights:
            sched_arr = f.get('time', {}).get('scheduled', {}).get('arrival')
            if not sched_arr:
                continue
            
            # 抓取表定時間大於「現在減2小時」的航班（包含剛降落或即將起飛的航班）
            if sched_arr > (current_ts - 7200):
                target_flight = f
                break
        
        # 如果都沒找到，退回顯示陣列中最後一個
        if not target_flight:
            target_flight = flights[-1]
            
        status_text = target_flight.get('status', {}).get('text', '未知')
        time_data = target_flight.get('time', {})
        
        # 1. 抓取並轉換表定抵達時間 (Scheduled)
        sched_ts = time_data.get('scheduled', {}).get('arrival')
        sched_time = datetime.fromtimestamp(sched_ts, TZ).strftime("%m-%d %H:%M") if sched_ts else "未知"
        
        # 2. 抓取並轉換即時預計抵達時間 (Estimated/Real)
        est_ts = time_data.get('estimated', {}).get('arrival') or time_data.get('real', {}).get('arrival')
        est_time = datetime.fromtimestamp(est_ts, TZ).strftime("%m-%d %H:%M") if est_ts else "依表定時間"
        
        # 標記狀態 Emoji
        if "Delayed" in status_text:
            status = f"⚠️ {status_text}"
        elif "Canceled" in status_text:
            status = f"🚫 {status_text}"
        elif "Landed" in status_text:
            status = f"🏁 {status_text}"
        else:
            status = f"✅ {status_text}"
            
        return {
            "航班": flight_no,
            "狀態": status,
            "表定抵達": sched_time,
            "即時預計抵達": est_time,
            "最後更新": current_time_str
        }
        
    except Exception as e:
        return {"航班": flight_no, "狀態": "🔌 連線異常", "表定抵達": "-", "即時預計抵達": "-", "最後更新": current_time_str}

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
