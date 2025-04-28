import requests
import time
from datetime import datetime
from pytz import timezone

# --- Supabase設定 ---
SUPABASE_URL = "https://svexgvaaeeszdtsbggnf.supabase.co"
SUPABASE_API_KEY = "REDACTED_SUPABASE_KEY"

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}

# --- LINE設定 ---
LINE_ACCESS_TOKEN = "lszhy7usClELTs8XrUl5WUgz2eczgYDv8ej9BdTK4wGa1bH27e8Yaw1wErd8bieRYWEkjTvJXwmVv3c7rTVw/K7aUS4HOCwxd5jTpnohzUxn7+0eCRRAmlH6+LIJow4sAgPK8jELBzasnl9Nqo9/kAdB04t89/1O/w1cDnyilFU="

CATEGORY_TO_GROUPID = {
    "ランチ": "REDACTED_LINE_GROUP_ID",
    "ディナー": "REDACTED_LINE_GROUP_ID",
    "ベーグル": "REDACTED_LINE_GROUP_ID"
}

NOTICE_DAYS_BEFORE = [3, 2, 1]

# --- 共通関数 ---

def get_today_jst():
    jst = timezone('Asia/Tokyo')
    return datetime.now(jst).date()

def cleanup_expired():
    today_str = get_today_jst().strftime("%Y-%m-%d")
    url = f"{SUPABASE_URL}/rest/v1/minus?date_origin=lt.{today_str}"
    response = requests.delete(url, headers=headers)
    if response.status_code in (200, 204):
        print(f"🧹 過去日付（{today_str}より前）をSupabaseから削除しました", flush=True)
    else:
        print(f"❌ 過去データ削除失敗: {response.text}", flush=True)

def fetch_all_minus():
    today_str = get_today_jst().strftime("%Y-%m-%d")
    params = {
        "select": "*",
        "date_origin": f"gte.{today_str}",
        "order": "date_origin"
    }
    response = requests.get(f"{SUPABASE_URL}/rest/v1/minus", headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("取得エラー:", response.text, flush=True)
        return []

def send_line_notification(group_id, message, retry=1):
    if not group_id:
        return
    headers_line = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": message}]
    }

    for attempt in range(retry + 1):
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers_line, json=payload)
        print(f"📨 通知送信結果 (try {attempt+1}): {response.status_code}", flush=True)

        if response.status_code == 200:
            return  # 成功したら即return
        elif response.status_code == 429 and attempt < retry:
            print("⏳ 429エラー。5秒待ってリトライします...", flush=True)
            time.sleep(5)
        else:
            break  # リトライしてもダメなら抜ける

# --- メイン処理 ---

def main():
    print("🚀 notify_auto.py 実行開始", flush=True)

    # 過去日削除
    cleanup_expired()

    today = get_today_jst()
    records = fetch_all_minus()

    group_records_urgent = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}
    group_records_future = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}

    for record in records:
        category_full = record["category"]
        date_display = record["date_display"]
        time_range = record["time_range"]
        minus_count = record["minus_count"]
        date_origin = record["date_origin"]

        date_obj = datetime.strptime(date_origin, "%Y-%m-%d").date()
        days_before = (date_obj - today).days

        if "ランチ" in category_full:
            group_key = "ランチ"
        elif "ディナー" in category_full:
            group_key = "ディナー"
        else:
            group_key = "ベーグル"

        if days_before in NOTICE_DAYS_BEFORE:
            group_records_urgent.setdefault(group_key, {}).setdefault(category_full, []).append((date_display, time_range, minus_count))
        elif days_before > 3:
            group_records_future.setdefault(group_key, {}).setdefault(category_full, []).append((date_display, time_range, minus_count))

    for group, subcats in group_records_urgent.items():
        urgent_exists = any(subcats.values())  # 🔥直近マイナス日があるか判定

        if not urgent_exists:
            # 直近がないなら未来も含めて送らない
            continue

        message = ""

        if urgent_exists:
            message += "🆘直近で埋まっていないマイナス日です！\n"
            for subcat, records in sorted(subcats.items()):
                message += f"\n{subcat}\n"
                for date_display, time_range, minus_count in sorted(records):
                    message += f"{date_display} {time_range} ▲{minus_count}人\n"
            message += "\nご協力お願いします！🙇‍♂️\n\n"

        if group_records_future[group]:
            message += "\n▼先の日程のマイナス日▼\n"
            for subcat, records in sorted(group_records_future[group].items()):
                message += f"\n{subcat}\n"
                for date_display, time_range, minus_count in sorted(records):
                    message += f"{date_display} {time_range} ▲{minus_count}人\n"
            message += "\nご協力お願いします！🙇‍♂️"

        send_line_notification(CATEGORY_TO_GROUPID[group], message.strip())
        time.sleep(1)  # ★送信ごとに1秒休憩

    print("✅ notify_auto.py 実行完了", flush=True)

if __name__ == "__main__":
    main()
