# 公開・Inoreader受入状況（2026-10-21 JST）

## 稼働している環境

- 公開リポジトリ: https://github.com/icjgndisk-hub/inoreader-rss
- 配信一覧: https://icjgndisk-hub.github.io/inoreader-rss/
- 初回の収集・履歴保存・Pages配信成功: https://github.com/icjgndisk-hub/inoreader-rss/actions/runs/39400491861
- 画像再取得修正のCI成功（30テスト）: https://github.com/icjgndisk-hub/inoreader-rss/actions/runs/39548100796
- 修正適用後の全サイト収集・履歴保存・Pages再公開成功: https://github.com/icjgndisk-hub/inoreader-rss/actions/runs/39548466745
- 自動実行ログ: https://github.com/icjgndisk-hub/inoreader-rss/actions

| 配信元 | 公開RSS |
|---|---|
| 週刊アスキーPLUS | https://icjgndisk-hub.github.io/inoreader-rss/weekly-ascii.xml |
| 号外NET 松本 | https://icjgndisk-hub.github.io/inoreader-rss/goguynet-matsumoto.xml |
| 信濃毎日新聞デジタル | https://icjgndisk-hub.github.io/inoreader-rss/shinmai.xml |
| 伊那谷ねっと | https://icjgndisk-hub.github.io/inoreader-rss/ina-dani.xml |
| 4サイト統合 | https://icjgndisk-hub.github.io/inoreader-rss/all.xml |

OPML: https://icjgndisk-hub.github.io/inoreader-rss/feeds.opml

個別RSS各500件・統合1000件。公開URLのHTTP 200、XML解析、feedparser、GUID重複なしを `cloud-audit.json` に記録。画像数は記事の入れ替わりで変化するため、時点付きの同ファイルと `public/status.json` を正とする。

2026-10-21 14:17 JSTの公開URL実測:

| サイト | 履歴保存 | RSS件数 | 画像URL・HTTP/ヘッダー検証済み | 画像付き割合 |
|---|---:|---:|---:|---:|
| 週刊アスキーPLUS | 2,519 | 500 | 500 | 100% |
| 号外NET 松本 | 541 | 500 | 500 | 100% |
| 信濃毎日新聞デジタル | 1,009 | 500 | 391 | 78.2% |
| 伊那谷ねっと | 548 | 500 | 500 | 100% |

履歴合計4,617件、初期URL集合からの消失0。上の割合はRSS収録記事を分母にした画像付き割合であり、全新着記事の取得成功率やInoreader上の表示率ではない。画像検証日時はstate内に保存し、7日で再検証する。すべての画像を14:17に一斉に再取得したという意味ではない。

## Inoreaderの実画面検証

| サイト | 実施結果 |
|---|---|
| 週刊アスキーPLUS | 新URLの購読追加成功。初回100記事を表示。スマートフォン、航空、カメラ、飲食など複数の記事の一覧サムネイルを実画面で確認。最重要条件を達成 |
| 号外NET 松本 | 新URLの購読完了。ただし「全ての記事」でも0件。前回巡回08:12・成功、巡回間隔6時間以上、最終配信N/Aを確認。公開RSSには500件ある。利用者の指示で追加調査を終了し、未解決として記録。公開RSSは維持 |
| 信濃毎日新聞デジタル | 新URLの購読完了。記者会見、警察庁舎、閣議など複数の記事サムネイルを実画面で確認。画像なしの記事もある |
| 伊那谷ねっと | 新URLの購読完了。初回100件を取り込み、棒高跳の選手、面会、夏日の記事などの一覧サムネイルを実画面で確認 |

2026-10-21、認証後に残る購読確認を実施。週刊アスキー・信毎・伊那谷の3サイトで画像表示を確認した。号外NETは利用者が更新頻度と調査コストを踏まえて追究不要と判断したため、追加調査を終了。全4サイト成功とは扱わない。既存の購読は削除していない。公式検証ツールも診断完了前に調査を終了したため、検証成功とは扱わない。

検索プレビューに「利用できる記事がありません」が出ても、週刊アスキーは購読後に100件を読み込めた。検索プレビューと実際の購読一覧は分けて評価する。RSS側の500件が初回に全部Inoreaderへ入ることは保証しない。

## 自動運転と障害時の結果

2026-10-21 14時台の取得記録では定期実行29回中28回成功、1回失敗。起動間隔は約27.5〜59.0分だった。毎時07・22・37・52分のcronを設定しているが、GitHub側の遅延・欠落により15分を保証できない。さらにInoreader側の巡回待ちが加わる。

失敗記録 https://github.com/icjgndisk-hub/inoreader-rss/actions/runs/39504065308 では伊那谷の発見処理が失敗したが、保存548件と既存500件のRSSを維持し、Pagesは配信できた。次回の定期実行で成功へ復帰した。最終Statusは収集失敗を隠さず失敗を返す。実行履歴は `scheduled-runs.json` に保存。

初期収集URL集合とクラウド再実行後の集合を比較し、消失0件を確認。500件より古い履歴もGit管理のstateに保持する。全サイトの全記事数は既知でないので、取得網羅率100%とはしない。

## 画像回復の追加修正

号外NETの過去記事1件で一覧/OGP画像のヘッダーが検証上限を超えていた。古い失敗記事も補完対象へ戻し、記事本文の別候補が見つかった場合は再試行待ちを解除するよう修正。実サイトで代替JPEG（1280×768）の取得に成功し、隔離した本番データと、修正後のクラウド実行・公開RSSの両方で500件すべての検証済み画像を確認した。公開側の適用結果は `cloud-audit.json` と `latest-run.json` を参照。

根拠: `image-recovery.json`。元画像に対する制限回避や画像ファイル再配布はしていない。回復した実行でも失敗した候補のログは残るため、全画像がそろっていても収集statusがpartialになる場合がある。

## 運用上の限界

- 公開リポジトリ＋標準Ubuntu Actions＋Pagesで稼働。有料サービス登録、larger runner、Inoreader Pro、PC常時起動は不要。将来の無料条件変更までは保証しない。
- 信毎には代表画像を取得できない記事がある。写真なしと公開画像を発見できなかったケースをすべて区別できるわけではなく、ロゴで水増ししない。
- 伊那谷は日付のみのためRSSの00:00 JSTは表現上の値で、実際の公開時刻ではない。
- 外部画像が削除・拒否されたりサイト構造が変わった場合は保守が必要。記事本文や画像本体は保存しないため、画像が永久に残る保証はない。
- 長期停止中に一覧・サイトマップから消えた未発見URLは回収できないことがある。履歴は自動削除しないため長期的には容量管理が必要。
- GitHubの定期実行停止条件や設定変更があればActions画面から再有効化が必要。日常操作は不要だが、無期限・無保守の運用を保証するものではない。

コード、サイト別取得処理、RSS生成、画像抽出、履歴保存、エラーログ、30件のテスト、導入手順、拡張手順はこのリポジトリに収録済み。初期ローカル検証の `acceptance-evidence.json` は当時の記録として保持し、この公開後報告で更新状況を補足する。
