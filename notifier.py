"""
Holodexからのデータ取得に失敗した時、または分類ミスが疑われるデータ
(複数orgにまたがるチャンネル)を検知した時にSlackへ通知するスクリプト。
GitHub Actionsで定期実行される想定 (.github/workflows/notify.yml)。

必要な環境変数:
  HOLODEX_API_KEY   Holodex APIキー
  SLACK_WEBHOOK_URL Slack Incoming Webhook URL
"""
import os
import sys

import requests

from holodex_client import ORGS, dedupe_videos, fetch_live_and_upcoming_with_status


def send_slack_alert(webhook_url: str, message: str) -> None:
    payload = {"text": f"🚨 *配信ウォッチャー: データ異常検知*\n{message}"}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()


def main() -> int:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL が設定されていません。", file=sys.stderr)
        return 1

    videos, failed_orgs = fetch_live_and_upcoming_with_status(ORGS)
    problems: list[str] = []

    if failed_orgs:
        problems.append(
            f"以下のorgでHolodexからのデータ取得に失敗しました: {', '.join(failed_orgs)}\n"
            "しばらく経っても直らない場合はHolodex側の障害やAPIキーの期限切れの可能性があります。"
        )

    deduped = dedupe_videos(videos)
    cross_org = [v for v in deduped if "/" in v.get("_org", "")]
    if cross_org:
        names = sorted({
            v.get("channel", {}).get("name", "不明") for v in cross_org
        })
        problems.append(
            "複数orgにまたがるチャンネルを検知しました(Holodex側の分類ミスの可能性): "
            + ", ".join(names)
            + "\nアプリ側では一旦非表示にしていますが、無関係なチャンネルであれば"
            "app.pyのMANUALLY_EXCLUDED_CHANNEL_NAMESに追記してください。"
            "\n※このアラートは解消されるまで実行のたびに繰り返し届きます。"
        )

    if problems:
        detail = "\n\n".join(problems)
        print("=== 検知した内容 ===")
        print(detail)
        print("====================")
        try:
            send_slack_alert(webhook_url, detail)
            print("Slackへの通知も送信しました。")
        except requests.RequestException as e:
            print(f"Slack送信自体にも失敗: {e}", file=sys.stderr)
            return 1
        return 1

    print(f"取得成功。現在の配信/予定件数: {len(videos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
