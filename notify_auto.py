import sqlite3
from datetime import datetime
import requests
import os

# ファイルパス（DBファイル）
DB_FILE = "minus.db"

# LINE設定
LINE_ACCESS_TOKEN = "lszhy7usClELTs8XrUl5WUgz2eczgYDv8ej9BdTK4wGa1bH27e8Yaw1wErd8bieRYWEkjTvJXwmVv3c7rTVw/K7aUS4HOCwxd5jTpnohzUxn7+0eCRRAmlH6+LIJow4sAgPK8jELBzasnl9Nqo9/kAdB04t89/1O/w1cDnyilFU="
CATEGORY_TO_GROUPID = {
    "ランチ": "C2addcfb0a7d3375c310ff01e42a1dc30",
    "ディナー": "REDACTED_LINE_GROUP_ID",
    "ベーグル": "REDACTED_LINE_GROUP_ID"
}

# 通知対象日（3日前、2日前、1日前）
NOTICE_DAYS_BEFORE = [3, 2, 1]

# SQLite DB接続
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# 通知済みチェック
def is_notified(unique_key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM notified_log WHERE unique_key = ?", (unique_key,))
    result = c.fetchone()
    conn.close()
    return result is not None

# 通知済みログに保存
def save_log(unique_key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO notified_log (unique_key) VALUES (?)", (unique_key,))
    conn.commit()
    conn.close()

# 通知送信
def send_line_notification(group_id, message):
    if not group_id:
        return
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": message}]
    }
    response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)
    print("📨 通知送信結果：", response.status_code)

def main():
    today = datetime.today().date()

    # DBからマイナスデータを取得
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, category, date_display, time_range, minus_count, date_origin FROM minus")
    minus_list = c.fetchall()
    conn.close()

    group_records_urgent = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}
    group_records_future = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}

    new_notified = []

    for item in minus_list:
        category_full = item[1]  # category
        date_str = item[5]  # date_origin
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        formatted_date = date_obj.strftime("%m/%d")  # ここを修正して、日付を"MM/DD"形式に変更
        days_before = (date_obj - today).days

        if "ランチ" in category_full:
            group_key = "ランチ"
        elif "ディナー" in category_full:
            group_key = "ディナー"
        else:
            group_key = "ベーグル"

        if days_before in NOTICE_DAYS_BEFORE:
            unique_key = f"{category_full}_{date_str}_{days_before}"
            if is_notified(unique_key):
                continue

            if category_full not in group_records_urgent[group_key]:
                group_records_urgent[group_key][category_full] = []
            group_records_urgent[group_key][category_full].append(item)

            new_notified.append(unique_key)

        elif days_before > 3:
            if category_full not in group_records_future[group_key]:
                group_records_future[group_key][category_full] = []
            group_records_future[group_key][category_full].append(item)

    for group, subcats in group_records_urgent.items():
        if not subcats and not group_records_future[group]:
            continue

        message = ""

        if subcats:
            message += "🆘直近で埋まっていないマイナス日です！\n"
            for subcat, records in sorted(subcats.items()):
                message += f"\n{subcat}\n"
                sorted_records = sorted(records, key=lambda x: x[5])  # Sorting by date_origin
                for r in sorted_records:
                    message += f"{formatted_date} {r[3]} ▲{r[4]}人\n"  # formatted_date, time_range, minus_count
            message += "\nご協力お願いします！🙇‍♂️\n\n"

        if group_records_future[group]:
            message += "\n▼先の日程のマイナス日▼\n"
            for subcat, records in sorted(group_records_future[group].items()):
                message += f"\n{subcat}\n"
                sorted_records = sorted(records, key=lambda x: x[5])  # Sorting by date_origin
                for r in sorted_records:
                    message += f"{formatted_date} {r[3]} ▲{r[4]}人\n"  # formatted_date, time_range, minus_count

            message += "\nご協力お願いします！🙇‍♂️"

        send_line_notification(CATEGORY_TO_GROUPID[group], message.strip())

    # 通知した3日前・2日前・1日前分だけ記録する
    if new_notified:
        for unique_key in new_notified:
            save_log(unique_key)

if __name__ == "__main__":
    main()
