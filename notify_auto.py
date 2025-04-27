import requests
from datetime import datetime
from pytz import timezone
from supabase import create_client

# Supabase接続情報
SUPABASE_URL = "https://svexgvaaeeszdtsbggnf.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)

# LINE設定
LINE_ACCESS_TOKEN = "lszhy7usClELTs8XrUl5WUgz2eczgYDv8ej9BdTK4wGa1bH27e8Yaw1wErd8bieRYWEkjTvJXwmVv3c7rTVw/K7aUS4HOCwxd5jTpnohzUxn7+0eCRRAmlH6+LIJow4sAgPK8jELBzasnl9Nqo9/kAdB04t89/1O/w1cDnyilFU="
CATEGORY_TO_GROUPID = {
    "ランチ": "C2addcfb0a7d3375c310ff01e42a1dc30",
    "ディナー": "REDACTED_LINE_GROUP_ID",
    "ベーグル": "REDACTED_LINE_GROUP_ID"
}

# 通知対象日（3日前、2日前、1日前）
NOTICE_DAYS_BEFORE = [3, 2, 1]

def get_today_jst():
    jst = timezone('Asia/Tokyo')
    return datetime.now(jst).date()

def cleanup_expired():
    today_str = get_today_jst().strftime("%Y-%m-%d")
    supabase.table("minus").delete().lt("date_origin", today_str).execute()
    print(f"🧹 過去日付（{today_str}より前）をSupabaseから削除しました", flush=True)

def fetch_minus():
    today = get_today_jst()
    response = supabase.table("minus").select("*").gte("date_origin", today.strftime("%Y-%m-%d")).order("date_origin").execute()
    return response.data

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
    print("📨 通知送信結果：", response.status_code, flush=True)

def main():
    print("🚀 notify_auto.py 実行開始", flush=True)

    # まず、期限切れデータをクリーンアップ！
    cleanup_expired()

    today = get_today_jst()
    all_records = fetch_minus()

    group_records_urgent = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}
    group_records_future = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}

    for record in all_records:
        category_full = record['category']
        date_display = record['date_display']
        time_range = record['time_range']
        minus_count = record['minus_count']
        date_origin = record['date_origin']
        date_obj = datetime.strptime(date_origin, "%Y-%m-%d").date()
        days_before = (date_obj - today).days

        if "ランチ" in category_full:
            group_key = "ランチ"
        elif "ディナー" in category_full:
            group_key = "ディナー"
        else:
            group_key = "ベーグル"

        if days_before in NOTICE_DAYS_BEFORE:
            group_records_urgent.setdefault(group_key, {}).setdefault(category_full, []).append({
                "date_display": date_display,
                "time_range": time_range,
                "minus_count": minus_count
            })
        elif days_before > 3:
            group_records_future.setdefault(group_key, {}).setdefault(category_full, []).append({
                "date_display": date_display,
                "time_range": time_range,
                "minus_count": minus_count
            })

    for group, subcats in group_records_urgent.items():
        if not subcats and not group_records_future[group]:
            print(f"✅ {group}：通知する内容はなし", flush=True)
            continue

        message = ""

        if subcats:
            message += "🆘直近で埋まっていないマイナス日です！\n"
            for subcat, records in sorted(subcats.items()):
                message += f"\n{subcat}\n"
                for record in sorted(records, key=lambda x: x["date_display"]):
                    message += f"{record['date_display']} {record['time_range']} ▲{record['minus_count']}人\n"
            message += "\nご協力お願いします！🙇‍♂️\n\n"

        if group_records_future[group]:
            message += "\n▼先の日程のマイナス日▼\n"
            for subcat, records in sorted(group_records_future[group].items()):
                message += f"\n{sub
