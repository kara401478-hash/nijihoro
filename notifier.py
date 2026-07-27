"""
新しく配信が始まったライバーを検知して Slack に通知するスクリプト。
GitHub Actions で定期実行される想定 (.github/workflows/notify.yml)。

必要な環境変数:
  HOLODEX_API_KEY   Holodex APIキー
  SLACK_WEBHOOK_URL Slack Incoming Webhook URL

状態管理:
  notified.json に「前回時点で通知済み(=live中)だった動画ID」を保存し、
  差分(新しく live になったもの)だけ通知する。
  配信が終了したIDは次回実行時に自然と消える(現在のlive集合で上書きするため)。
"""
import json
import os
import sys
from pathlib import Path

import requests

from holodex_client import ORGS, fetch_currently_live

STATE_FILE = Path(__file__).parent / "notified.json"


def load_notified_ids() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return set()


def save_notified_ids(ids: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8")


def send_slack_message(webhook_url: str, video: dict) -> None:
    channel = video.get("channel", {})
    title = video.get("title", "(タイトル不明)")
    video_id = video.get("id")
    org = video.get("_org", "")
    url = f"https://www.youtube.com/watch?v={video_id}"

    payload = {
        "text": f"🔴 *[{org}] {channel.get('name', '不明')}* が配信を開始しました！\n"
        f"*{title}*\n{url}"
    }
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()


def main() -> int:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL が設定されていません。", file=sys.stderr)
        return 1

    current_live = fetch_currently_live(ORGS)
    current_ids = {v["id"] for v in current_live if v.get("id")}

    notified_ids = load_notified_ids()
    new_lives = [v for v in current_live if v["id"] not in notified_ids]

    for video in new_lives:
        try:
            send_slack_message(webhook_url, video)
            print(f"通知送信: {video.get('channel', {}).get('name')} / {video.get('title')}")
        except requests.RequestException as e:
            print(f"Slack送信失敗: {e}", file=sys.stderr)

    # 現在liveの集合で上書き(終了した配信のIDは自然に消える)
    save_notified_ids(current_ids)
    print(f"現在の配信数: {len(current_ids)} / 新規通知: {len(new_lives)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
