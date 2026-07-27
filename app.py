"""
にじさんじ・ホロライブ・ぶいすぽ 配信一覧ビューア

実行方法:
  export HOLODEX_API_KEY=xxxxx   # https://holodex.net/ で無料発行
  streamlit run app.py
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import streamlit as st

from holodex_client import ORGS, fetch_live_and_upcoming

st.set_page_config(page_title="配信ウォッチャー", page_icon="🔴", layout="wide")

# --- 季節テーマ(月に応じてバナーのグラデーションと絵文字を切り替え) ---
SEASON_THEMES = {
    "summer": {
        "grad": "linear-gradient(135deg,#00c6ff 0%,#0072ff 55%,#00b4d8 100%)",
        "bg": "linear-gradient(180deg,#d6f3ff 0%,#eefcff 260px,#ffffff 520px)",
        "emoji": "🌊☀️🍧",
        "label": "夏",
    },
    "autumn": {
        "grad": "linear-gradient(135deg,#f6d365 0%,#fda085 100%)",
        "bg": "linear-gradient(180deg,#fff2d9 0%,#fff8ec 260px,#ffffff 520px)",
        "emoji": "🍁🎑",
        "label": "秋",
    },
    "winter": {
        "grad": "linear-gradient(135deg,#5b86e5 0%,#36d1dc 100%)",
        "bg": "linear-gradient(180deg,#eaf6ff 0%,#f3fbff 260px,#ffffff 520px)",
        "emoji": "❄️⛄",
        "label": "冬",
    },
    "spring": {
        "grad": "linear-gradient(135deg,#ff9a9e 0%,#fecfef 100%)",
        "bg": "linear-gradient(180deg,#ffe9f0 0%,#fff3f7 260px,#ffffff 520px)",
        "emoji": "🌸🌷",
        "label": "春",
    },
}


def get_season() -> str:
    m = date.today().month
    if m in (6, 7, 8):
        return "summer"
    if m in (9, 10, 11):
        return "autumn"
    if m in (12, 1, 2):
        return "winter"
    return "spring"


THEME = SEASON_THEMES[get_season()]

st.markdown(
    """
    <style>
    /* NOTE: GithubIcon(Share/Fork等のツールバー)はStreamlit Community Cloud側が
       外側から被せているUIのため、アプリ内のCSSからは非表示にできません(仕様上の制約)。 */

    .vtube-banner {
        border-radius: 18px;
        padding: 18px 22px 22px 22px;
        margin-bottom: 18px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.18);
    }
    .vtube-banner-title {
        font-size: 1.6rem; font-weight: 800; color: #ffffff;
        text-shadow: 0 1px 3px rgba(0,0,0,0.25);
        margin: 0;
    }
    .vtube-banner-sub {
        font-size: 0.85rem; color: rgba(255,255,255,0.9);
        margin-top: 4px;
    }

    .vtube-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        overflow: hidden;
        height: 250px;
        display: flex;
        flex-direction: column;
        margin-bottom: 14px;
        background: #ffffff;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }
    .vtube-thumb { width: 100%; height: 110px; object-fit: cover; }
    .vtube-body { padding: 8px 10px; flex: 1; overflow: hidden; }
    .vtube-org { font-size: 11px; color: #0072ff; margin-bottom: 2px; font-weight: 600; }
    .vtube-channel-row {
        display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
    }
    .vtube-avatar {
        width: 20px; height: 20px; border-radius: 50%;
        object-fit: cover; flex-shrink: 0;
    }
    .vtube-name {
        font-size: 13px; font-weight: bold; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; color: #111;
    }
    .vtube-title {
        font-size: 12.5px; line-height: 1.4; display: -webkit-box;
        -webkit-line-clamp: 3; -webkit-box-orient: vertical;
        overflow: hidden; text-decoration: none; color: #333;
    }

    /* --- モバイル最適化(幅640px以下) --- */
    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
            padding-top: 1.2rem !important;
        }
        .vtube-banner { padding: 14px 16px 18px 16px; border-radius: 14px; }
        .vtube-banner-title { font-size: 1.15rem !important; line-height: 1.3 !important; }
        .vtube-banner-sub { font-size: 0.75rem !important; }
        h3 { font-size: 1.05rem !important; }
        .vtube-card { height: 210px; }
        .vtube-thumb { height: 85px; }
        .vtube-name { font-size: 12px; }
        .vtube-title { font-size: 11.5px; -webkit-line-clamp: 2; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <style>
    [data-testid="stAppViewContainer"], .stApp {{
        background: {THEME['bg']};
        background-attachment: fixed;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

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


st.markdown(
    f"""
    <div class="vtube-banner" style="background:{THEME['grad']};">
      <p class="vtube-banner-title">🔴 にじさんじ / ホロライブ / ぶいすぽ 配信ウォッチャー</p>
    </div>
    """,
    unsafe_allow_html=True,
)

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

    st.divider()
    st.caption("セキュリティ")
    st.markdown(
        "[![CodeQL](https://github.com/kara401478-hash/nijihoro/actions/workflows/codeql.yml/badge.svg)]"
        "(https://github.com/kara401478-hash/nijihoro/actions/workflows/codeql.yml)\n\n"
        "[![Dependency Audit](https://github.com/kara401478-hash/nijihoro/actions/workflows/dependency-audit.yml/badge.svg)]"
        "(https://github.com/kara401478-hash/nijihoro/actions/workflows/dependency-audit.yml)"
    )

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
        <div class="vtube-card">
          <img class="vtube-thumb" src="{thumb}">
          <div class="vtube-body">
            <div class="vtube-org">[{org}]</div>
            <div class="vtube-channel-row">
              <img class="vtube-avatar" src="{photo}">
              <span class="vtube-name">{name}</span>
            </div>
            <a href="{url}" target="_blank" class="vtube-title">{title}</a>
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
