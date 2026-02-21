import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Flight Radar Dashboard", layout="wide")

# 預設時區防呆
DEFAULT_TZ = ZoneInfo("Asia/Manila")

def format_time_by_tz(ts, tz_name):
    """將 Unix Timestamp 轉換為指定機場的當地時間"""
    if not ts: return "-"
    try:
        # 根據機場的時區動態轉換時間
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
    
    # 維持你原本要求的精確欄位名稱
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
            
            # 以出發地時區來判定使用者選擇的日期
            orig_tz = f.get('airport', {}).get('origin', {}).get('timezone', {}).get('name')
            check_tz = ZoneInfo(orig_tz) if orig_tz else DEFAULT_TZ
            
            flight_date = datetime.fromtimestamp(compare_ts, check_tz).date()
            if flight_date == target_date:
                target_flight = f
                break
        
        if not target_flight: return empty_row("📅 該日無航班")
            
        # --- 解析機場與時區 ---
        orig_data = target_flight.get('airport', {}).get('origin', {})
        dest_data = target_flight.get
