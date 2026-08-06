"""
Holodexからのデータ取得に失敗した時だけSlackに通知するスクリプト。
GitHub Actionsで定期実行される想定 (.github/workflows/notify.yml)。

必要な環境変数:
  HOLODEX_API_KEY   Holodex APIキー
  SLACK_WEBHOOK_URL Slack Incoming Webhook URL
"""
import os
import sys

import requests

from holodex_client import ORGS, fetch_live_and_upcoming_with_status


def send_slack_alert(webhook_url: str, message: str) -> None:
    payload = {"text": f"🚨 *配信ウォッチャー: データ取得エラー*\n{message}"}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()


def main() -> int:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL が設定されていません。", file=sys.stderr)
        return 1

    videos, failed_orgs = fetch_live_and_upcoming_with_status(ORGS)

    if failed_orgs:
        message = (
            f"以下のorgでHolodexからのデータ取得に失敗しました: {', '.join(failed_orgs)}\n"
            "しばらく経っても直らない場合はHolodex側の障害やAPIキーの期限切れの可能性があります。"
        )
        try:
            send_slack_alert(webhook_url, message)
            print(f"エラー通知を送信しました: {failed_orgs}")
        except requests.RequestException as e:
            print(f"Slack送信自体にも失敗: {e}", file=sys.stderr)
            return 1
        return 1

    print(f"取得成功。現在の配信/予定件数: {len(videos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
