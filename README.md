# Inoreader Image RSS Kit v2.0

週刊アスキーPLUS・号外NET松本・信濃毎日新聞デジタル・伊那谷ねっとの見出し、公開日時、元記事URL、代表画像URLを収集し、RSS 2.0を生成する個人用プログラム。

**コードと実サイト取得は検証済み。GitHubへの配置・公開URL・Inoreaderでの実表示は、同梱の検証報告を確認すること。未公開のURLを完成済みとして扱わない。**

## 構成と公開範囲

推奨は **GitHubの公開リポジトリ + 標準UbuntuのGitHub Actions + GitHub Pages**。PCの常時起動、APIキー、Inoreader Proは不要。

公開リポジトリにはコード、サイト設定、取得済みのタイトル・公開日時・記事URL・画像URL、取得状況、履歴が保存される。Pagesは `public/` のみを配信するが、`state/` も公開リポジトリからは閲覧可能。画像ファイルや記事本文、ログイン情報、個人のInoreader購読履歴は保存しない。これは秘密のフィードではない。

現在のGitHub公式条件では、公開リポジトリで標準ホストランナーを使うActionsは無料。Private化するとこのワークフローは実行しない。課金されるlarger runner、外部有料サービス、Codespacesは使用しない。配信の一時artifactは公開後に当該実行分だけ削除し、失敗時も1日で失効する設定。無料サービスの条件変更や障害まで永久に保証するものではない。

## 導入（ブラウザだけで行う場合）

1. GitHubで新しい **Public** リポジトリを作る。推奨名は `inoreader-rss`。READMEの自動作成は不要。
2. ZIPを展開し、`inoreader-rss` フォルダーの**中身**をすべてアップロードする。外側のフォルダーを丸ごと入れ子にしない。`.github/workflows/update.yml`、`rsskit/`、`config.toml`、`state/` がリポジトリ直下にあることを確認する。
3. リポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** にする。必要なら **Settings → Actions → General → Workflow permissions** を **Read and write permissions** にする。ブランチ保護でActionsのmainへの書き込みを拒否しない。
4. **Actions → Update image RSS → Run workflow → Run workflow**。初回アップロードとPages設定の順序により最初の自動実行が失敗していた場合も、ここで再実行する。既に収集した初期データが同梱されているため、通常はbootstrapをオンにする必要はない。
5. Actionsが緑色になったら、Settings → Pagesに表示されるサイトURLを開く。各行の **RSS** をInoreaderの購読追加へ貼り付ける。`feeds.opml` の一括読み込みも使える。
6. Inoreaderで **カード表示またはマガジン表示** にし、週刊アスキーの新規記事の画像を確認する。旧フィードを削除する必要はない。画像の実表示確認後に整理する。

公開URLの形式は以下。`YOUR_ACCOUNT` と `YOUR_REPOSITORY` は実際の値へ置き換える。**これは形式例であり、現在稼働しているURLの約束ではない。**

```
https://YOUR_ACCOUNT.github.io/YOUR_REPOSITORY/weekly-ascii.xml
https://YOUR_ACCOUNT.github.io/YOUR_REPOSITORY/goguynet-matsumoto.xml
https://YOUR_ACCOUNT.github.io/YOUR_REPOSITORY/shinmai.xml
https://YOUR_ACCOUNT.github.io/YOUR_REPOSITORY/ina-dani.xml
https://YOUR_ACCOUNT.github.io/YOUR_REPOSITORY/all.xml
```

Actionsがリポジトリ名からURLを設定するため、通常 `config.toml` のbase_url編集は不要。独自ドメインを使う場合はワークフローの `FEED_BASE_URL` を変更する。

## ローカル実行・検証

Python 3.11以上（CIは3.12）。作業ディレクトリはこのREADMEのあるフォルダー。

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python generate.py --force
python scripts/validate.py
```

初回の広い収集：

```sh
python generate.py --bootstrap --pages 18 --articles 120 --images 70
```

障害後の単独再試行：

```sh
python generate.py --site weekly-ascii --force --retry-failed
```

HTML・OPML・RSSの再出力のみ：

```sh
python generate.py --render-only --base-url https://YOUR_ACCOUNT.github.io/YOUR_REPOSITORY
```

ローカルのXMLファイルのパスをInoreaderへ登録することはできない。公開HTTPS URLが必要。

## 更新・履歴・画像

- Actionsは毎時07・22・37・52分に起動予定。週刊アスキーと信毎は15分、号外NETと伊那谷は30分を目安に処理する。処理完了時間ではなく前回試行開始時刻から判定する。
- Actionsには遅延・欠落があり、Inoreader無料版には15分巡回の保証がない。RSSのttlも巡回を強制しない。
- 個別RSSは最新500件、統合RSSは最新1000件。500件より古い記事のメタデータも `state/` から削除しない。これらはGitコミットで永続保存し、Actions cacheを履歴の保存先にしない。
- 初回の号外NET/伊那谷のバックフィルは500件程度を満たすまで分割継続。通常は少なくとも2ページを確認し、既知記事だけのページで追いついたと判断する。障害後に1実行で届かない場合はカーソルを保存する。
- 週刊アスキーは公式RSS・トップ・月別アーカイブを組み合わせる。前回成功から月をまたいだ場合は、保存した月カーソルで順次回収する。
- 信毎は公開SSRのメタデータとローリングサイトマップを使う。サイトマップのlastmodを公開日時として使用しない。未取得URLは永続キューに入り、公開日時・見出しを取得できるまでRSSへ出さない。
- 既知記事はURLで更新するため、タイトルや画像が変わっても別記事として増えない。元サイトがURL自体を変えた場合の自動同一判定は未対応。
- 画像は記事固有OGP/Twitter/NewsArticle JSON-LD/記事本文の指定範囲/一覧画像/RSSから選択。サイトロゴ、広告の代表的パターン、信毎のnoPhoto等を除外。汎用の「ページ先頭の画像」は使わない。
- RSSにはdescriptionの通常img、content:encoded、media:thumbnail、media:contentを出力。enclosureはMIMEとバイト長が実応答で確認できた場合だけ出力する。
- 画像検証は1回につき設定件数まで順次実行し、状態を保存。リファラー偽装、画像プロキシ、画像の再アップロードはしない。HTTP 403の画像を回避して取得しない。
- 伊那谷の公開情報には日付しかないため、精度 `day` を保存しRSSではJST 00:00と表現。その旨をdescriptionに明示する。正確な公開時刻を推測で埋めない。
- 画像と記事の一時失敗は再試行。429/5xxは短いバックオフ、長いRetry-Afterは次回へ延期。403の本体は即失敗。robots.txtはRFC 9309に従い、取得成功時はルールを尊重、4xx（429除外）は未提供扱い、ネットワーク障害/5xxは取得保留とする。

## 稼働確認と復旧

- 公開ページの件数・状態、`status.json`、ActionsのSummaryで確認する。詳細は `reports/latest-run.json` とActionsログ。
- `ok` はその実行で発見処理に成功した状態であり、すべての記事・画像・Inoreader表示を保証しない。`verified_images_in_feed` と `pending_metadata` を併せて見る。
- 信毎の写真なし記事は画像なしが正しい。共通ロゴを付けて画像取得成功率を水増ししない。
- 号外NETは最新の元記事自体が古いことがある。取得成功と配信元の更新頻度は別問題。元記事の日付を今日に書き換えて新着に見せない。
- `state/*.json` と `.bak` が履歴。破損時は空状態で上書きせず停止する。GitHubの過去コミット、またはJSON構造を確認した `.bak` から復元する。
- publicの既存RSSを空フィードで上書きしない。一部サイトが失敗しても他サイトは処理し、履歴とログを保存する。
- 公開リポジトリは活動が60日間ないとscheduleが自動無効化される。通常は履歴コミットが発生するが、停止や権限エラーが続けば自動回復できない。無効化時はActionsでEnable workflow。完全無人で障害まで永久に自己修復するわけではない。
- stateは自動削除しないため長期的には容量が増える。各JSONが50MB以上になる前に、月別分割などの保守が必要。履歴を消して容量を誤魔化す処理は入れていない。
- 同時ローカル実行はしない。クラウドはconcurrencyで直列化する。mainへの手動変更がpushと競合した場合は、無理なforce pushをせず失敗させ、最新mainを取得する次回実行で回復する。

## サイトを追加する

```sh
python scripts/discover.py https://example.com/
```

HTML内で宣言されたRSS/Atom/JSON Feedを検査し、記事数・画像候補を表示する。未宣言の配信やJavaScript専用フィードは発見できないことがある。URLを入力するだけですべてのサイトを正しく収集する機能ではない。

1. `rsskit/adapters/` に専用Adapterを追加する。
2. `canonical()` に記事URLパターンを追加する。
3. `ADAPTERS` と `config.toml` に登録する。
4. 実HTMLの最小fixtureと回帰テストを追加する。
5. `scripts/validate.py` の期待フィード一覧を更新する。

## 取得範囲の限界

一覧・サイトマップから消え、どの実行でも発見できなかった記事は保証できない。信毎の「もっと見る」はJS/GraphQLだが、この版は未公開API依存を避けて公開サイトマップで補完する。サイトマップの保存期間を超える長期停止からの全件回収は保証しない。カテゴリによって画像のない記事もある。配信元のURL・HTML構造・規約・アクセス条件が変わると保守が必要。

元記事本文・有料部分はRSSへ収録しない。画像は配信元URLへの外部参照であり、外部参照できたこと自体が再利用許諾を意味するわけではない。公開範囲や配信元条件が目的と合わない場合はそのサイトの配信を止め、権利者の案内に従う。

## 主要な公式資料（2026-10-20確認）

- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows
- https://www.inoreader.com/pricing
- https://www.rfc-editor.org/rfc/rfc9309.html
- https://weekly.ascii.jp/info/site_policy/
- https://ina-dani.net/copyright
- https://ina-dani.net/external

旧 `Inoreader_Free_RSS_Kit.zip` は解析済み。画像HTML+media:thumbnail、URL基準の保存という考え方を引き継ぎ、共通セレクター、時刻の一律12:00補完、画像再取得を止めるフラグ、250件の履歴切り捨てを廃止した。
