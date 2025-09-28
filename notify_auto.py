import requests
import time
from datetime import datetime, timedelta
from pytz import timezone
from dotenv import load_dotenv
import os

load_dotenv()

# --- Supabase設定 ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}

# --- LINE設定 ---
CATEGORY_TO_ACCESS_TOKEN = {
    "販売": os.getenv("LINE_ACCESS_TOKEN_HANBAI"),
    "製造": os.getenv("LINE_ACCESS_TOKEN_SEIZOU"),
}

CATEGORY_TO_GROUPID = {
    "販売": os.getenv("LINE_GROUP_ID_HANBAI"),
    "製造": os.getenv("LINE_GROUP_ID_SEIZOU"),
}

DEADLINE_GROUP_ID = os.getenv("LINE_GROUP_ID_DEADLINE")


CATEGORY_TO_CONTACT = {
    "販売": "ヘルプ可能な方は【販売】のグループLINEへ連絡お願いします🙇‍♀️",
    "製造": "ヘルプ可能な方は【製造】のグループLINEへ連絡お願いします🙇‍♀️",
}

# --- 共通関数 ---

def get_today_jst():
    jst = timezone('Asia/Tokyo')
    return datetime.now(jst).date()

def cleanup_expired():
    today_str = get_today_jst().strftime("%Y-%m-%d")
    url = f"{SUPABASE_URL}/rest/v1/minus?date_origin=lt.{today_str}"
    response = requests.delete(url, headers=headers)
    if response.status_code in (200, 204):
        print(f"🧹 {today_str}より前を削除", flush=True)

def fetch_all_minus():
    today_str = get_today_jst().strftime("%Y-%m-%d")
    params = {
        "select": "*",
        "date_origin": f"gte.{today_str}",
        "order": "date_origin"
    }
    response = requests.get(f"{SUPABASE_URL}/rest/v1/minus", headers=headers, params=params)
    return response.json() if response.status_code == 200 else []

def send_line_notification(group_key, message, retry=1):
    access_token = CATEGORY_TO_ACCESS_TOKEN[group_key]
    group_id = CATEGORY_TO_GROUPID[group_key]
    headers_line = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": message}]
    }

    for attempt in range(retry + 1):
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers_line, json=payload)
        print(f"📨 {group_key} 通知結果 (try {attempt+1}): {response.status_code}", flush=True)
        if response.status_code == 200:
            return
        elif response.status_code == 429 and attempt < retry:
            print("⏳ 429エラー、10秒待機", flush=True)
            time.sleep(10)

# --- 提出締切リマインド通知 ---
def check_and_notify_deadline_reminder():
    group_id = os.getenv("LINE_GROUP_ID_DEADLINE")
    access_token = os.getenv("LINE_ACCESS_TOKEN_HANBAI")  # 共通アカウント

    url = f"{SUPABASE_URL}/rest/v1/shift_deadline?select=deadline&order=created_at.desc&limit=1"
    response = requests.get(url, headers=headers)
    if response.status_code != 200 or not response.json():
        return

    deadline = datetime.strptime(response.json()[0]["deadline"], "%Y-%m-%d").date()
    today = get_today_jst()
    days_left = (deadline - today).days

    if days_left not in [3, 2, 1]:
        return

    if days_left == 3:
        text = (
            "⚠️シフト提出締切日まで【あと3日】です！\n\n"
            "提出が遅れる方は、\n\n"
            "販売：宮内\n製造：宮内\n\n"
            "まで必ず連絡ください！"
        )
    elif days_left == 2:
        text = (
            "⚠️シフト提出締切日まで【あと2日】です！\n\n"
            "提出が遅れる方は、\n\n"
            "販売：宮内\n製造：宮内\n\n"
            "まで必ず連絡ください！"
        )
    elif days_left == 1:
        text = (
            "⚠️【明日】がシフト提出締切日です！\n"
            "まだ提出していない方は提出お願いします🙇‍♀️\n\n"
            "提出が遅れる方は、\n\n"
            "販売：宮内\n製造：宮内\n\n"
            "まで必ず連絡ください！"
        )

    headers_line = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": text}]
    }

    requests.post("https://api.line.me/v2/bot/message/push", headers=headers_line, json=payload)
    print(f"📅 締切リマインド通知（{days_left}日前）送信", flush=True)

# --- メイン処理 ---

def main():
    print("🚀 notify_auto.py 実行開始", flush=True)
    check_and_notify_deadline_reminder()
    cleanup_expired()

    today = get_today_jst()
    urgent_days = [(today + timedelta(days=i)).strftime("%m/%d") for i in range(4)]
    records = fetch_all_minus()

    group_data = {"販売": {}, "製造": {}}

    for record in records:
        category_full = record["category"]
        date_display = record["date_display"]
        time_range = record["time_range"]
        minus_count = record["minus_count"]

        if "販売" in category_full:
            group = "販売"
        else:
            group = "製造"

        group_data.setdefault(group, {}).setdefault(category_full, []).append((date_display, time_range, minus_count))

    for group, cats in group_data.items():
        urgent_found = False
        message = "⚠️シフトご協力お願いします⚠️\n\n"

        for subcat, entries in cats.items():
            urgent_entries = []
            for date_display, time_range, minus_count in entries:
                if date_display in urgent_days:
                    urgent_found = True
                urgent_entries.append((date_display, time_range, minus_count))

            if urgent_entries:
                message += f"{subcat}\n"
                for date_display, time_range, minus_count in urgent_entries:
                    suffix = "🆘" if date_display in urgent_days else ""
                    message += f"{date_display} {time_range} ▲{minus_count}人{suffix}\n"
                message += "\n"

        if urgent_found:
            message += "ーーーーーーーーー\n\n"
            message += CATEGORY_TO_CONTACT[group]
            send_line_notification(group, message.strip())
            time.sleep(3)

    print("✅ notify_auto.py 実行完了", flush=True)

if __name__ == "__main__":
    main()
