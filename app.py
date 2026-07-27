"""
にじさんじ・ホロライブ配信一覧ビューア

実行方法:
  export HOLODEX_API_KEY=xxxxx   # https://holodex.net/ で無料発行
  streamlit run app.py
"""
from datetime import datetime, timezone

import streamlit as st

from holodex_client import ORGS, fetch_live_and_upcoming

st.set_page_config(page_title="配信ウォッチャー", page_icon="🔴", layout="wide")

st.title("🔴 にじさんじ / ホロライブ 配信ウォッチャー")
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
def load_videos(orgs: tuple[str, ...]):
    return fetch_live_and_upcoming(list(orgs))


if refresh:
    load_videos.clear()

videos = load_videos(tuple(selected_orgs))

if keyword:
    videos = [
        v for v in videos if keyword.lower() in v.get("channel", {}).get("name", "").lower()
    ]

if status_filter == "配信中のみ":
    videos = [v for v in videos if v.get("status") == "live"]
elif status_filter == "配信予定のみ":
    videos = [v for v in videos if v.get("status") == "upcoming"]

live_count = sum(1 for v in videos if v.get("status") == "live")
upcoming_count = sum(1 for v in videos if v.get("status") == "upcoming")

c1, c2 = st.columns(2)
c1.metric("配信中", live_count)
c2.metric("配信予定", upcoming_count)

st.divider()

if not videos:
    st.info("該当する配信が見つかりませんでした。")

for v in videos:
    channel = v.get("channel", {})
    status = v.get("status")
    title = v.get("title", "(タイトル不明)")
    video_id = v.get("id")
    org = v.get("_org", "")

    start_raw = v.get("start_actual") or v.get("start_scheduled")
    start_str = ""
    if start_raw:
        try:
            dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).astimezone()
            start_str = dt.strftime("%m/%d %H:%M")
        except ValueError:
            start_str = start_raw

    badge = "🔴 配信中" if status == "live" else "🕒 配信予定"

    col1, col2 = st.columns([1, 5])
    with col1:
        photo = channel.get("photo")
        if photo:
            st.image(photo, width=64)
    with col2:
        st.markdown(
            f"**[{org}]** {badge}　`{start_str}`\n\n"
            f"**{channel.get('name', '不明')}**\n\n"
            f"[{title}](https://www.youtube.com/watch?v={video_id})"
        )
    st.divider()
