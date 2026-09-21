# Hatchman 2.0 ローカル移行検証レポート

作成日: 2026-09-22  
基準資料: `HATCHMAN_ARCHAEOLOGY.md`

## 結果

旧HatchmanをAstro製の静的アーカイブとしてローカルに再構築した。公開対象404件はすべて旧pathで生成され、下書き3件はMarkdownに保存しつつ公開HTMLを生成していない。旧WordPressのPHP、テーマ、プラグイン、JavaScriptは実行も流用もしていない。

| 項目 | 結果 |
|---|---:|
| 移行Markdown | 407件 |
| 公開 | 404件（投稿403、固定ページ1） |
| 下書き | 3件（公開0件） |
| 一意なlegacy path | 404 / 404 |
| 生成済みlegacy path | 404 / 404 |
| `_wp_old_slug` リダイレクト | 383 / 383 |
| URL衝突 | 0件 |
| Astro生成HTML | 418ページ |

## 原文とメタデータ

各Markdownはタイトル、WP ID、種別、状態、公開日時、更新日時、slug、legacy URL/path、former slug、親WP ID、カテゴリ、タグをFront Matterへ保存した。元 `post_content` のSHA-256と文字数も持たせている。検証時にSQLを再読込して全407件のハッシュを照合し、不一致は0件だった。

本文は原文を基礎に、安全な静的HTMLを残す方式で保存した。実行要素の停止や画像URLの置換は再現可能な移行スクリプトで行い、元バックアップは変更していない。

## URL

- `/%postname%/` に基づく公開404 pathをすべて生成
- `_wp_old_slug` 383件を `public/_redirects` に301として生成
- リダイレクト元の重複0件、転送先欠落0件
- 本文内の旧 `/post-<ID>/` 形式1件は、該当記事の正規legacy pathへ表示時変換
- 内部リンク欠落0件

## 画像・添付

旧画像ディレクトリ全体はコピーしていない。本文から参照されたファイルだけを照合し、ファイルシグネチャを検査して `public/legacy-media/` にコピーした。

| 種別 | 件数 |
|---|---:|
| 本文内画像参照 | 3,421 |
| 完全一致 | 2,665 |
| 大文字小文字差を吸収 | 739 |
| 外部画像 | 17 |
| 欠落 | 0 |
| 原寸画像へのリンク | 18 |
| 拡張子と実体の相違を補正 | 1 |
| 公開した一意なローカル素材 | 3,371 |

外部画像17件は `www.hamazo.tv` に自動接続せず、ローカルの停止表示へ置換した。元URLと対応状況は `migration/asset-map.json` に保持している。`02_31.png` は実体がJPEGだったため、内容を変更せず `.jpg` として配信する対応を記録した。生成HTML上の画像欠落は0件、旧hatchman.orgの画像・PDF依存は0件。

## 特殊表現

| 要素 | 元データ | 移行結果 |
|---|---:|---|
| `[amazonjs]` | 163箇所 | 外部接続せず停止表示。原文shortcodeを折りたたみ内に保持 |
| `[browser-shot]` | 20トークン | 19個の開始shortcodeを停止表示へ変換。残る1トークンは対応する終了記法 |
| iframe | 95件 | iframeを生成せず、旧srcを文字として示す停止表示 |
| `<script>` | 39記事・44要素 | 実行せず、原文スクリプト本文をエスケープして記録 |
| inline style / `<style>` | 131記事 | 静的表示に必要なものを保持し、危険なCSS値を除去 |
| HTML表 | 8記事 | 静的HTMLの表として保持。狭い画面では表領域を横スクロール |
| 数式 | 0記事 | 追加処理なし |

生成HTMLには、実行可能なscript、iframe、object、embed、form、イベント属性、`javascript:` URL、未処理の対象shortcodeが残っていない。

## セキュリティ検証

- SQLをZIP内からストリームで読み、展開SQLを保存していない
- 投稿・postmeta・分類・必要なWordPress設定だけを解析対象にした
- ユーザー、コメント、アクセス解析、セッション等を成果物へ出力していない
- WordPressパスワードハッシュ、session token、DB秘密情報、PHP開始タグの成果物内検出: 0件
- 旧PHP、テーマ、プラグイン、旧JavaScriptの公開素材へのコピー: 0件
- 許可した画像形式はJPEG、PNG、GIF、WebP、ICO。リンク素材はPDFもファイルシグネチャ検査対象

## ビルド・自動検証

- `astro check`: 0 errors / 0 warnings / 0 hints
- `astro build`: 成功、418ページ生成
- 公開legacy page: 404 / 404
- 下書き誤公開: 0
- 301設定: 383 / 383
- broken internal links: 0
- missing rendered images: 0
- unresolved shortcode: 0
- dangerous rendered elements/attributes: 0
- 旧ドメイン画像・PDF依存: 0

詳細な機械判定は `reports/validation.json`、画像対応は `migration/asset-map.json`、コンテンツ台帳は `migration/inventory.json`、旧slug対応は `migration/old-slugs.json` に保存した。

## 目視確認

次をローカルブラウザで確認した。

1. `/` — アーカイブ説明、最新記事、一覧への入口
2. `/nekocafe-raimu/` — 2020年の最新記事、公開日、複数カテゴリ、Google Maps停止表示
3. `/hamamatsushi-trip-amusementpark-palpal/` — 最古記事、画像4点の読込、スマートフォン相当幅で横はみ出しなし
4. `/post-7989/` — 約1.7万字の最長記事、HTML表2点、表とページの横はみ出しなし
5. `/the-best-highest-firstclass-marimba/` — browser-shot 7点、YouTube iframe 2点、Amazon 1点の停止表示、画像2点

## 人間による公開前確認を推奨する記事

- WP 7989 `/post-7989/`: 長い料金比較表が当時の情報として読み取れるか
- WP 8185 `/post-8185/`: iframe 7件を停止した後も本文の流れが理解できるか
- WP 8470 `/the-best-highest-firstclass-marimba/`: browser-shot、動画、Amazon停止表示の密度
- WP 9306 `/my-stress-theory/`: Amazon紹介7件を停止した状態で本文が成立するか
- WP 9562 `/ramen-menyaclear/`: 広告、browser-shot、iframe、scriptを含む複合記事
- WP 7827 `/post-7827/`: 拡張子がPNG、実体がJPEGだった原寸画像リンク

## 公開前に残った課題

公開を機械的に妨げる既知の問題はない。次の項目は原文欠落ではなく、意図的に停止した外部機能である。

- Amazon商品表示163件の代替は未実装
- browser-shot 19個のスクリーンショット表示は未復元
- iframe 95件は動画・地図・Facebookを含め停止中
- 外部画像17件は自動表示せず、元URLを対応表に保存
- 外部リンク先は当時のままであり、リンク切れや現在の内容は保証しない

これらは安全性を優先した公開後改善候補であり、静的アーカイブの公開自体を妨げない。
