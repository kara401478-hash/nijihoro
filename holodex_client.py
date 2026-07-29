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

# 画面/フィルタに表示する箱の名前(表示用の名称)。
# ぶいすぽ(VSPO)はHolodex側で正式なorg対応が確認できなかったため対象外にしています。
ORGS = ["Nijisanji", "Hololive"]

ORG_API_CANDIDATES: dict[str, list[str]] = {
    "Nijisanji": ["Nijisanji"],
    "Hololive": ["Hololive"],
}


def _get_api_key() -> str | None:
    return os.environ.get("HOLODEX_API_KEY")


def _headers() -> dict:
    key = _get_api_key()
    headers = {"user-agent": "vtuber-live-tracker/1.0"}
    if key:
        headers["X-APIKEY"] = key
    return headers


def _fetch_for_org_candidate(org_param: str, limit: int) -> list[dict]:
    params = {
        "org": org_param,
        "status": "live,upcoming",
        "limit": limit,
        "sort": "start_scheduled",
    }
    resp = requests.get(
        f"{BASE_URL}/live", params=params, headers=_headers(), timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def fetch_live_and_upcoming(orgs: list[str], limit: int = 50) -> list[dict]:
    """
    指定した org (表示名, 複数可) の「配信中 + 配信予定」動画一覧を取得する。
    Holodexの /live エンドポイントは status=live,upcoming を返す。

    表記ゆれのある org (例: VSPO) は ORG_API_CANDIDATES の候補を順番に試し、
    最初にヒットしたものを使う。

    戻り値の各要素(抜粋):
      - id: YouTube動画ID
      - title: タイトル
      - status: "live" | "upcoming"
      - start_scheduled / start_actual: 開始時刻
      - channel: {name, id, photo, ...}
      - _org: 表示用の箱名(ORGSと同じ表記に統一)
    """
    results: list[dict] = []
    for org in orgs:
        candidates = ORG_API_CANDIDATES.get(org, [org])
        org_data: list[dict] = []
        for candidate in candidates:
            try:
                data = _fetch_for_org_candidate(candidate, limit)
            except requests.RequestException as e:
                print(f"[holodex_client] {org}({candidate}) の取得に失敗: {e}")
                continue
            if data:
                org_data = data
                break  # ヒットしたらそれ以上候補を試さない
        for item in org_data:
            item["_org"] = org  # 表示は統一名にする
        results.extend(org_data)
    return results


def fetch_currently_live(orgs: list[str], limit: int = 50) -> list[dict]:
    """live中のものだけに絞って取得(通知botで使う)"""
    all_items = fetch_live_and_upcoming(orgs, limit=limit)
    return [v for v in all_items if v.get("status") == "live"]
