# デプロイ手順

FMSv2はFlask + SQLiteの単一プロセスアプリ。旧版（`FMS-main/`、PHP + MariaDB）と違い外部DBサーバーが不要なので、配置は大幅に簡単になっている。

## 0. 前提

- Python 3.11以降
- 本番運用では`flask run`（開発用サーバー）を使わない。`waitress`（Windows/Linux両対応の純Python製WSGIサーバー）または`gunicorn`（Linux専用）などの本番用WSGIサーバー経由で`wsgi:app`を起動する

## 1. ファイルの配置

```
/path/to/FMSv2/
├── .env              ← .env.example からコピーして作成（手順2）
├── instance/         ← SQLiteのDBファイルを置く（.gitignore対象）
├── logs/             ← アクセスログ（.gitignore対象）
└── wsgi.py           ← エントリーポイント
```

`instance/`と`logs/`はアプリ実行ユーザーが書き込み可能である必要がある。

## 2. 依存インストールと`.env`の作成

```
pip install -r requirements.txt
cp .env.example .env
```

`.env`の各項目:

| 変数 | 必須 | 説明 |
|---|---|---|
| `FMS_SECRET_KEY` | ○ | 未設定だと起動時に`RuntimeError`で落ちる。`python -c "import secrets; print(secrets.token_hex(32))"`等で生成する |
| `FMS_DB_PATH` | - | 既定`instance/fms.db` |
| `FMS_LOG_PATH` | - | 既定`logs/app_access_log.txt` |
| `FMS_HEALTHCHECK_TOKEN` | - | `/healthcheck?token=...`用。未設定だと常に404 |
| `FMS_FORCE_HTTPS` | HTTPS運用時は必須 | `1`にするとセッションクッキーにSecure属性が付き、HSTSヘッダーも送信される。**HTTPSでリバースプロキシ配下に置くなら必ず`1`にする**（`0`のままだとセッションクッキーが平文送信されうる） |
| `FMS_TRUSTED_PROXY_COUNT` | リバースプロキシ配下なら必須 | リバースプロキシを何段挟むか。`0`（既定）だと`X-Forwarded-For`等を一切信用しない＝プロキシ配下だとログイン試行制限のIP判定が全リクエスト同一IPになり実質機能しなくなる。nginx等を1段挟むなら`1`にする |
| `FMS_MAX_CONTENT_LENGTH` | - | リクエストボディの上限バイト数。既定12MB |
| `FMS_GEMINI_API_KEY` 等 | - | レシート読取/店名候補/チャット入力機能用。未設定でも他機能は動く |

> **重要な制約**: `.env`は`wsgi.py`が`python-dotenv`で読み込む。`flask --app fmsv2:create_app run`のように`wsgi.py`を経由しない起動方法では`.env`は読み込まれない（`FMS_SECRET_KEY`未設定でアプリが起動失敗する）。本番でも`wsgi.py`経由（`waitress-serve --call wsgi:app`ではなく`waitress-serve wsgi:app`、または`gunicorn wsgi:app`）で起動すること。

## 3. DBの初期化

```
flask --app wsgi init-db
```

`schema.sql` + `seed.sql`（初期カテゴリー/決済手段マスタ）が投入される。既存DBに対して再実行しても`CREATE TABLE IF NOT EXISTS`なので安全（データは消えない）。

## 4. 起動（本番）

Linux（gunicorn、ワーカー数はCPU/メモリに応じて調整。個人用途なら1〜2で十分）:
```
gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app
```

Windows/クロスプラットフォーム（waitress）:
```
waitress-serve --host=0.0.0.0 --port=8000 wsgi:app
```

いずれもリバースプロキシ（nginx等）でTLS終端し、`FMS_FORCE_HTTPS=1`・`FMS_TRUSTED_PROXY_COUNT=1`をセットする構成を推奨する。

## 5. リバースプロキシ配下に置く場合の注意

- nginxで`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`のように転送する
- アプリ側は`FMS_TRUSTED_PROXY_COUNT`に設定した段数だけ`X-Forwarded-For`を信用する（`werkzeug.middleware.proxy_fix.ProxyFix`）。段数を実際のプロキシ台数より多く設定すると、クライアントが偽装した`X-Forwarded-For`を信用してしまうので、正確な段数を設定する

## 6. Gemini連携機能（任意）

レシート読取・店名オートコンプリート・チャット入力はオプション機能。`FMS_GEMINI_API_KEY`が未設定でもアプリ全体は正常に動作し、これらの機能だけが502エラーを返す。

キー設定後の動作確認:
```
flask --app wsgi verify-gemini
```

## 7. 動作確認

1. ブラウザで公開URLを開き`/register`でユーザー作成→ログイン
2. 取引を登録し、月次・レポート画面を確認
3. `logs/app_access_log.txt`が生成され行が追記されることを確認
4. `FMS_HEALTHCHECK_TOKEN`を設定していれば`/healthcheck?token=...`でDB接続とログ書き込み権限を確認

## トラブルシューティング早見表

| 症状 | 主な原因 |
|---|---|
| 起動時に`RuntimeError: FMS_SECRET_KEY が設定されていない` | `.env`が読み込まれていない（`wsgi.py`を経由しない起動方法、または`.env`の配置場所が違う） |
| ログイン試行回数制限が機能しない/全ユーザーが同時にロックされる | リバースプロキシ配下で`FMS_TRUSTED_PROXY_COUNT`が未設定（`0`のまま） |
| HTTPSなのにセッションが頻繁に切れる/Cookieが送信されない | `FMS_FORCE_HTTPS=1`が未設定（Secure属性なしのCookieをブラウザがHTTPS間で扱う際の挙動に依存） |
| レシート読取/チャット入力が「現在利用できません」で502 | `FMS_GEMINI_API_KEY`未設定（意図的な挙動。使わないなら無視してよい） |
| `/healthcheck`が常に404 | `FMS_HEALTHCHECK_TOKEN`未設定、またはクエリの`token`不一致 |
| アクセスログが増えない | `logs/`の書き込み権限不足（アプリはログ書き込み失敗時も本体機能は継続する） |
