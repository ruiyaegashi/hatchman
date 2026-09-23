# Recovery / Onboarding調査 — 2026-09-23

目的は既存のHatchmanへ戻るための手順修繕です。新しいArchitecture Decision、Amazonの採用判断、Domain / Mailの方式決定は含みません。運用手順は [RECOVERY.md](../docs/RECOVERY.md) を参照します。この文書は調査時点の記録で、現在状態を更新し続ける台帳ではありません。

## 基準と調査範囲

| 対象 | 基準 |
| --- | --- |
| YDI main | `24689a75a55613cb303edc51a72d81bdad4169ea` |
| hatchman main | `e72eda85780523fd5053374211dbc9a7fc12c01e` |
| hatchman `feature/amazon-associates-preview` | `b6b55f6e878c520b32035ce179c57d908579ac2a` |

- YDIのOrganization / Information Flowと合同入社式の記録を再確認。組織ルールの複製や変更は行わない。
- GitHubの全2 branch、全PR（0件）、open Issues（0件）を確認。上記2 HEADから到達可能な全10 commitをローカルGitでも調査した。mainは4 commit、Previewはそこから6 commit先、behind 0。
- README、package.json、lockfile、scripts、migration / reports、Amazon mapping / Function / componentを照合。
- 旧ローカルのhatchman checkoutはPreview HEADと一致し、追跡対象・通常の未追跡変更はなし。別のremote-inspect checkoutは初期commitだけで、現在状態の根拠にはしなかった。
- 旧ローカル発掘領域の実ファイルと、別保管の元WordPressバックアップを読み取り確認。過去ChatやMemoryを状態・完了・API資格の根拠にしなかった。
- GitHubのHEADと一致する旧ローカルGit objectsから独立した作業コピーを作った。旧checkoutや発掘資料・バックアップは変更していない。

削除済みremote branch、サーバー側の到達不能object、存在を確認できない別PCの資料までは確認できない。「全履歴に存在しなかった」と無制限には断定しない。

## 発見と修繕

| 問題 | 対応 |
| --- | --- |
| READMEの通常確認に、原稿・素材を削除して再生成するmigrateが混在 | GitHubだけでできるbuild / devと、SQL照合・使い捨てcheckoutでの再移行を分離 |
| `pnpm run dev`に対応するscriptがない | 既存Astroの`astro dev`を追加 |
| migration / validationが旧PCの絶対パスに依存 | 両entry pointに`--backup-root`と`HATCHMAN_BACKUP_ROOT`を追加。未指定・不足・repositoryとの重複を出力前に拒否 |
| validateが過去の`reports/validation.json`を上書き | 新しい結果をGit管理外`.recovery/validation.json`へ出力。build前提も明示 |
| 発掘台帳の参照に所在・状態説明がない | 実物の所在を特定し、下記に由来・hash・限界を記録。元レポートからリンク |
| open PRだけではAmazon未統合成果を見落とす | 全branch確認手順と固定SHAの比較を記録 |
| Python bytecodeが追跡され、実行で無関係な差分が生じる | 追跡済みcache2件を削除し、cache・検証出力・バックアップ形式をignore。ignoreは秘密情報の公開審査の代替ではない |

記事・素材・redirect・migration台帳・Amazonの採用状態は変更していない。既存の変換規則、静的表示、責任境界を維持する。

## HATCHMAN_ARCHAEOLOGY.mdの実物と履歴

**結論: 確認できた実物は失われていない。Git未収録のローカル歴史資料だった。**

- 旧作業領域の相対位置 `hatchman-archaeology/HATCHMAN_ARCHAEOLOGY.md` に実物を確認。
- 同じdirectoryに `analysis.json`、`inventory.json`、`analyze_hatchman.py`、`generate_report.py` が存在する。実行・変更・公開はしていない。
- 文書内の作成日は2026-09-22。実ファイルは76,201 bytes、SHA-256は `226626c2c60ce68a5ab3e7f202211dc720af9a55c7295b0ca8bba61a1594caa5`。
- mainとPreviewから到達可能な10 commitについて、path履歴・object名を調べたが、この文書の追加・削除は確認できなかった。
- `reports/MIGRATION_REPORT.md`の名前による参照は `7c8c7e13e9929c2ac252331f707fd46a2b2e75fa` で導入されている。repository内リンクの欠損というより、外部ローカル資料への説明不足だった。

PC固有の絶対パスと内部申し送りはpublic repoへ転記しない。実物は管理者が保管する旧作業領域から上記相対位置・hashで同定する。見つからない場合も、現在のsite buildはGitHub内の成果で行い、発掘記録を推測で再作成しない。

### 歴史から現在への差

| 発掘台帳の段階 | 調査基準mainの状態 |
| --- | --- |
| Markdown / Astroは未実施、移行手順を提案 | 407 Markdown、公開404・draft3、Astro実装、383転送が存在 |
| 画像は将来`public/images`へ救出する案 | 実装は`public/legacy-media`。救出3,371素材＋停止表示SVG1件＝3,372ファイル |
| `browser-shot`20トークン、script39記事 | 移行レポートでは開始shortcode19個＋終了記法1、script44要素。母数が違う |
| Front Matterのreview等は案 | 実装済みschemaと`migration_review`を読む |
| 旧絶対バックアップパスを記録 | 現在の保管場所には追加の中間directoryがあり、旧パスは不存在。実行時指定へ変更 |

旧WordPressの侵害兆候は発掘時の静的調査記録であり、今回の新しいフォレンジック判断ではない。現行READMEの「旧実行環境を再利用せず内容だけ救出」を維持する。台帳の全文を再作成・public repoへ複製する作業はしていない。

## Amazon Previewの現在状態

[固定SHA間の差分](https://github.com/ruiyaegashi/hatchman/compare/e72eda85780523fd5053374211dbc9a7fc12c01e...b6b55f6e878c520b32035ce179c57d908579ac2a)。この修繕PRへmerge / cherry-pickしていない。

変更ファイルは以下の4件。

- `affiliate/legacy-text-link-audit.json`（追加）
- `affiliate/mapping.json`
- `functions/api/amazon.ts`
- `src/components/AmazonProductCards.astro`

| 項目 | main | Preview |
| --- | --- | --- |
| 公開記事mapping | 404件 | 404件 |
| 商品割当 | 140件・67記事・70 ASIN | 同じ旧ASIN集合を使用 |
| API表示状態 | pending140、approved0 | pending137、validation3、approved0 |
| 旧ASINテキストリンク | 専用復旧実装なし | text_link_status approved140、ASINのみのリンク表示 |
| tracking ID | mappingのassociate_tagはnull | テキストリンクpolicyにIDを設定 |
| 短縮URL | 未解決8件 | 同じ8件を手動確認対象として記録 |

PreviewにはAPI検証用の限定ASIN / 検索、キャッシュ設定変更も含まれる。6 commit中には一時診断の追加と除去があるため、途中commitの説明を最終状態とは扱わない。テキストリンク復旧だけの差分でも、API商品の採用完了でもない。

**成果としては現在も参照・レビュー可能。採用済みとは判定しない。** mainを祖先として持ち、内容・素材・URLを変更していないため、消失した成果や別content向けの断片ではない。現在の商品情報、外部API資格、Secret設定、Preview配信の有効性はGit差分だけでは確定しない。今回は外部APIや本番への接続試験をしていない。

### BODへ戻す判断

- テキストリンク復旧を採用するか、いつ統合するか。
- API検証用変更も一緒に採用するか、別に整理するか。
- tracking ID・表示方針・旧商品の扱いをどの確認条件で承認するか。短縮URLを推測で別商品へ置き換えない。
- Domain / Mailの方式・本番切替とAmazon統合の順序。履歴上の公開・計画と、現在の運用証跡を分けて扱う。

## 修正しない事項・限界

- Amazon branchの統合・承認状態、Domain / Mail、ADR-0000、YDI全体Architectureは判断対象として残す。
- `reports/validation.json`やDNS / Amazon移行レポートは過去記録として保持する。現在の配信・API資格の証明へ書き換えない。
- 既存validatorの検査範囲・exit条件は拡張していない。内部リンク欠落のexit条件、欠損データでの診断改善、全本文の意味・外部リンク確認は別の作業候補。
- 発掘資料の長期保管場所・冗長化、削除済み履歴の有無はこの調査だけでは確定できない。現物の所在と識別方法を示し、正式な保管方針は決めない。

## Validation

2026-09-23、Windows / Node 24.19.0 / Python 3.12.14で実施。実行環境のpnpmは11.25.0（packageManager指定11.19.0とは異なる）。`--frozen-lockfile`でinstallし、packageManager・lockfile・依存バージョンは変更していない。

- `python -B -m unittest discover -s tests -v`: 4 tests成功。未指定時の安全な停止、CLI優先・空白を含むパス、元Web資産の必要条件、repositoryと重複する入力の拒否、追跡済み出力の不変を確認。
- `pnpm run check`: 12 files、errors / warnings / hintsすべて0。
- `pnpm run build`: 419ページ生成成功（418個の`index.html`と`404.html`）。
- `pnpm run validate --backup-root <実在する外部保存先>`: 407原稿、公開404 / draft3、公開404ページ生成、383転送。ハッシュ不一致・URL重複・draft誤生成・素材欠落・危険要素・内部リンク欠落・fatalはすべて0。新レポートは`.recovery/validation.json`へ出力され、過去レポートは不変。
- 別の空出力先で、修正後のmigrationを実バックアップに対して実行。原稿407、素材3,372、転送1、台帳4の計3,784ファイルを基準mainのGit blobと照合。3,469件はbytes一致、315件はGitのテキスト改行差（CRLF / LF）のみ。その他の差分・余分なファイルは0。元SQL ZIPの実行前後SHA-256は一致。再生成物はこのPRへ含めない。
- Previewの404記事IDが現行の公開記事集合と一致し、140組のWP ID / 旧ASINがmainと一致することを機械照合。text承認140、API承認0、API検証用3を確認。Previewの外部APIや配信を試験した意味ではない。
- `git diff --exit-code origin/main -- src public migration affiliate functions reports/validation.json pnpm-lock.yaml`: 差分なし。
- `git diff --check`: 成功。

実行環境上の制約: 最初のcheckはAstroのユーザー領域への書込み権限で失敗したため、実行時だけ`ASTRO_TELEMETRY_DISABLED=1`を指定してcheck / buildを実施した。`pnpm run dev`は新しいscriptを解決できたが、通常実行・権限を拡張した実行・Node直接起動とも「Dev server failed to start within 30s」で停止し、HTTP疎通は未検証。原因をrepositoryの不具合と断定せず、この環境ではdev起動成功を確認できていないと記録する。build成功からdev・本番・Cloudflare Functionsの成功を推定しない。
