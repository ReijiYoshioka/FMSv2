# FMSv2

## 概要

家計簿システム「FMS」の後継。旧版（`../FMS-main/`、PHP + MariaDB）の機能を新しい技術スタックで再現し、その後新機能を追加する。旧版はドキュメントが存在しないため、機能仕様は`../FMS-main/web/fms/public/api/*.php`と`../FMS-main/web/fms/sql/init.sql`を読んで把握する。

- **フェーズ1（機能網羅、現在ここ）**: 取引管理・月次収支・検索フィルタ・レポート/グラフ・予算管理・定期取引・マスタ編集・CSV入出力・アカウント管理・アクセスログ
- **フェーズ2（機能追加）**: フェーズ1完了後に着手。フェーズ1未完了のうちは新機能を先行実装しない

## 技術スタック

| レイヤー | 技術 |
| --- | --- |
| バックエンド | Python + Flask |
| データベース | SQLite（`sqlite3`標準ライブラリで生SQL、ORM不使用） |
| フロントエンド | HTML / CSS / JavaScript + Bootstrap 5 |
| 外部API | Gemini API（`google-genai`、レシート読取機能で使用。任意機能でAPIキー未設定でも他機能は動く） |
| テスト | pytest |
| Lint/Format | ruff / black |

## Build & Test

- 依存インストール: `pip install -r requirements.txt`
- テスト: `pytest`。**実装を変更したら必ず実行し、失敗があれば直してからタスク完了とする**
- Lint: `ruff check .`
- Format: `black .`

## アーキテクチャ

- Flaskアプリケーションファクトリ + Blueprint構成。旧版のAPI分割に合わせ、`transactions` / `summary` / `budget` / `recurring` / `masters` / `account` / `csv`単位でBlueprintを分ける
- DBスキーマは`../FMS-main/web/fms/sql/init.sql`を参照してSQLiteに移植する

## Coding Conventions

- PEP8準拠。ruff/blackの指摘に従う
- 命名はsnake_case
- SQLは必ずパラメータ化クエリを使う（文字列結合でSQL文を組み立てない）。旧版のPDOプリペアドステートメント方針を継承する

## Rules

- 実装後は必ず`pytest`を実行し、グリーンになってからタスク完了とする
- 認証はセッションベース、状態変更エンドポイントにはCSRF対策を入れる（旧版はカスタムCSRFトークン方式。Flaskでも同等の仕組みを用意する）
- 機密情報（DB接続情報等）はコードに直書きせず、`.gitignore`対象の設定ファイルまたは環境変数に分離する
- 新しい依存を追加する前に本当に必要か検討する

## Gotchas

- 旧版（`../FMS-main/`）にはドキュメントが一切ない。機能仕様は必ずコードを読んで確認する
- 定期取引の「二重適用防止」など、旧版READMEに記載された挙動は実装漏れしやすいため個別に確認する
- 旧版の関数命名はcamelCaseとsnake_caseが混在している。新版はPython規約（snake_case）に統一する
- レシート読取機能は読み取った画像自体を保存しない（Geminiに送って抽出結果を受け取ったら即破棄）。抽出結果は既存の取引登録モーダルに事前入力するだけで、保存前に必ずユーザーが確認する
- Gemini呼び出しの日次上限は汎用テーブル`api_call_attempts`（`endpoint`列で機能ごとに区別。`security/api_rate_limit.py`）で管理する。機能を追加する際はテーブルを増やさずここに乗せる
- 店名オートコンプリート（Google Maps Grounding）は位置情報（緯度経度）を永続保存しない。店名の文字列だけをdescriptionに反映する。GroundingツールはGeminiの`response_schema`（構造化JSON出力）と併用できないため、`grounding_metadata.grounding_chunks`から候補を抽出する方式にしている（`gemini_client.suggest_places`）
- チャット自動入力は会話履歴をサーバー側に保存しない（ブラウザのJS変数だけで保持し、モーダルを閉じれば消える＝日をまたいで引き継がれない）。1往復で情報が足りなければGeminiがquestionを1つだけ返し、最大6往復で打ち切る（`chat_service.MAX_TURNS`）
- `.env`は`wsgi.py`が`python-dotenv`で読み込む。`flask --app fmsv2:create_app run`のように`wsgi.py`を経由しない起動方法では`.env`が読み込まれず`FMS_SECRET_KEY`未設定エラーになる。デプロイ手順は`DEPLOY.md`を参照
