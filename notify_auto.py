import json
from datetime import datetime, timedelta
import requests
import os

# ファイルパス
DATA_FILE = "minus_data.json"
LOG_FILE = "notified_log.json"

# LINE設定
LINE_ACCESS_TOKEN = "lszhy7usClELTs8XrUl5WUgz2eczgYDv8ej9BdTK4wGa1bH27e8Yaw1wErd8bieRYWEkjTvJXwmVv3c7rTVw/K7aUS4HOCwxd5jTpnohzUxn7+0eCRRAmlH6+LIJow4sAgPK8jELBzasnl9Nqo9/kAdB04t89/1O/w1cDnyilFU="
CATEGORY_TO_GROUPID = {
    "ランチ": "C2addcfb0a7d3375c310ff01e42a1dc30",
    "ディナー": "C19ec6409b4971ad50d9d1df02bd5c8d7",
    "ベーグル": ""
}

NOTICE_DAYS_BEFORE = [7, 3, 1]

def load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return json.load(f)

def save_log(log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

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
    notified_log = load_log()

    with open(DATA_FILE, "r") as f:
        minus_list = json.load(f)

    # グループごと → サブカテゴリごと → データ一覧
    group_records = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}

    for item in minus_list:
        category_full = item["カテゴリ"]
        date_str = item["日付元"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        days_before = (date_obj - today).days

        if days_before not in NOTICE_DAYS_BEFORE:
            continue

        unique_key = f"{category_full}_{date_str}_{days_before}"
        if unique_key in notified_log:
            continue

        # グループカテゴリを決定
        if "ランチ" in category_full:
            group_key = "ランチ"
        elif "ディナー" in category_full:
            group_key = "ディナー"
        else:
            group_key = "ベーグル"

        if category_full not in group_records[group_key]:
            group_records[group_key][category_full] = []
        group_records[group_key][category_full].append(item)

        notified_log.append(unique_key)

    # グループごとに通知を作成
    for group, subcats in group_records.items():
        if not subcats:
            continue

        message = "🆘まだ埋まっていないマイナス日です！\n"

        for subcat, records in sorted(subcats.items()):
            message += f"\n{subcat}\n"
            sorted_records = sorted(records, key=lambda x: x["日付元"])
            for r in sorted_records:
                message += f"{r['日付']} {r['時間帯']} ▲{r['マイナス人数']}人\n"

        send_line_notification(CATEGORY_TO_GROUPID[group], message.strip())

    save_log(notified_log)

if __name__ == "__main__":
    main()
