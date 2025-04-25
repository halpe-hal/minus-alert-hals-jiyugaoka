import json
from datetime import datetime
import requests
import os

# ファイルパス
DATA_FILE = "minus_data.json"
LOG_FILE = "notified_log.json"

# LINE設定
LINE_ACCESS_TOKEN = "lszhy7usClELTs8XrUl5WUgz2eczgYDv8ej9BdTK4wGa1bH27e8Yaw1wErd8bieRYWEkjTvJXwmVv3c7rTVw/K7aUS4HOCwxd5jTpnohzUxn7+0eCRRAmlH6+LIJow4sAgPK8jELBzasnl9Nqo9/kAdB04t89/1O/w1cDnyilFU="
CATEGORY_TO_GROUPID = {
    "ランチ": "REDACTED_LINE_GROUP_ID",
    "ディナー": "REDACTED_LINE_GROUP_ID",
    "ベーグル": "REDACTED_LINE_GROUP_ID"
}

# 通知対象日（3日前、2日前、1日前）
NOTICE_DAYS_BEFORE = [3, 2, 1]

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

    group_records_urgent = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}
    group_records_future = {"ランチ": {}, "ディナー": {}, "ベーグル": {}}

    new_notified = []

    for item in minus_list:
        category_full = item["カテゴリ"]
        date_str = item["日付元"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        days_before = (date_obj - today).days

        if "ランチ" in category_full:
            group_key = "ランチ"
        elif "ディナー" in category_full:
            group_key = "ディナー"
        else:
            group_key = "ベーグル"

        if days_before in NOTICE_DAYS_BEFORE:
            unique_key = f"{category_full}_{date_str}_{days_before}"
            if unique_key in notified_log:
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
                sorted_records = sorted(records, key=lambda x: x["日付元"])
                for r in sorted_records:
                    message += f"{r['日付']} {r['時間帯']} ▲{r['マイナス人数']}人\n"
            message += "\nご協力お願いします！🙇‍♂️\n\n"

        if group_records_future[group]:
            message += "\n▼先の日程のマイナス日▼\n"
            for subcat, records in sorted(group_records_future[group].items()):
                message += f"\n{subcat}\n"
                sorted_records = sorted(records, key=lambda x: x["日付元"])
                for r in sorted_records:
                    message += f"{r['日付']} {r['時間帯']} ▲{r['マイナス人数']}人\n"

            message += "\nご協力お願いします！🙇‍♂️"

        send_line_notification(CATEGORY_TO_GROUPID[group], message.strip())

    # 通知した3日前・2日前・1日前分だけ記録する
    if new_notified:
        notified_log.extend(new_notified)
        save_log(notified_log)

if __name__ == "__main__":
    main()
