import streamlit as st
from datetime import datetime, time
import json
import requests

st.set_page_config(page_title="シフトマイナス管理システム", layout="wide")

DATA_FILE = "minus_data.json"

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

LINE_ACCESS_TOKEN = "lszhy7usClELTs8XrUl5WUgz2eczgYDv8ej9BdTK4wGa1bH27e8Yaw1wErd8bieRYWEkjTvJXwmVv3c7rTVw/K7aUS4HOCwxd5jTpnohzUxn7+0eCRRAmlH6+LIJow4sAgPK8jELBzasnl9Nqo9/kAdB04t89/1O/w1cDnyilFU="

CATEGORY_TO_GROUPID = {
    "ランチ": "REDACTED_LINE_GROUP_ID",
    "ディナー": "REDACTED_LINE_GROUP_ID",
    "ベーグル": "REDACTED_LINE_GROUP_ID"
}

st.markdown("""
    <style>
    /* number_input（input[type=number]）の見た目カスタム */
    input[type=number] {
        background-color: #ffffff !important;
        border: 1px solid #333333 !important;
        color: #000000 !important;
        padding: 6px;
        border-radius: 6px;
    }

    /* フォーカス時のスタイル（オプション） */
    input[type=number]:focus {
        border-color: #006a38 !important;
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(0, 106, 56, 0.2);
    }
    </style>
""", unsafe_allow_html=True)

def send_group_notification(group_key, categories):
    items = [item for item in st.session_state.minus_list if item['カテゴリ'] in categories]
    if not items:
        return

    items_sorted = sorted(items, key=lambda x: (x['カテゴリ'], x['日付元']))
    category_map = {}
    for item in items_sorted:
        cat = item['カテゴリ']
        if cat not in category_map:
            category_map[cat] = []
        category_map[cat].append(item)

    message = "🆘現在のマイナス日🆘\n"
    for cat, records in category_map.items():
        message += f"\n{cat}\n"
        for r in records:
            message += f"{r['日付']} {r['時間帯']} ▲{r['マイナス人数']}人\n"

    group_id = CATEGORY_TO_GROUPID[group_key]
    if not group_id:
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": message.strip()}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)

if "minus_list" not in st.session_state:
    st.session_state.minus_list = load_data()

color_map = {
    "ランチ【ホール】": "#ffe4b5",
    "ランチ【キッチン】": "#ffe4b5",
    "ディナー【ホール】": "#d0eaff",
    "ディナー【キッチン】": "#d0eaff",
    "ベーグル": "#e1ffd0"
}

category_groups = {
    "ランチ": ["ランチ【ホール】", "ランチ【キッチン】"],
    "ディナー": ["ディナー【ホール】", "ディナー【キッチン】"],
    "ベーグル": ["ベーグル"]
}

# --- 画面表示スタート ---
st.markdown("""
    <style>
        .main > div {
            max-width: 960px;
            margin: auto;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h1 style='text-align: center; color: #333333; font-family: "Segoe UI", sans-serif; font-size:32px;'>
        シフトマイナス管理
    </h1>
""", unsafe_allow_html=True)

st.markdown("""
    <h2 style='color: #444; margin: 30px 0; border-left: 5px solid #006a38; border-bottom:1px solid #006a38; padding: 1% 1% 1% 3%; font-size: 25px;'>マイナスの新規登録</h2>
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    category = st.selectbox("カテゴリ", [
        "ランチ【ホール】",
        "ランチ【キッチン】",
        "ディナー【ホール】",
        "ディナー【キッチン】",
        "ベーグル"
    ])
with col2:
    minus_date = st.date_input("日付", value=datetime.today())
with col3:
    start_time = st.time_input("開始", value=time(9, 0))
with col4:
    end_time = st.time_input("終了", value=time(13, 0))
with col5:
    minus_count = st.selectbox("人数", options=list(range(1, 6)), index=0)

if st.button("登録", use_container_width=True):
    new_data = {
        "カテゴリ": category,
        "日付": minus_date.strftime("%m/%d"),
        "時間帯": f"{start_time.strftime('%H:%M')}〜{end_time.strftime('%H:%M')}",
        "マイナス人数": minus_count,
        "日付元": minus_date.strftime("%Y-%m-%d")
    }
    st.session_state.minus_list.append(new_data)
    save_data(st.session_state.minus_list)
    st.success("登録しました！")


st.divider()

# --- 現在募集中のマイナス日 ---
st.markdown("""
    <h2 style='color: #444; margin: 30px 0; border-left: 5px solid #006a38; border-bottom:1px solid #006a38; padding: 1% 1% 1% 3%; font-size: 25px;'>現在募集中のマイナス日</h2>
""", unsafe_allow_html=True)

selected_group = st.selectbox("カテゴリを選択", ["ランチ", "ディナー", "ベーグル"])

subcategories = category_groups[selected_group]

found = False
for i, data in enumerate(st.session_state.minus_list):
    if data['カテゴリ'] not in subcategories:
        continue
    found = True
    with st.container():
        st.markdown(f"""
            <div style='background-color:{color_map[data['カテゴリ']]};
                        padding:15px;border-radius:12px;margin-bottom:10px;'>
                <h4 style='margin:0;'>{data['カテゴリ']}（{data['日付']}）</h4>
                <p style='margin:0;'>時間帯: {data['時間帯']}</p>
                <p style='margin:0;'>あと <strong>{data['マイナス人数']}</strong> 人必要</p>
            </div>
        """, unsafe_allow_html=True)

        filled = st.number_input(
            f"埋まった人数を入力（{data['カテゴリ']} - {data['日付']}）",
            min_value=0,
            max_value=data['マイナス人数'],
            key=f"input_{i}"
        )
        if filled > 0:
            if st.button(f"反映（{data['カテゴリ']} - {data['日付']}）", key=f"btn_{i}"):
                data['マイナス人数'] -= filled
                if data['マイナス人数'] <= 0:
                    st.session_state.minus_list.pop(i)
                save_data(st.session_state.minus_list)
                st.rerun()

if not found:
    st.write("現在募集中のマイナスはありません。")

if st.button(f"{selected_group}マイナス募集をする", use_container_width=True, key=f"notify_{selected_group}"):
    send_group_notification(selected_group, subcategories)
    st.success("通知を送信しました！")
