import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="CEB Flight Tracker", layout="wide")

# 強制鎖定當地時區 (UTC+8)
TZ = ZoneInfo("Asia/Manila")

def format_time(ts):
    if ts: return datetime.fromtimestamp(ts, TZ).strftime("%H:%M")
    return "-"

def get_ceb_arrival_data(flight_no, target_date):
    url = f"https://api.flightradar24.com/common/v1/flight/list.json?query={flight_no}&fetchBy=flight&page=1&limit=20"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    current_time_str = datetime.now(TZ).strftime("%H:%M:%S")
    
    def empty_row(status_msg):
        return {
            "航班": flight_no,
            "狀態": status_msg,
            "出發地": "-",
            "表定抵達 (與Google同步)": "-",
            "實際降落 (跑道時間)": "-",
            "最後更新": current_time_str
        }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return empty_row("❌ 請求遭阻擋")
            
        data = res.json()
        flights = data.get('result', {}).get('response', {}).get('data', [])
        
        if not flights: return empty_row("❓ 無此航班")
        
        target_flight = None
        for f in flights:
            # 專注尋找該日期的航班 (以抵達時間為準)
            sched_arr_ts = f.get('time', {}).get('scheduled', {}).get('arrival')
            if not sched_arr_ts: continue
            
            flight_date = datetime.fromtimestamp(sched_arr_ts, TZ).date()
            if flight_date == target_date:
                target_flight = f
                break
        
        if not target_flight: return empty_row("📅 該日無航班")
            
        orig_code = target_flight.get('airport', {}).get('origin', {}).get('code', {}).get('iata', '???')
        
        time_data = target_flight.get('time', {})
        sched_arr_ts = time_data.get('scheduled', {}).get('arrival')
        real_arr_ts = time_data.get('real', {}).get('arrival') or time_data.get('estimated', {}).get('arrival')

        # 表定時間
        str_sched_arr = format_time(sched_arr_ts)
        # 實際降落時間 (輪子落地)
        str_real_arr = format_time(real_arr_ts) if real_arr_ts else "依表定"
        
        status_text = target_flight.get('status', {}).get('text', '未知')
        if "Delayed" in status_text: status = f"⚠️ 延誤"
        elif "Canceled" in status_text: status = f"🚫 取消"
        elif "Landed" in status_text: status = f"🏁 已降落"
        else: status = f"✅ 準點"
            
        return {
            "航班": flight_no,
            "狀態": status,
            "出發地": orig_code,
            "表定抵達 (與Google同步)": str_sched_arr,
            "實際降落 (跑道時間)": str_real_arr,
            "最後更新": current_time_str
        }
        
    except Exception as e:
        return empty_row("🔌 連線異常")

# --- UI 介面 ---
st.title("🛬 CEB 專屬航班監控 Dashboard")

if "run" not in st.session_state: st.session_state.run = False

with st.sidebar:
    st.header("控制台")
    selected_date = st.date_input("選擇降落日期", datetime.now(TZ).date())
    
    inputs = st.text_area("航班編號 (每行一個)", "CI705\nBR225\nCX705").split('\n')
    flights_list = [f.strip().upper() for f in inputs if f.strip()][:10]
    
    col1, col2 = st.columns(2)
    if col1.button("🚀 開始監控"): st.session_state.run = True
    if col2.button("🛑 停止"): st.session_state.run = False

placeholder = st.empty()
if st.session_state.run:
    while st.session_state.run:
        with st.spinner("同步數據中..."):
            data = [get_ceb_arrival_data(f, selected_date) for f in flights_list]
            df = pd.DataFrame(data)
            
        with placeholder.container():
            st.dataframe(df, use_container_width=True, hide_index=True)
            next_update = (datetime.now(TZ).timestamp() + 600)
            st.success(f"同步完成。下次更新：{datetime.fromtimestamp(next_update, TZ).strftime('%H:%M:%S')}")
        
        for _ in range(600):
            if not st.session_state.run: break
            time.sleep(1)
        if st.session_state.run: st.rerun()
else:
    st.info("請設定日期並點擊左側「開始監控」。")
