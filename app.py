"""
にじさんじ・ホロライブ・ぶいすぽ 配信一覧ビューア

実行方法:
  export HOLODEX_API_KEY=xxxxx   # https://holodex.net/ で無料発行
  streamlit run app.py
"""
from collections import defaultdict
from datetime import datetime

import streamlit as st

from holodex_client import ORGS, fetch_live_and_upcoming

st.set_page_config(page_title="配信ウォッチャー", page_icon="🔴", layout="wide")

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def parse_start(v: dict):
    raw = v.get("start_actual") or v.get("start_scheduled")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return None


def format_date_header(d) -> str:
    return f"{d.month}月{d.day}日({WEEKDAY_JP[d.weekday()]})"


st.title("🔴 にじさんじ / ホロライブ / ぶいすぽ 配信ウォッチャー")
st.caption("Powered by Holodex API")

# --- サイドバー: フィルタ ---
with st.sidebar:
    st.header("フィルタ")
    selected_orgs = st.multiselect("箱を選択", ORGS, default=ORGS)
    keyword = st.text_input("推し検索(チャンネル名の一部)", "")
    status_filter = st.radio("表示状態", ["すべて", "配信中のみ", "配信予定のみ"], index=0)
    refresh = st.button("🔄 最新の情報に更新")

if not selected_orgs:
    st.warning("左のサイドバーで箱を1つ以上選んでください。")
    st.stop()


@st.cache_data(ttl=60)
def load_videos(orgs):
    return fetch_live_and_upcoming(list(orgs))


if refresh:
    load_videos.clear()

videos = load_videos(tuple(selected_orgs))

if keyword:
    videos = [
        v for v in videos if keyword.lower() in v.get("channel", {}).get("name", "").lower()
    ]

live_videos = [v for v in videos if v.get("status") == "live"]
upcoming_videos = [v for v in videos if v.get("status") == "upcoming"]

# 日付ごとにグルーピング(配信予定用)
by_date = defaultdict(list)
for v in upcoming_videos:
    dt = parse_start(v)
    if dt:
        by_date[dt.date()].append((dt, v))

available_dates = sorted(by_date.keys())

with st.sidebar:
    if available_dates:
        date_labels = {format_date_header(d): d for d in available_dates}
        selected_labels = st.multiselect(
            "配信予定日で絞る(未選択=全日程)", list(date_labels.keys())
        )
        selected_dates = {date_labels[label] for label in selected_labels} or set(available_dates)
    else:
        selected_dates = set()

c1, c2 = st.columns(2)
c1.metric("配信中", len(live_videos))
c2.metric("配信予定", len(upcoming_videos))
st.divider()


def render_video_card(v):
    channel = v.get("channel", {})
    title = v.get("title", "(タイトル不明)")
    video_id = v.get("id")
    org = v.get("_org", "")
    photo = channel.get("photo")
    if photo:
        st.image(photo, width=72)
    st.markdown(f"`[{org}]` **{channel.get('name', '不明')}**")
    st.markdown(f"[{title}](https://www.youtube.com/watch?v={video_id})")


# --- 配信中セクション(常に上部・日付フィルタの影響を受けない) ---
if status_filter in ("すべて", "配信中のみ") and live_videos:
    st.subheader("🔴 現在、配信中！")
    cols = st.columns(3)
    for i, v in enumerate(live_videos):
        with cols[i % 3]:
            render_video_card(v)
    st.divider()

# --- 配信予定セクション(日付→時間帯でグルーピング) ---
if status_filter in ("すべて", "配信予定のみ"):
    st.subheader("🕒 今後の予定")
    if not available_dates:
        st.info("配信予定が見つかりませんでした。")
    for date in available_dates:
        if date not in selected_dates:
            continue
        st.markdown(f"### {format_date_header(date)}")

        by_time = defaultdict(list)
        for dt, v in by_date[date]:
            by_time[dt.strftime("%H:%M")].append(v)

        for time_str in sorted(by_time.keys()):
            st.markdown(
                f"<div style='background:#1f77b4;color:white;padding:6px 12px;"
                f"border-radius:6px;font-weight:bold;margin:8px 0;'>{time_str} 〜</div>",
                unsafe_allow_html=True,
            )
            vids = by_time[time_str]
            cols = st.columns(min(len(vids), 3) or 1)
            for i, v in enumerate(vids):
                with cols[i % len(cols)]:
                    render_video_card(v)
        st.divider()
