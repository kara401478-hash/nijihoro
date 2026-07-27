# vtuber-live-tracker

[![CodeQL](https://github.com/kara401478-hash/nijihoro/actions/workflows/codeql.yml/badge.svg)](https://github.com/kara401478-hash/nijihoro/actions/workflows/codeql.yml)
[![Dependency Audit](https://github.com/kara401478-hash/nijihoro/actions/workflows/dependency-audit.yml/badge.svg)](https://github.com/kara401478-hash/nijihoro/actions/workflows/dependency-audit.yml)

にじさんじ・ホロライブの配信中/配信予定を一覧表示するWebアプリ + 配信開始をSlackに通知するBot。
データソースは [Holodex API](https://docs.holodex.net/) を利用。

## 構成

```
app.py              Streamlit Webアプリ(一覧表示)
notifier.py         配信開始検知 → Slack通知(GitHub Actionsで定期実行)
holodex_client.py   Holodex APIの共通ラッパー
notified.json       通知済み配信IDの状態ファイル(notifier.pyが自動更新)
.github/workflows/notify.yml  10分毎に自動実行するワークフロー
```

## セットアップ

### 1. Holodex APIキーを取得
1. https://holodex.net/ にログイン(Google/Discord/Xでログイン可)
2. 右上アカウントアイコン → Account Settings → API Key を発行

### 2. Slack Incoming Webhookを作成
1. Slack App管理画面 (https://api.slack.com/apps) → Create New App
2. "Incoming Webhooks" を有効化 → 通知したいチャンネルを選んでWebhook URLを発行

### 3. ローカルでWebアプリを動かす

```bash
pip install -r requirements.txt
export HOLODEX_API_KEY=xxxxx
streamlit run app.py
```

### 4. 通知Botをデプロイ(GitHub Actions)

1. このリポジトリをGitHubにpush
2. Settings → Secrets and variables → Actions で以下を登録
   - `HOLODEX_API_KEY`
   - `SLACK_WEBHOOK_URL`
3. Actionsタブから "Live Notify" を手動実行(workflow_dispatch)して動作確認
   → 以降は10分毎に自動実行される

### 5. Webアプリを公開したい場合
[Streamlit Community Cloud](https://streamlit.io/cloud) にこのリポジトリを連携し、
Secrets に `HOLODEX_API_KEY` を設定すればブラウザから誰でもアクセスできる状態で公開できる。

## セキュリティ

このリポジトリでは以下を自動実行しています(mainブランチへのpush/PR時 + 毎週月曜):

- **CodeQL**: コード自体の静的解析(危険なコードパターンの検出)
- **pip-audit**: `requirements.txt` の依存パッケージに既知の脆弱性(CVE)がないかチェック
- **Dependabot**: 依存パッケージの更新を毎週自動チェックし、必要ならPRを作成

上のバッジが緑(passing)であれば、直近のスキャンで問題は見つかっていません。
初回はActionsタブで手動実行(workflow_dispatchが無いものは次のpushかスケジュールで走ります)して緑になるか確認してください。

## カスタマイズのヒント

- `holodex_client.py` の `ORGS` に箱を追加/削除すれば対象グループを変更できる
  (Holodex対応の他グループ名は https://holodex.net/ のプルダウンで確認可能)
- 通知頻度を上げたい場合は `notify.yml` の cron を調整(ただしGitHub Actionsの
  scheduleは最短でも実際は数分〜十数分の遅延が発生することがある点に注意)
- お気に入りチャンネルだけ通知したい場合は `notifier.py` で
  `current_live` をチャンネル名/IDでフィルタすればOK
