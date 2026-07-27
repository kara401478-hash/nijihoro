"""
にじさんじ・ホロライブ・ぶいすぽ 配信一覧ビューア

実行方法:
  export HOLODEX_API_KEY=xxxxx   # https://holodex.net/ で無料発行
  streamlit run app.py
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import streamlit as st

from holodex_client import ORGS, fetch_live_and_upcoming

st.set_page_config(page_title="配信ウォッチャー", page_icon="🔴", layout="wide")

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# 日本時間はDSTが無いので固定オフセットでOK(サーバーのタイムゾーンに依存しない)
JST = timezone(timedelta(hours=9))


def parse_start(v: dict):
    raw = v.get("start_actual") or v.get("start_scheduled")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(JST)
    except ValueError:
        return None


def dedupe_videos(items: list[dict]) -> list[dict]:
    """複数org検索で同じ動画(コラボ等)が重複した場合に1枚へ統合する"""
    merged: dict[str, dict] = {}
    for v in items:
        vid = v.get("id")
        if not vid:
            continue
        if vid not in merged:
            merged[vid] = dict(v)
        else:
            existing_orgs = merged[vid]["_org"].split("/")
            this_org = v.get("_org", "")
            if this_org and this_org not in existing_orgs:
                merged[vid]["_org"] = "/".join(existing_orgs + [this_org])
    return list(merged.values())


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
videos = dedupe_videos(videos)

if keyword:
    videos = [
        v for v in videos if keyword.lower() in v.get("channel", {}).get("name", "").lower()
    ]

live_videos = [v for v in videos if v.get("status") == "live"]
upcoming_videos = [v for v in videos if v.get("status") == "upcoming"]

# 日付ごとにグルーピング(配信予定用)。予定時刻を過ぎてまだliveになっていない
# ものは「押し配信(遅延)」として別枠にする。ただし何時間も放置されている
# ものはHolodex側のデータが更新されていない古いゴミの可能性が高いので除外する。
STALE_THRESHOLD = timedelta(hours=3)
now_jst = datetime.now(JST)
by_date = defaultdict(list)
overdue = []
for v in upcoming_videos:
    dt = parse_start(v)
    if not dt:
        continue
    diff = now_jst - dt
    if diff > STALE_THRESHOLD:
        continue  # 古すぎるデータは表示しない
    if dt < now_jst:
        overdue.append((dt, v))
    else:
        by_date[dt.date()].append((dt, v))
overdue.sort(key=lambda pair: pair[0])

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

displayed_upcoming_count = len(overdue) + sum(len(v) for v in by_date.values())

c1, c2 = st.columns(2)
c1.metric("配信中", len(live_videos))
c2.metric("配信予定", displayed_upcoming_count)
st.divider()


def render_video_card(v):
    channel = v.get("channel", {})
    title = v.get("title", "(タイトル不明)")
    video_id = v.get("id")
    org = v.get("_org", "")
    photo = channel.get("photo", "")
    name = channel.get("name", "不明")
    thumb = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
    url = f"https://www.youtube.com/watch?v={video_id}"

    st.markdown(
        f"""
        <div style="border:1px solid #333;border-radius:10px;overflow:hidden;
                    height:250px;display:flex;flex-direction:column;
                    margin-bottom:14px;background:#0e1117;">
          <img src="{thumb}" style="width:100%;height:110px;object-fit:cover;">
          <div style="padding:8px 10px;flex:1;overflow:hidden;">
            <div style="font-size:11px;color:#8ab4f8;margin-bottom:2px;">[{org}]</div>
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
              <img src="{photo}" style="width:20px;height:20px;border-radius:50%;
                          object-fit:cover;flex-shrink:0;">
              <span style="font-size:13px;font-weight:bold;white-space:nowrap;
                          overflow:hidden;text-overflow:ellipsis;">{name}</span>
            </div>
            <a href="{url}" target="_blank" style="text-decoration:none;color:#ddd;">
              <div style="font-size:12.5px;line-height:1.4;display:-webkit-box;
                          -webkit-line-clamp:3;-webkit-box-orient:vertical;
                          overflow:hidden;">{title}</div>
            </a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- 配信中セクション(常に上部・日付フィルタの影響を受けない) ---
if status_filter in ("すべて", "配信中のみ") and live_videos:
    st.subheader("🔴 現在、配信中！")
    cols = st.columns(3)
    for i, v in enumerate(live_videos):
        with cols[i % 3]:
            render_video_card(v)
    st.divider()

# --- 押し配信(予定時刻を過ぎたがまだ開始していない) ---
if status_filter in ("すべて", "配信予定のみ") and overdue:
    st.subheader("⏰ まもなく開始？(予定時刻超過)")
    cols = st.columns(3)
    for i, (dt, v) in enumerate(overdue):
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
