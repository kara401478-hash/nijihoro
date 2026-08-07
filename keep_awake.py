"""
Streamlit Community Cloud はアクセスが無いと12時間でスリープするため、
定期的にブラウザで実際にアクセスして起こしっぱなしにするスクリプト。
GitHub Actionsで定期実行される想定 (.github/workflows/keep-awake.yml)。

単純なHTTP GET(curlなど)だとStreamlit側の"シェルページ"が返るだけで
実際のアクセスとしてカウントされないことがあるため、Playwrightで
ブラウザを起動してJSも実行させた上でアクセスする。
"""
import sys

from playwright.sync_api import sync_playwright

APP_URL = "https://nijihoro-sbpyks2licdyfb4qu8aezs.streamlit.app"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(APP_URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"アクセス自体に失敗: {e}", file=sys.stderr)
            browser.close()
            return 1

        # スリープ中だと「起こす」ボタンが表示されるのでクリックする
        try:
            wake_button = page.get_by_text("Yes, get this app back up!", exact=False)
            if wake_button.is_visible(timeout=5000):
                print("スリープ中だったので起こしボタンを押します。")
                wake_button.click()
                page.wait_for_timeout(15000)
        except Exception:
            # ボタンが無い = 既に起きている、ということなので問題なし
            pass

        print("アプリへのアクセス完了。")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
