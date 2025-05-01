import requests
import time
from datetime import datetime, timedelta
from pytz import timezone

# --- Supabase設定 ---
SUPABASE_URL = "https://svexgvaaeeszdtsbggnf.supabase.co"
SUPABASE_API_KEY = "REDACTED_SUPABASE_KEY"

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}

# --- LINE設定（カテゴリ別） ---
CATEGORY_TO_ACCESS_TOKEN = {
    "ランチ": "hmp3OjtL/EgTaApP1tZFBmH7pugsMhINkziSw2hALJwvycAbuaDWwka8yYiFTpx4YoB9V3+0uOSaUoerzUmAZPtDNaDJXb6XFop1cQ4B47sqLAGgQDMYQTUkmOD848KIaJJs9cSmJ6mnpJ3exzQGxAdB04t89/1O/w1cDnyilFU=",
    "ディナー": "Z2sMt/mVYmkhaqkYdIGfVVW3SF1pDmuUYO9cRxtccnlV7kgK7SOpi0fRQdpb266lDQp8rMSgIN5src670FbzN/3H5XkH6LeQTJScREFH8rHj1RhP/psxoTDh2N4fywhsv+SUN8l0nmnXZ9Q5xzl4HQdB04t89/1O/w1cDnyilFU=",
    "ベーグル": "aHnqYPGLV2yOqW80wEtnyV1BmixOyd6R/pdp4iQrAxK3qacd2eYPMwe0P9jKDuyzB1aJoZJII2YpLUGnrRhKybcZ9vhB72mCIugirf/kCU/Ebcr0IyvPBrfExwc+eUcYFrTvR6Dv1AvsVX28jvuESgdB04t89/1O/w1cDnyilFU="
}

CATEGORY_TO_GROUPID = {
    "ランチ": "REDACTED_LINE_GROUP_ID",
    "ディナー": "REDACTED_LINE_GROUP_ID",
    "ベーグル": "REDACTED_LINE_GROUP_ID"
}

CATEGORY_TO_CONTACT = {
    "ランチ": "ヘルプ可能な方は【笹子MGR】へ個人LINEお願いします🙇‍♀️",
    "ディナー": "ヘルプ可能な方は【田島店長】へ個人LINEお願いします🙇‍♀️",
    "ベーグル": "ヘルプ可能な方は【堀井店長】へ個人LINEお願いします🙇‍♀️"
}

NOTICE_DAYS_BEFORE = [0, 1, 2, 3]

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
        print(f"📨 {group_key} 通知送信結果 (try {attempt+1}): {response.status_code}", flush=True)

        if response.status_code == 200:
            return
        elif response.status_code == 429 and attempt < retry:
            print("⏳ 429エラー。10秒待ってリトライします...", flush=True)
            time.sleep(10)
        else:
            break

# --- メイン処理 ---

def main():
    print("🚀 notify_auto.py 実行開始", flush=True)

    cleanup_expired()
    today = get_today_jst()
    records = fetch_all_minus()

    group_records = {"ランチ": [], "ディナー": [], "ベーグル": []}

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

        group_records[group_key].append((date_display, time_range, minus_count, days_before))

    for group, items in group_records.items():
        if not items:
            continue

        message = "⚠️シフトご協力お願いします⚠️\n\n"

        for date_display, time_range, minus_count, days_before in sorted(items):
            suffix = "🆘" if days_before in NOTICE_DAYS_BEFORE else ""
            message += f"{date_display} {time_range} ▲{minus_count}人{suffix}\n"

        message += "\nーーーーーーーーー\n\n"
        message += CATEGORY_TO_CONTACT[group]

        send_line_notification(group, message.strip())
        time.sleep(3)

    print("✅ notify_auto.py 実行完了", flush=True)

if __name__ == "__main__":
    main()
