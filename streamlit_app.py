import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Flight Radar Dashboard", layout="wide")

DEFAULT_TZ = ZoneInfo("Asia/Manila")

def format_time_by_tz(ts, tz_name):
    if not ts: return "-"
    try:
        tz = ZoneInfo(tz_name) if tz_name else DEFAULT_TZ
        return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return datetime.fromtimestamp(ts, DEFAULT_TZ).strftime("%Y-%m-%d %H:%M*")

def get_flight_data(flight_no, target_date):
    url = f"https://api.flightradar24.com/common/v1/flight/list.json?query={flight_no}&fetchBy=flight&page=1&limit=20"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    current_time_str = datetime.now(DEFAULT_TZ).strftime("%H:%M:%S")
    
    def empty_row(status_msg):
        return {
            "航班": flight_no,
            "狀態": status_msg,
            "表定起飛": "-",
            "表定抵達": "-",
            "實際/預計起飛": "-",
            "實際/預計抵達": "-",
            "最後更新": current_time_str
        }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return empty_row("❌ 請求遭阻擋")
            
        data = res.json()
        flights = data.get('result', {}).get('response', {}).get('data', [])
        
        if not flights: return empty_row("❓ 無此航班")
        
        target_flight = None
        for f in flights:
            sched_dep_ts = f.get('time', {}).get('scheduled', {}).get('departure')
            sched_arr_ts = f.get('time', {}).get('scheduled', {}).get('arrival')
            compare_ts = sched_dep_ts if sched_dep_ts else sched_arr_ts
            if not compare_ts: continue
            
            orig_tz = f.get('airport', {}).get('origin', {}).get('timezone', {}).get('name')
            check_tz = ZoneInfo(orig_tz) if orig_tz else DEFAULT_TZ
            
            flight_date = datetime.fromtimestamp(compare_ts, check_tz).date()
            if flight_date == target_date:
                target_flight = f
                break
        
        if not target_flight: return empty_row("📅 該日無航班")
            
        orig_data = target_flight.get('airport', {}).get('origin', {})
        dest_data = target_flight.get('airport', {}).get('destination', {})
        
        orig_code = orig_data.get('code', {}).get('iata', '???') if orig_data else '???'
        dest_code = dest_data.get('code', {}).get('iata', '???') if dest_data else '???'
        
        orig_tz_name = orig_data.get('timezone', {}).get('name') if orig_data else None
        dest_tz_name = dest_data.get('timezone', {}).get('name') if dest_data else None

        time_data = target_flight.get('time', {})
        sched_dep_ts = time_data.get('scheduled', {}).get('departure')
        sched_arr_ts = time_data.get('scheduled', {}).get('arrival')
        real_dep_ts = time_data.get('real', {}).get('departure') or time_data.get('estimated', {}).get('departure')
        real_arr_ts = time_data.get('real', {}).get('arrival') or time_data.get('estimated', {}).get('arrival')

        str_sched_dep = f"[{orig_code}] {format_time_by_tz(sched_dep_ts, orig_tz_name)}" if sched_dep_ts else "-"
        str_sched_arr = f"[{dest_code}] {format_time_by_tz(sched_arr_ts, dest_tz_name)}" if sched_arr_ts else "-"
        str_real_dep = f"[{orig_code}] {format_time_by_tz(real_dep_ts, orig_tz_name)}" if real_dep_ts else "依表定時間"
        str_real_arr = f"[{dest_code}] {format_time_by_tz(real_arr_ts, dest_tz_name)}" if real_arr_ts else "依表定時間"
        
        status_text = target_flight.get('status', {}).get('text', '未知')
        if "Delayed" in status_text: status = f"⚠️ {status_text}"
        elif "Canceled" in status_text: status = f"🚫 {status_text}"
        elif "Landed" in status_text: status = f"🏁 {status_text}"
        else: status = f"✅ {status_text}"
            
        return {
            "航班": flight_no,
            "狀態": status,
            "表定起飛": str_sched_dep,
            "表定抵達": str_sched_arr,
            "實際/預計起飛": str_real_dep,
            "實際/預計抵達": str_real_arr,
            "最後更新": current_time_str
        }
        
    except Exception as e:
        return empty_row("🔌 連線異常")

# --- UI 介面 ---
st.title("✈️ 專業版航班監控 Dashboard")

if "run" not in st.session_state: st.session_state.run = False

with st.sidebar:
    st.header("控制台")
    
    # 新增顯示模式切換
    view_mode = st.radio("🖥️ 顯示模式", ["💻 表格模式 (適合電腦)", "📱 卡片模式 (適合手機)"])
    st.divider()
    
    selected_date = st.date_input("選擇監控日期 (依出發地時間)", datetime.now(DEFAULT_TZ).date())
    
    inputs = st.text_area("航班編號 (每行一個)", "CI705\nBR225\nCX705").split('\n')
    flights_list = [f.strip().upper() for f in inputs if f.strip()][:10]
    
    col1, col2 = st.columns(2)
    if col1.button("🚀 開始監控"): st.session_state.run = True
    if col2.button("🛑 停止"): st.session_state.run = False
    
    st.info("自動更新頻率：10 分鐘")

placeholder = st.empty()
if st.session_state.run:
    while st.session_state.run:
        with st.spinner(f"正在同步 {selected_date.strftime('%Y-%m-%d')} 的航班數據..."):
            data = [get_flight_data(f, selected_date) for f in flights_list]
            df = pd.DataFrame(data)
            
        with placeholder.container():
            # 根據使用者選擇的模式渲染不同 UI
            if "表格模式" in view_mode:
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                # 手機版卡片式 UI (使用 container 加上邊框)
                for index, row in df.iterrows():
                    with st.container(border=True):
                        st.markdown(f"### ✈️ {row['航班']} &nbsp; | &nbsp; {row['狀態']}")
                        st.markdown(f"**🛫 起飛:** <br> 表定：{row['表定起飛']} <br> 實際：{row['實際/預計起飛']}", unsafe_allow_html=True)
                        st.markdown(f"**🛬 抵達:** <br> 表定：{row['表定抵達']} <br> 實際：{row['實際/預計抵達']}", unsafe_allow_html=True)
                        st.caption(f"最後更新: {row['最後更新']}")

            next_update = (datetime.now(DEFAULT_TZ).timestamp() + 600)
            next_update_str = datetime.fromtimestamp(next_update, DEFAULT_TZ).strftime('%H:%M:%S')
            st.success(f"數據同步完成。下一次更新時間：{next_update_str}")
        
        for _ in range(600):
            if not st.session_state.run: break
            time.sleep(1)
            
        if st.session_state.run:
            st.rerun()
else:
    st.info("請設定日期並點擊左側「開始監控」以獲取即時數據。")
