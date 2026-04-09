# nit-portal

NITポータルから個人向けデータを取得するための作業用リポジトリです。

## 使い方

`.env` に以下を入れます。

```env
USER_NAME=...
PASSWORD=...
DATABASE_URL=sqlite:///data/nit_portal.db
CREDENTIALS_ENCRYPTION_KEY=...
```

学生時間割をJSONで取得します。

```bash
python3 scripts/fetch_timetable.py
```

掲示板の全表示一覧をJSONで取得します。

```bash
python3 scripts/fetch_notices.py
```

ポータルの時間割と掲示詳細をRDBへ同期します。

```bash
python3 scripts/sync_portal.py
```

同期後のDBから公開用JSONを書き出します。

```bash
python3 scripts/export_public_data.py
```

同期と公開用JSON出力をまとめて実行します。

```bash
python3 scripts/sync_and_export.py
```

複数ユーザーを追加します。`TARGET_PORTAL_PASSWORD` は環境変数から渡します。

```bash
TARGET_PORTAL_PASSWORD=... python3 scripts/add_portal_user.py --display-name "Taro" --portal-user-name "s123456"
```

登録済みの有効ユーザーを一括同期します。

```bash
python3 scripts/sync_all_users.py
```

`DATABASE_URL` を変えるとSQLite以外へ切り替えられます。将来PostgreSQLへ移す場合も同じスキーマを使えます。

`notices` テーブルには本文だけでなく、通知の出所タブ、詳細リンクID群、差分検知用の `content_hash`、`first_seen_at`、`last_seen_at`、`content_updated_at` を保存します。複数ユーザー対応のため `users` と `portal_credentials` テーブルも追加してあり、資格情報は `CREDENTIALS_ENCRYPTION_KEY` で暗号化して保存します。既存DBに対しても不足列は自動で追加します。

`public/api/` には `notices.json`、`timetable.json`、`status.json` を出力します。静的ホスティングへそのまま載せられるので、無料構成ではこのJSONを配る形が一番扱いやすいです。

## 自動同期

GitHub Actions は [sync-public-data.yml](/Users/uyuyu/Developer/ikeyu-dev/nit-portal/.github/workflows/sync-public-data.yml) で 6 時間ごとに `scripts/sync_and_export.py` を実行します。GitHub のリポジトリ Secrets に `USER_NAME`、`PASSWORD`、必要なら `CREDENTIALS_ENCRYPTION_KEY` を設定してください。

このワークフローは `public/api/` だけをコミットします。Vercel から Next.js を配信する場合は、この `public/api/` をそのまま参照できます。
