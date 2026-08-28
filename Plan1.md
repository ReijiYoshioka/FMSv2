# FMSv2 実装計画（フェーズ1: 旧FMSの機能網羅）

## Context

旧FMS（`FMS-main/web/fms/`、PHP8 + MariaDB）は完全にvibe codingで作られ、設計ドキュメントが存在しない家計簿Webアプリ。GitHub上に既存の`FMS`リポジトリがあるため、名前衝突を避ける目的で新リポジトリ名を`FMSv2`とするが、プロダクトとしては同一システムの後継である。

移行方針は2フェーズ制で、本計画はフェーズ1（既存機能の新スタックでの網羅的再現）のみを対象とする。フェーズ2（新機能追加）は本計画のスコープ外。

新スタック: Python + Flask / SQLite（`sqlite3`標準ライブラリ、ORM不使用） / HTML+CSS+JS + Bootstrap5 + Chart.js / pytest / ruff + black。旧版もPHP標準機能のみで認証・CSRF・レート制限を自前実装していたため、新版もFlask-WTF/Flask-Login等の追加依存を避け、Flask標準機能＋標準ライブラリで同思想を継承する。

旧コードの調査（3エージェントによる`FMS-main/`の直接読解）で、DBスキーマ・API仕様（transactions/summary/budget/recurring/masters/account/csv）・認証/CSRF/レート制限/アクセスログ/healthcheck・フロントエンド構成（ページ/JS/Chart.js）を確認済み。ドキュメントが存在しない旧版の挙動は**コードが正**であり、以下の仕様はすべてそのコード読解に基づく。

## 新旧の対応関係（重要な設計判断）

- 旧版`transactions.user_id`等は`users.username`をVARCHARで直接格納する設計だが、新版では`users.id`への整数外部キーに正規化する（機能的には同一、データ整合性の改善。テーブル全体で一貫してこの正規化を適用する）
- 旧版はPHPサーバーサイドセッション、新版はFlask標準の署名付きクッキーセッションを使う（個人利用アプリのため、サーバーサイドストレージは不要と判断）
- それ以外のAPI挙動・業務ロジック・UI構成は忠実に再現する

## ディレクトリ構成

```
FMSv2/
├── CLAUDE.md                       既存（フェーズ2着手時に更新）
├── Plan1.md                        このファイル
├── pyproject.toml                  ruff/black設定
├── requirements.txt                Flask, Werkzeug
├── requirements-dev.txt            pytest, ruff, black
├── .gitignore                      instance/, *.db, .env, logs/*.txt 等
├── .env.example                    FMS_SECRET_KEY, FMS_HEALTHCHECK_TOKEN 等
├── wsgi.py                         本番エントリポイント
├── instance/.gitkeep               fms.db 配置先（git管理外）
├── logs/.gitkeep                   app_access_log.txt 配置先（git管理外）
├── fmsv2/
│   ├── __init__.py                 create_app() ファクトリ
│   ├── config.py                   環境変数読込（config.php.example相当）
│   ├── db.py                       sqlite3接続ヘルパー（PRAGMA foreign_keys=ON必須）
│   ├── schema.sql / seed.sql       DDL＋初期マスタデータ
│   ├── cli.py                      `flask init-db`
│   ├── security/                   csrf.py, auth.py, rate_limit.py, headers.py
│   ├── logging_/access_log.py      BEGIN/END方式アクセスログ＋prune
│   ├── blueprints/                 auth, pages, api_transactions, api_summary,
│   │                                api_budget, api_recurring, api_masters,
│   │                                api_account, api_csv, healthcheck
│   ├── services/                   *_repo.py（SQL＋業務ロジック本体。Blueprintは薄く保つ）
│   ├── utils/                      dates.py, json_response.py
│   ├── templates/                  base.html, auth/*.html, pages/*.html
│   └── static/                     vendor/(bootstrap,chartjs), css/, js/
└── tests/                          conftest.py + test_*.py（機能単位）
```

**Blueprint/Service分離の理由**: 旧版は1 APIファイルにロジックを直書きしていたが、新版は`services/*_repo.py`にSQL・業務ロジックを集約し、BlueprintをHTTP層のみの薄いラッパーにする。特にsummary/budget/transactionsで共有する「内訳(transaction_items)があればitem単位category、無ければ本体categoryをUNION ALLで合算」という集計ロジックは`summary_repo.py`に一箇所実装し、pytestからHTTPを経由せず直接ロジックを検証できるようにする。

## DBスキーマ（SQLite移植の要点）

- `AUTO_INCREMENT` → `INTEGER PRIMARY KEY AUTOINCREMENT`
- `ENUM('income','expense')` → `TEXT CHECK(type IN ('income','expense'))`
- `DECIMAL(12,0)`（小数なし金額） → `INTEGER`
- `ON UPDATE CURRENT_TIMESTAMP`はSQLiteに無いため、UPDATE時に`updated_at`をアプリ側で明示的にセットする
- 外部キーは接続ごとに`PRAGMA foreign_keys = ON`を実行しないと無視される点に注意（`db.py`の接続直後に必須実行）
- テーブル一覧: `users` / `login_attempts`(idx: ip_address,attempted_at) / `categories` / `payment_methods`(初期データ: カテゴリー13件・決済手段8件、旧`sql/init.sql`から転記) / `transactions`(idx: user_id+date, category_id, payment_method_id) / `transaction_items`(idx: transaction_id, CASCADE) / `recurring_transactions` / `recurring_applications`(UNIQUE(user_id,recurring_id,month) — 二重適用防止の要) / `budgets`(UNIQUE(user_id,category_id,month))

## API仕様（フェーズ1で再現する挙動。全て`/api/...`、JSON、認証必須、POST/DELETEはCSRF必須）

共通: 未認証はAPI系401 JSON・画面系はloginへリダイレクト。CSRFは`X-CSRF-Token`ヘッダ優先、無ければbody内`csrf_token`、不一致403。例外はサーバーログのみに詳細を出し利用者には汎用メッセージ+500。

1. **transactions**: 一覧（月フィルタ必須orデフォルト今月、`q`/`type`/`category_id`/`min`/`max`、内訳付き、`date DESC,id DESC`）。`action=metadata`でマスタ一覧。新規/更新: description必須、items有無でamount算出方法分岐（items合計 or トップレベルamount必須）、type=income時payment_method_id強制null、expense×items有りでcategory_id未指定なら最頻カテゴリー自動設定、更新はitems全削除→再INSERT（トランザクション必須）。削除は所有権チェック404。
2. **summary**: `mode`分岐で月次/年次のincome・expense・balance、カテゴリー別（内訳/本体UNION ALL集計、未分類ラベル）、決済手段別（未設定ラベル）、月別推移。**前月比はバックエンド未実装**（フロントが当月・前月を並行fetchして差分計算——この設計を維持）。
3. **budget**: カテゴリー別実支出（summaryと同じUNION ALL集計）とbudgets JOINでremaining/ratio算出。前月コピー（upsert）、一括保存（amount=0はDELETE）、単一保存/削除。
4. **recurring**: 一覧+当月適用済みフラグ。登録/更新（type=income時payment_method_id強制null）。**適用処理**: active=1の各テンプレを独立トランザクションで処理、`recurring_applications`へのINSERT（UNIQUE制約）が一意制約違反なら「既適用」としてskip、成功したら適用日=min(day_of_month,当月末日)で取引INSERTし紐付け、結果`{applied,already,total}`。削除は所有権チェック。
5. **masters**: 共有マスタ（user_idなし）。追加/改名（UNIQUE違反409）。削除は使用中チェック（category: transactions/transaction_items/recurring_transactions/budgets、payment: transactions/recurring_transactions の参照件数>0なら409拒否）。
6. **account**: パスワード変更。新8文字以上、新旧同一拒否、現パスワード検証失敗403。
7. **csv**: エクスポート（UTF-8 BOM付き、ヘッダ`date,type,description,category,payment_method,amount,memo`固定順、CSVインジェクション対策エスケープ）。インポート（2MB上限、ヘッダ自動判定、列数<6/日付・金額不正はskip、カテゴリ/決済手段は名前文字列でマスタ解決・未登録はnull、1トランザクション、結果`{success,inserted,skipped,errors[]}`）。

## 認証・セキュリティ

- 全レスポンスに`X-Content-Type-Options:nosniff`/`X-Frame-Options:DENY`/`Referrer-Policy:same-origin`。クッキーは`httponly`/`secure`(HTTPS判定)/`samesite=Lax`。
- CSRF: 256bitランダムトークンをセッションに保持、比較は`hmac.compare_digest`でタイミング安全に行う。
- ログイン: IP単位レート制限（15分5回失敗でロック、`login_attempts`テーブル）、`werkzeug.security.check_password_hash`、成否メッセージ統一（ユーザー列挙防止）。
- 登録: username3文字以上、password8文字以上、UNIQUE違反ハンドリング、`werkzeug.security.generate_password_hash`。
- ログアウト: POST限定+CSRF必須（ログアウトCSRF対策）。
- アクセスログ: `before_request`/`teardown_request`でBEGIN/END行をファイル追記（トークン紐付け、経過ms、ステータス、method、path、user、IP）、365日保持のprune処理。
- healthcheck: 独立エンドポイント、トークンを`hmac.compare_digest`で比較、不一致は404で存在を隠す。DB接続・テーブル存在・ログ書込可否を診断。

## フロントエンド

- 3ページ（monthly/graphs/manage）はFlaskルーティングで個別テンプレート・個別JSファイルに分離（旧版は1つの`app.js`が`?page=`分岐で全担当）。`base.html`にnavbar・CSRFメタタグ・Toast領域を共通化。
- `static/js/common.js`にCSRF付きfetchラッパー・401時トースト＋リダイレクト・escapeHtml等を集約し、旧`app.js`のロジックをそのまま移植。
- Bootstrap5/Chart.jsは旧`public/vendor/bootstrap/`・`public/vendor/chartjs/`のファイルをそのままコピーして自己ホスト継続。

## 実装順序

1. **Stage 0（土台）**: pyproject/requirements/.gitignore → `config.py`/`db.py`/`schema.sql`/`seed.sql`/`cli.py` → `create_app()`最小構成 → `tests/conftest.py`+スキーマテスト。**pytestが通ることを最初のマイルストーンにする**
2. **Stage 1（認証基盤）**: security/headers・csrf・auth・rate_limit → `users_repo.py` → `blueprints/auth.py`+テンプレート → テスト
3. **Stage 2（transactions）**: 最も複雑で他機能の土台。repo→blueprint→テスト（フィルタ全パターン、items整合、所有権、CSRF/401境界）
4. **Stage 3（summary）**: transactionsのUNION ALL集計を`summary_repo.py`に共通化 → テスト
5. **Stage 4（budget）**: summary_repoの集計に依存 → テスト
6. **Stage 5（recurring）**: 独立トランザクション処理が要。二重適用防止のテストを最重要視
7. **Stage 6（masters/account/csv）**: 横断的な小機能
8. **Stage 7（アクセスログ/healthcheck）**
9. **Stage 8（フロントエンド）**: base.html→common.js→3ページ分のテンプレート/JS→vendor配置
10. **Stage 9（仕上げ）**: `ruff check .` / `black .` / `pytest`全体グリーン確認

依存順の理由: summary/budgetは共通集計ロジックを必要とするためtransactions確定後に着手。recurringはtransactions INSERTロジックに依存。masters/account/csvは他APIが安定後の横断機能。

## pytestテスト戦略

- DB fixtureは`tmp_path`に一時sqliteファイルを作り、テストごとに`schema.sql`+`seed.sql`を再実行してクリーン状態から開始（`:memory:`はFlask `g`との接続共有が難しいため不採用）。
- 単体（services層、HTTP非経由）: UNION ALL集計、最頻カテゴリ自動設定、月末日クランプ、CSVエスケープ関数
- 結合（test_client経由）: ステータスコード・JSON構造・DB状態変化・CSRF/401/403/404/409境界
- 重点シナリオ: 定期取引の二重適用防止、items全削除→再INSERT、type=income時payment_method_id強制null、budget/summaryの集計一致、masters削除の使用中チェック、CSVのBOM/インジェクション対策/import異常系、ログインレート制限、アクセスログBEGIN/END+prune、healthcheckトークン404
- 運用ルール: 実装変更のたびに`pytest`実行→グリーンになるまで直す（`FMSv2/CLAUDE.md`記載のルールをそのまま踏襲）

## Critical Files

- `FMSv2/fmsv2/schema.sql` — DDL全定義
- `FMSv2/fmsv2/db.py` — 接続ヘルパー（PRAGMA foreign_keys必須）
- `FMSv2/fmsv2/services/summary_repo.py` — UNION ALL集計の共通実装
- `FMSv2/fmsv2/security/csrf.py` — CSRF発行/検証
- `FMSv2/tests/conftest.py` — テストDB fixture

参照専用（変更しない）:
- `FMS-main/web/fms/sql/init.sql`
- `FMS-main/web/fms/public/db_connect.php` / `logger.php` / `healthcheck.php`
- `FMS-main/web/fms/public/js/app.js`
- `FMS-main/web/fms/public/vendor/**`（Bootstrap5/Chart.jsをそのままコピー）

## 検証方法

- 各Stage完了時に`pytest`を実行しグリーンを確認してから次Stageへ進む
- Stage 9完了時に`ruff check .` / `black --check .` / `pytest`をこの順で実行し全てパスすることを確認
- フロントエンド（Stage 8）完了後は`flask run`でサーバーを起動し、ブラウザで実際にログイン→取引登録→月次表示→グラフ表示→予算設定→定期取引適用→CSV入出力の一連の操作を手動確認する
