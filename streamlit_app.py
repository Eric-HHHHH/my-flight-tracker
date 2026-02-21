import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Flight Board", layout="wide", initial_sidebar_state="collapsed")

DEFAULT_TZ = ZoneInfo("Asia/Manila")

# --- 隱藏原生的側邊欄按鈕 (透過 CSS) ---
st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none; }
        .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

def format_time_by_tz(ts, tz_name):
    if not ts: return "-"
    try:
        tz = ZoneInfo(tz_name) if tz_name else DEFAULT_TZ
        return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return datetime.fromtimestamp(ts, DEFAULT_TZ).strftime("%Y-%m-%d %H:%M*")

def get_flight_data(flight_no, target_date):
    url = f"https://api.flightradar24.com/common/v1/flight/list.json?query={flight_no}&fetchBy=flight&page=1&limit=20"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    current_time_str = datetime.now(DEFAULT_TZ).strftime("%H:%M:%S")
    
    def empty_row(status_msg):
        return {
            "航班": flight_no, "狀態": status_msg, "表定起飛": "-", "表定抵達": "-",
            "實際/預計起飛": "-", "實際/預計抵達": "-", "最後更新": current_time_str
        }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return empty_row("❌ 請求遭阻擋")
            
        flights = res.json().get('result', {}).get('response', {}).get('data', [])
        if not flights: return empty_row("❓ 無此航班")
        
        target_flight = None
        for f in flights:
            sched_dep_ts = f.get('time', {}).get('scheduled', {}).get('departure')
            sched_arr_ts = f.get('time', {}).get('scheduled', {}).get('arrival')
            compare_ts = sched_dep_ts if sched_dep_ts else sched_arr_ts
            if not compare_ts: continue
            
            orig_tz = f.get('airport', {}).get('origin', {}).get('timezone', {}).get('name')
            check_tz = ZoneInfo(orig_tz) if orig_tz else DEFAULT_TZ
            
            if datetime.fromtimestamp(compare_ts, check_tz).date() == target_date:
                target_flight = f
                break
        
        if not target_flight: return empty_row("📅 該日無航班")
            
        orig_data, dest_data = target_flight.get('airport', {}).get('origin', {}), target_flight.get('airport', {}).get('destination', {})
        orig_code, dest_code = orig_data.get('code', {}).get('iata', '???') if orig_data else '???', dest_data.get('code', {}).get('iata', '???') if dest_data else '???'
        orig_tz_name, dest_tz_name = orig_data.get('timezone', {}).get('name') if orig_data else None, dest_data.get('timezone', {}).get('name') if dest_data else None

        time_data = target_flight.get('time', {})
        sched_dep_ts, sched_arr_ts = time_data.get('scheduled', {}).get('departure'), time_data.get('scheduled', {}).get('arrival')
        real_dep_ts = time_data.get('real', {}).get('departure') or time_data.get('estimated', {}).get('departure')
        real_arr_ts = time_data.get('real', {}).get('arrival') or time_data.get('estimated', {}).get('arrival')

        status_text = target_flight.get('status', {}).get('text', '未知')
        if "Delayed" in status_text: status = f"⚠️ {status_text}"
        elif "Canceled" in status_text: status = f"🚫 {status_text}"
        elif "Landed" in status_text: status = f"🏁 {status_text}"
        else: status = f"✅ {status_text}"
            
        return {
            "航班": flight_no, "狀態": status,
            "表定起飛": f"[{orig_code}] {format_time_by_tz(sched_dep_ts, orig_tz_name)}" if sched_dep_ts else "-",
            "表定抵達": f"[{dest_code}] {format_time_by_tz(sched_arr_ts, dest_tz_name)}" if sched_arr_ts else "-",
            "實際/預計起飛": f"[{orig_code}] {format_time_by_tz(real_dep_ts, orig_tz_name)}" if real_dep_ts else "依表定時間",
            "實際/預計抵達": f"[{dest_code}] {format_time_by_tz(real_arr_ts, dest_tz_name)}" if real_arr_ts else "依表定時間",
            "最後更新": current_time_str
        }
    except Exception:
        return empty_row("🔌 連線異常")

# --- 初始化 ---
if "run" not in st.session_state: st.session_state.run = False

# --- UI 介面 ---
st.title("✈️ 航班動態看板")

# 將原本的 Sidebar 改為置中的展開面板 (Expander)
# 當開始監控時，面板會自動收合，讓出螢幕空間給數據
with st.expander("⚙️ 點擊展開/收攏設定控制台", expanded=not st.session_state.run):
    view_mode = st.radio("顯示模式", ["💻 表格 (適合電腦)", "📱 卡片 (適合手機)"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("選擇監控日期 (依出發地時間)", datetime.now(DEFAULT_TZ).date())
        st.caption("🔄 自動更新頻率：每 10 分鐘一次")
    with col2:
        inputs = st.text_area("航班編號 (每行一個)", "CI705\nBR225\nCX705", height=100)
    
    flights_list = [f.strip().upper() for f in inputs if f.strip()][:10]
    
    # 滿版大按鈕，方便單手大拇指點擊
    c1, c2 = st.columns(2)
    if c1.button("🚀 開始監控", use_container_width=True, type="primary"): st.session_state.run = True
    if c2.button("🛑 停止監控", use_container_width=True): st.session_state.run = False

st.divider()

# --- 執行監控 ---
placeholder = st.empty()
if st.session_state.run:
    while st.session_state.run:
        with st.spinner(f"正在同步 {selected_date.strftime('%Y-%m-%d')} 的數據..."):
            data = [get_flight_data(f, selected_date) for f in flights_list]
            df = pd.DataFrame(data)
            
        with placeholder.container():
            if "表格" in view_mode:
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                for index, row in df.iterrows():
                    with st.container(border=True):
                        st.markdown(f"#### ✈️ {row['航班']} &nbsp;|&nbsp; {row['狀態']}")
                        st.markdown(f"**🛫 起飛:** <br> 表定：{row['表定起飛']} <br> 實際：{row['實際/預計起飛']}", unsafe_allow_html=True)
                        st.markdown(f"**🛬 抵達:** <br> 表定：{row['表定抵達']} <br> 實際：{row['實際/預計抵達']}", unsafe_allow_html=True)
                        st.caption(f"最後更新: {row['最後更新']}")

            next_update = (datetime.now(DEFAULT_TZ).timestamp() + 600)
            st.success(f"數據同步完成。下一次更新：{datetime.fromtimestamp(next_update, DEFAULT_TZ).strftime('%H:%M:%S')}")
        
        for _ in range(600):
            if not st.session_state.run: break
            time.sleep(1)
            
        if st.session_state.run: st.rerun()
else:
    st.info("請在上方控制台設定日期與航班，並點擊「🚀 開始監控」。")
