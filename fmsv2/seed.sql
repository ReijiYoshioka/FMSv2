-- 初期マスタデータ（旧FMS `FMS-main/web/fms/sql/init.sql` から転記）
INSERT OR IGNORE INTO categories (name) VALUES
    ('食費'), ('住居費'), ('水道・光熱費'), ('通信費'),
    ('交通費'), ('税金・保険'), ('医療費'), ('教育費'),
    ('娯楽・趣味'), ('衣服・美容'), ('交際費'), ('貯蓄・投資'), ('雑費');

INSERT OR IGNORE INTO payment_methods (name) VALUES
    ('現金'), ('クレジットカード'), ('デビットカード'), ('電子マネー'),
    ('QRコード決済'), ('銀行振込'), ('口座引落'), ('その他');
