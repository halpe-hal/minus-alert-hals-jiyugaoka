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
    "ランチ": "hmp3OjtL/EgTaApP1tZFBmH7pugsMhINkziSw2hALJwvycAbuaDWwka8yYiFTpx4YoB9V3+0uOSaUoerzUmAZPtDNaDJXb6XFop1cQ4B47sqLAGgQDMYQTUkmOD848KIaJJs9cSmJ6mnpJ3exzQGxAdB04t89/1O/w1cDnyilFU=",
    "ディナー": "Z2sMt/mVYmkhaqkYdIGfVVW3SF1pDmuUYO9cRxtccnlV7kgK7SOpi0fRQdpb266lDQp8rMSgIN5src670FbzN/3H5XkH6LeQTJScREFH8rHj1RhP/psxoTDh2N4fywhsv+SUN8l0nmnXZ9Q5xzl4HQdB04t89/1O/w1cDnyilFU=",
    "ベーグル": "aHnqYPGLV2yOqW80wEtnyV1BmixOyd6R/pdp4iQrAxK3qacd2eYPMwe0P9jKDuyzB1aJoZJII2YpLUGnrRhKybcZ9vhB72mCIugirf/kCU/Ebcr0IyvPBrfExwc+eUcYFrTvR6Dv1AvsVX28jvuESgdB04t89/1O/w1cDnyilFU="
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

    message = "🆘シフトご協力お願いします🆘\n\n"

    for record in records:
        date_display = record["date_display"]
        time_range = record["time_range"]
        minus_count = record["minus_count"]

        suffix = "🆘" if date_display in urgent_days else ""
        message += f"{date_display} {time_range} ▲{minus_count}人{suffix}\n"

    message += "\nーーーーーーーーー\n\n"

    # カテゴリ別 担当者名
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
    payload = {"to": group_id, "messages": [{"type": "text", "text": message.strip()}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers_line, json=payload)

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

