import streamlit as st
from datetime import datetime, time, timedelta
import requests
from pytz import timezone

# --- Supabase設定 ---
SUPABASE_URL = "https://svexgvaaeeszdtsbggnf.supabase.co"
SUPABASE_API_KEY = "REDACTED_SUPABASE_KEY"

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
}

# --- LINE設定（カテゴリ別トークンとグループID） ---
CATEGORY_TO_ACCESS_TOKEN = {
    "ランチ": "REDACTED_LINE_TOKEN",
    "ディナー": "REDACTED_LINE_TOKEN",
    "ベーグル": "REDACTED_LINE_TOKEN"
}

CATEGORY_TO_GROUPID = {
    "ランチ": "REDACTED_LINE_GROUP_ID",
    "ディナー": "REDACTED_LINE_GROUP_ID",
    "ベーグル": "REDACTED_LINE_GROUP_ID"
}

# --- 共通関数 ---

def get_today_jst():
    jst = timezone('Asia/Tokyo')
    return datetime.now(jst).date()

def fetch_minus(subcategories):
    categories_query = ",".join(f'"{cat}"' for cat in subcategories)
    params = {
        "select": "*",
        "category": f"in.({categories_query})",
        "order": "date_origin",
        "date_origin": f"gte.{get_today_jst().strftime('%Y-%m-%d')}"
    }
    response = requests.get(f"{SUPABASE_URL}/rest/v1/minus", headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("取得エラー:", response.text)
        return []

def insert_minus(category, date_display, date_origin, time_range, minus_count):
    new_data = {
        "category": category,
        "date_display": date_display,
        "date_origin": date_origin,
        "time_range": time_range,
        "minus_count": minus_count
    }
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/minus",
        headers={**headers, "Content-Type": "application/json"},
        json=[new_data]
    )
    if response.status_code != 201:
        print("登録エラー:", response.text)

def update_minus(id, new_count):
    if new_count <= 0:
        response = requests.delete(
            f"{SUPABASE_URL}/rest/v1/minus?id=eq.{id}",
            headers=headers
        )
        if response.status_code != 204:
            print("削除エラー:", response.text)
    else:
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/minus?id=eq.{id}",
            headers={**headers, "Content-Type": "application/json"},
            json={"minus_count": new_count}
        )
        if response.status_code != 204:
            print("更新エラー:", response.text)

def send_group_notification(group_key, subcategories):
    records = fetch_minus(subcategories)
    if not records:
        return

    access_token = CATEGORY_TO_ACCESS_TOKEN[group_key]
    group_id = CATEGORY_TO_GROUPID[group_key]

    today = get_today_jst()
    urgent_days = [(today + timedelta(days=i)).strftime("%m/%d") for i in range(4)]

    # --- サブカテゴリごとにまとめる ---
    cat_map = {}
    for record in records:
        cat = record["category"]
        date_display = record["date_display"]
        time_range = record["time_range"]
        minus_count = record["minus_count"]
        suffix = "🆘" if date_display in urgent_days else ""

        cat_map.setdefault(cat, []).append(f"{date_display} {time_range} ▲{minus_count}人{suffix}")

    # --- メッセージ構築 ---
    message = "🆘シフトご協力お願いします🆘\n\n"

    for cat, lines in sorted(cat_map.items()):
        message += f"{cat}\n"
        for line in sorted(lines):  # 日付順に並ぶ
            message += line + "\n"
        message += "\n"

    message += "ーーーーーーーーー\n\n"

    if group_key == "ランチ":
        message += "ヘルプ可能な方は【笹子MGR】へ個人LINEお願いします🙇‍♀️"
    elif group_key == "ディナー":
        message += "ヘルプ可能な方は【田島店長】へ個人LINEお願いします🙇‍♀️"
    elif group_key == "ベーグル":
        message += "ヘルプ可能な方は【堀井店長】へ個人LINEお願いします🙇‍♀️"

    headers_line = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": message.strip()}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers_line, json=payload)

# --- 提出締切取得 & 古いデータ自動削除（常に最新1件を残す） ---
def get_current_deadline():
    url = f"{SUPABASE_URL}/rest/v1/shift_deadline?select=id,deadline,created_at&order=created_at.desc"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        rows = response.json()
        if not rows:
            return None

        latest = rows[0]
        latest_deadline = datetime.strptime(latest["deadline"], "%Y-%m-%d").date()

        # 📌 今日より前なら削除して非表示に
        if latest_deadline < get_today_jst():
            requests.delete(f"{SUPABASE_URL}/rest/v1/shift_deadline?id=eq.{latest['id']}", headers=headers)
            return None

        # 過去のデータを一括削除（最新以外）
        delete_ids = [r["id"] for r in rows if r["id"] != latest["id"]]
        for del_id in delete_ids:
            requests.delete(f"{SUPABASE_URL}/rest/v1/shift_deadline?id=eq.{del_id}", headers=headers)

        return latest_deadline
    return None

# --- 提出締切をLINEグループに通知する関数 ---
def notify_deadline_to_line(deadline_date):
    access_token = list(CATEGORY_TO_ACCESS_TOKEN.values())[0]  # 共通トークン使用
    group_id = "REDACTED_LINE_GROUP_ID"

    # 🔽 年を省略して / 区切り表示に変更
    formatted_date = deadline_date.strftime("%-m/%-d")  # Linux/mac の場合（Windowsなら "%#m/%#d"）
    message = f"⚠️シフト提出締切日は\n【{formatted_date}】です！\n提出遅れないようにお願いします🙇‍♀️"

    headers_line = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": message}]
    }

    requests.post("https://api.line.me/v2/bot/message/push", headers=headers_line, json=payload)



# --- 提出締切更新処理（全削除して1件だけ保存） ---
def update_deadline(new_date):
    requests.delete(f"{SUPABASE_URL}/rest/v1/shift_deadline", headers=headers)
    payload = [{"deadline": new_date.strftime("%Y-%m-%d")}]
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/shift_deadline",
        headers={**headers, "Content-Type": "application/json"},
        json=payload
    )
    return response.status_code == 201



# --- 画面表示スタート ---
st.set_page_config(page_title="シフトマイナス管理システム", layout="wide")

color_map = {
    "ランチ【ホール】": "#ffe4b5",
    "ランチ【キッチン】": "#ffe4b5",
    "ディナー【ホール】": "#d0eaff",
    "ディナー【キッチン】": "#d0eaff",
    "ベーグル": "#e1ffd0"
}

st.markdown("""
    <style>
        .main > div { max-width: 960px; margin: auto; }
        input[type=number] {
            background-color: #fff !important;
            border: 1px solid #333 !important;
            color: #000 !important;
            padding: 6px; border-radius: 6px;
        }
        input[type=number]:focus {
            border-color: #006a38 !important;
            outline: none !important;
            box-shadow: 0 0 0 2px rgba(0,106,56,0.2);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h1 style='text-align:center;color:#333;font-family:"Segoe UI",sans-serif;font-size:32px;'>
        シフトマイナス管理
    </h1>
""", unsafe_allow_html=True)

# --- UI表示 ---
st.markdown("""
    <h2 style='color:#444;margin:30px 0;
               border-left:5px solid #006a38;border-bottom:1px solid #006a38;
               padding:1% 1% 1% 3%;font-size:25px;'>
        現在のシフト提出締切日
    </h2>
""", unsafe_allow_html=True)

current_deadline = get_current_deadline()
if current_deadline:
    st.markdown(f"**現在の締切日：{current_deadline.strftime('%m/%d')}**")

    if st.button("締切日を通知する", use_container_width=True):
        notify_deadline_to_line(current_deadline)
        st.success("締切日をLINEに通知しました")
else:
    st.markdown("⚠️ まだ提出締切が登録されていません。")

new_deadline = st.date_input("新しい提出締切日を選択してください", value=current_deadline or get_today_jst())

if st.button("提出締切を更新", use_container_width=True):
    if update_deadline(new_deadline):
        st.success("提出締切を更新しました")
        st.rerun()  # ← これで画面が即リフレッシュされ、表示が更新されます
    else:
        st.error("更新に失敗しました")

st.markdown("""
    <h2 style='color:#444;margin:30px 0;
               border-left:5px solid #006a38;border-bottom:1px solid #006a38;
               padding:1% 1% 1% 3%;font-size:25px;'>
        マイナスの新規登録
    </h2>
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    category = st.selectbox("カテゴリ", list(color_map.keys()))
with col2:
    minus_date = st.date_input("日付", value=get_today_jst())
with col3:
    start_time = st.time_input("開始", value=time(9, 0))
with col4:
    end_time = st.time_input("終了", value=time(13, 0))
with col5:
    minus_count = st.selectbox("人数", options=list(range(1, 6)))

if st.button("登録", use_container_width=True):
    insert_minus(
        category,
        minus_date.strftime("%m/%d"),
        minus_date.strftime("%Y-%m-%d"),
        f"{start_time.strftime('%H:%M')}〜{end_time.strftime('%H:%M')}",
        minus_count
    )
    st.success("登録しました！")
    st.rerun()

st.divider()

st.markdown("""
    <h2 style='color:#444;margin:30px 0;
               border-left:5px solid #006a38;border-bottom:1px solid #006a38;
               padding:1% 1% 1% 3%;font-size:25px;'>
        現在募集中のマイナス日
    </h2>
""", unsafe_allow_html=True)

category_groups = {
    "ランチ": ["ランチ【ホール】", "ランチ【キッチン】"],
    "ディナー": ["ディナー【ホール】", "ディナー【キッチン】"],
    "ベーグル": ["ベーグル"]
}

selected_group = st.selectbox("カテゴリを選択", list(category_groups.keys()))
subcats = category_groups[selected_group]
records = fetch_minus(subcats)

if not records:
    st.write("現在募集中のマイナスはありません。")
else:
    for record in records:
        _id = record["id"]
        category = record["category"]
        date_display = record["date_display"]
        time_range = record["time_range"]
        minus_count = record["minus_count"]

        with st.container():
            st.markdown(f"""
                <div style='background-color:{color_map.get(category)};
                            padding:15px;border-radius:12px;margin-bottom:10px;'>
                    <h4 style='margin:0;'>{category}（{date_display}）</h4>
                    <p style='margin:0;'>時間帯: {time_range}</p>
                    <p style='margin:0;'>あと <strong>{minus_count}</strong> 人必要</p>
                </div>
            """, unsafe_allow_html=True)

            filled = st.number_input(
                f"埋まった人数を入力（{category} - {date_display}）",
                min_value=0,
                max_value=minus_count,
                key=f"input_{_id}"
            )
            if filled > 0:
                if st.button(f"反映（{category} - {date_display}）", key=f"btn_{_id}"):
                    new_count = minus_count - filled
                    update_minus(_id, new_count)
                    st.rerun()

    if st.button(f"{selected_group}マイナス募集通知を送る", use_container_width=True, key=f"notify_{selected_group}"):
        send_group_notification(selected_group, category_groups[selected_group])

        st.success("通知を送信しました！")

