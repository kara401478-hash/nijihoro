"""
Holodex API (https://docs.holodex.net/) の薄いラッパー。
にじさんじ・ホロライブなど VTuber の配信中/配信予定情報を取得する。

APIキーは無料で発行できる:
  1. https://holodex.net/ にログイン
  2. 右上アカウントアイコン → Account Settings → API Key
"""
import os
import requests

BASE_URL = "https://holodex.net/api/v2"

# よく使う org (グループ) 名。Holodex側の指定に合わせる。
# ぶいすぽ!はHolodex上では "VSPO!" 表記。もし拾えない場合は
# https://holodex.net/ の左上プルダウンで実際の表記を確認して調整してください。
ORGS = ["Nijisanji", "Hololive", "VSPO!"]


def _get_api_key() -> str | None:
    return os.environ.get("HOLODEX_API_KEY")


def _headers() -> dict:
    key = _get_api_key()
    headers = {"user-agent": "vtuber-live-tracker/1.0"}
    if key:
        headers["X-APIKEY"] = key
    return headers


def fetch_live_and_upcoming(orgs: list[str], limit: int = 50) -> list[dict]:
    """
    指定した org (複数可) の「配信中 + 配信予定」動画一覧を取得する。
    Holodexの /live エンドポイントは status=live,upcoming を返す。

    戻り値の各要素(抜粋):
      - id: YouTube動画ID
      - title: タイトル
      - status: "live" | "upcoming"
      - start_scheduled / start_actual: 開始時刻
      - channel: {name, id, photo, ...}
    """
    results: list[dict] = []
    for org in orgs:
        params = {
            "org": org,
            "status": "live,upcoming",
            "limit": limit,
            "sort": "start_scheduled",
        }
        try:
            resp = requests.get(
                f"{BASE_URL}/live", params=params, headers=_headers(), timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data:
                item["_org"] = org
            results.extend(data)
        except requests.RequestException as e:
            print(f"[holodex_client] {org} の取得に失敗: {e}")
    return results


def fetch_currently_live(orgs: list[str], limit: int = 50) -> list[dict]:
    """live中のものだけに絞って取得(通知botで使う)"""
    all_items = fetch_live_and_upcoming(orgs, limit=limit)
    return [v for v in all_items if v.get("status") == "live"]
