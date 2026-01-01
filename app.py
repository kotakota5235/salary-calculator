"""
アルバイト給料見込み計算アプリ

必要なライブラリ:
    pip install streamlit jpholiday

実行方法:
    streamlit run app.py
"""

import streamlit as st
import jpholiday
from datetime import datetime, date, timedelta
import re


# ===== 賃金設定 =====
BASE_WAGE = 1140        # 基本時給
WEEKEND_WAGE = 1290     # 土日祝日時給
WEEKDAY_AFTERNOON = 1190  # 平日13:00〜17:00
WEEKDAY_EVENING = 1290    # 平日17:00以降


def is_holiday_or_weekend(target_date: date) -> bool:
    """土日祝日かどうかを判定する"""
    # 土曜(5) または 日曜(6)
    if target_date.weekday() >= 5:
        return True
    # 祝日判定
    if jpholiday.is_holiday(target_date):
        return True
    return False


def parse_time(time_str: str) -> tuple[int, int]:
    """時刻文字列をパースして (時, 分) を返す"""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def time_to_minutes(hour: int, minute: int) -> int:
    """時:分 を分に変換"""
    return hour * 60 + minute


def minutes_to_hours(minutes: int) -> float:
    """分を時間（小数）に変換"""
    return minutes / 60


def calculate_overlap(start1: int, end1: int, start2: int, end2: int) -> int:
    """2つの時間帯の重なりを分で返す"""
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    return max(0, overlap_end - overlap_start)


def calculate_daily_wage(work_date: date, start_time: str, end_time: str) -> dict:
    """
    1日の給料を計算する
    
    Returns:
        dict: 計算結果（時間帯別の内訳と合計）
    """
    start_h, start_m = parse_time(start_time)
    end_h, end_m = parse_time(end_time)
    
    start_minutes = time_to_minutes(start_h, start_m)
    end_minutes = time_to_minutes(end_h, end_m)
    
    total_minutes = end_minutes - start_minutes
    
    result = {
        "date": work_date,
        "start": start_time,
        "end": end_time,
        "total_minutes": total_minutes,
        "wage": 0,
        "breakdown": []
    }
    
    # 土日祝日の場合
    if is_holiday_or_weekend(work_date):
        wage = minutes_to_hours(total_minutes) * WEEKEND_WAGE
        result["wage"] = wage
        result["breakdown"].append({
            "type": "土日祝",
            "minutes": total_minutes,
            "rate": WEEKEND_WAGE,
            "amount": wage
        })
        return result
    
    # 平日の場合 - 時間帯別に計算
    # 時間帯定義（分単位）
    MORNING_END = time_to_minutes(13, 0)      # 13:00まで（基本時給）
    AFTERNOON_END = time_to_minutes(17, 0)    # 17:00まで（1190円）
    
    wage = 0
    
    # 13:00より前（基本時給）
    morning_minutes = calculate_overlap(start_minutes, end_minutes, 0, MORNING_END)
    if morning_minutes > 0:
        morning_wage = minutes_to_hours(morning_minutes) * BASE_WAGE
        wage += morning_wage
        result["breakdown"].append({
            "type": "〜13:00",
            "minutes": morning_minutes,
            "rate": BASE_WAGE,
            "amount": morning_wage
        })
    
    # 13:00〜17:00（1190円）
    afternoon_minutes = calculate_overlap(start_minutes, end_minutes, MORNING_END, AFTERNOON_END)
    if afternoon_minutes > 0:
        afternoon_wage = minutes_to_hours(afternoon_minutes) * WEEKDAY_AFTERNOON
        wage += afternoon_wage
        result["breakdown"].append({
            "type": "13:00〜17:00",
            "minutes": afternoon_minutes,
            "rate": WEEKDAY_AFTERNOON,
            "amount": afternoon_wage
        })
    
    # 17:00以降（1290円）
    evening_minutes = calculate_overlap(start_minutes, end_minutes, AFTERNOON_END, time_to_minutes(24, 0))
    if evening_minutes > 0:
        evening_wage = minutes_to_hours(evening_minutes) * WEEKDAY_EVENING
        wage += evening_wage
        result["breakdown"].append({
            "type": "17:00〜",
            "minutes": evening_minutes,
            "rate": WEEKDAY_EVENING,
            "amount": evening_wage
        })
    
    result["wage"] = wage
    return result


def parse_shift_text(text: str) -> list[dict]:
    """
    シフト表テキストをパースする
    
    Returns:
        list: 各勤務日の情報リスト
    """
    lines = text.strip().split("\n")
    shifts = []
    
    # 現在の年を取得（年をまたぐ場合の処理用）
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    for line in lines:
        # 空行やヘッダー行をスキップ
        if not line.strip():
            continue
        if "日付" in line and "勤務時間" in line:
            continue
        
        # 「－」「ー」を含む行は勤務なしとしてスキップ
        if "－" in line or "ー" in line:
            continue
        
        # 日付パターン: MM/DD(曜日) または M/D(曜日)
        date_pattern = r"(\d{1,2})/(\d{1,2})\([^)]+\)"
        date_match = re.search(date_pattern, line)
        
        if not date_match:
            continue
        
        month = int(date_match.group(1))
        day = int(date_match.group(2))
        
        # 年の決定（現在の月より小さい月は翌年と判断）
        year = current_year
        if month < current_month - 6:  # 半年以上前の月なら翌年
            year = current_year + 1
        elif month > current_month + 6:  # 半年以上後の月なら前年
            year = current_year - 1
        
        try:
            work_date = date(year, month, day)
        except ValueError:
            continue
        
        # 勤務時間パターン: HH:MM～HH:MM または HH:MM〜HH:MM
        time_pattern = r"(\d{1,2}:\d{2})[～〜](\d{1,2}:\d{2})"
        time_match = re.search(time_pattern, line)
        
        if not time_match:
            continue
        
        start_time = time_match.group(1)
        end_time = time_match.group(2)
        
        # 時刻を2桁にフォーマット
        start_parts = start_time.split(":")
        end_parts = end_time.split(":")
        start_time = f"{int(start_parts[0]):02d}:{start_parts[1]}"
        end_time = f"{int(end_parts[0]):02d}:{end_parts[1]}"
        
        shifts.append({
            "date": work_date,
            "start": start_time,
            "end": end_time
        })
    
    return shifts


def format_minutes(minutes: int) -> str:
    """分を「○時間○分」形式にフォーマット"""
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}時間"
    return f"{hours}時間{mins}分"


def main():
    """メインアプリケーション"""
    st.set_page_config(
        page_title="アルバイト給料見込み計算",
        page_icon="💰",
        layout="centered"
    )
    
    st.title("💰 アルバイト給料見込み計算")
    
    st.markdown("""
    シフト表をコピー＆ペーストして、月給見込み額を計算します。
    
    **対応フォーマット例:**
    ```
    日付	勤務時間	労働時間	休憩時間
    12/18(木)	17:00～20:00	03:00	00:00
    12/22(月)	17:00～20:00	03:00	00:00
    01/03(土)	13:00～17:30	04:30	00:00
    ```
    """)
    
    # 賃金ルールの表示
    with st.expander("📋 賃金ルール"):
        st.markdown(f"""
        | 条件 | 時給 |
        |------|------|
        | 基本時給 | {BASE_WAGE:,}円 |
        | 土日祝日 | {WEEKEND_WAGE:,}円 |
        | 平日 13:00〜17:00 | {WEEKDAY_AFTERNOON:,}円 |
        | 平日 17:00以降 | {WEEKDAY_EVENING:,}円 |
        
        ※ 時間帯をまたぐ場合は分割計算されます
        """)
    
    # シフト表入力
    shift_text = st.text_area(
        "シフト表を貼り付けてください",
        height=200,
        placeholder="日付\t勤務時間\t労働時間\t休憩時間\n12/18(木)\t17:00～20:00\t03:00\t00:00"
    )
    
    # 計算ボタン
    if st.button("🧮 計算する", type="primary", use_container_width=True):
        if not shift_text.strip():
            st.warning("シフト表を入力してください。")
            return
        
        # パース
        shifts = parse_shift_text(shift_text)
        
        if not shifts:
            st.error("有効なシフトデータが見つかりませんでした。フォーマットを確認してください。")
            return
        
        # 計算
        results = []
        total_wage = 0
        total_minutes = 0
        
        for shift in shifts:
            result = calculate_daily_wage(shift["date"], shift["start"], shift["end"])
            results.append(result)
            total_wage += result["wage"]
            total_minutes += result["total_minutes"]
        
        # 結果表示
        st.markdown("---")
        st.subheader("📊 計算結果")
        
        # 各日の内訳
        st.markdown("#### 日別内訳")
        
        for result in sorted(results, key=lambda x: x["date"]):
            work_date = result["date"]
            weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
            weekday = weekday_names[work_date.weekday()]
            
            # 土日祝判定
            is_special = is_holiday_or_weekend(work_date)
            holiday_name = jpholiday.is_holiday_name(work_date)
            
            date_str = f"{work_date.month}/{work_date.day}({weekday})"
            if holiday_name:
                date_str += f" 🎌{holiday_name}"
            elif is_special:
                date_str += " 🗓️"
            
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{date_str}**")
                with col2:
                    st.write(f"{result['start']}〜{result['end']}")
                with col3:
                    st.write(f"**{result['wage']:,.0f}円**")
                
                # 詳細内訳（平日で時間帯をまたぐ場合）
                if len(result["breakdown"]) > 1:
                    detail_text = " / ".join([
                        f"{b['type']}: {format_minutes(b['minutes'])}×{b['rate']:,}円"
                        for b in result["breakdown"]
                    ])
                    st.caption(f"　　{detail_text}")
        
        # 合計
        st.markdown("---")
        st.subheader("📈 合計")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("合計勤務時間", format_minutes(total_minutes))
        with col2:
            st.metric("月給見込み額", f"{total_wage:,.0f}円")
        
        # 勤務日数
        st.info(f"📅 勤務日数: {len(results)}日")


if __name__ == "__main__":
    main()
