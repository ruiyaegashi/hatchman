# Hatchman Recovery / Onboarding

この文書は既存productへ戻るための手順です。責任・設計の変更や、Amazon / Domain / Mailの採用判断を行うものではありません。

## 0. 現在のProduction Reality

2026-09-30時点:

- public domain: `https://hatchman.org`
- hosting: Cloudflare Pages project `hatchman`
- deploy source: このrepositoryの `main`
- production deploy: GitHub連携のautomatic deployment
- DNS authority: Cloudflare DNS
- Registrar: XServer
- XServer独自ドメイン永久無料特典: 維持
- media storage: private R2 bucket `hatchman-media`
- Pages binding: `MEDIA -> hatchman-media`
- runtime: Astro static site + Cloudflare Pages Functions
- old XServer WordPress / Web hosting: 退役済み

Production復旧では、XServerの旧WordPress環境をoriginとして戻すことを前提にしません。
まずCloudflare Pages / DNS / R2 / 実HTTPを現在Realityとして確認してください。

Production復帰の詳細な完了記録はYDI Drive logical ID
`log/hatchman/20260930/production-recovery-closeout`
を参照します。

## 1. 現在状態を確定する

組織の入口はREADMEから参照するYDIの文書です。YDIの現在状態はGitHub上のmainを基準とし、branch / open PRは未統合成果として読み、Issueや過去レポートを実装済み機能と混同しません。

ローカル作業が残っていれば、最初に `git status --short --branch`、`git diff`、`git diff --cached` を確認し、変更を消さずに保全します。その後、通常のGit環境で次を確認します。取得はローカルrefを更新しますが、checkoutやmergeは行いません。

```console
git remote -v
git fetch origin
git rev-parse origin/main
git ls-remote --heads origin
git branch -a -vv
git log --all --oneline --decorate
```

originが `https://github.com/ruiyaegashi/hatchman.git` を指すことを確認します。ローカルがなければ新しい作業先へcloneします。branchを限定したcloneの場合は全remote branchを取得し直します。

- [全branch](https://github.com/ruiyaegashi/hatchman/branches)、[PR](https://github.com/ruiyaegashi/hatchman/pulls)、[Issues](https://github.com/ruiyaegashi/hatchman/issues)を確認する。PRがなくても未統合branchは存在し得る。
- branchごとに `git rev-list --left-right --count origin/main...origin/<branch>` と `git diff --stat origin/main...origin/<branch>` で差を読む。
- 調査時のmain SHA、branch SHA、PR状態を記録する。過去のSHA・件数は [Recovery調査](../reports/RECOVERY_AUDIT_2026-09-23.md) にあるが、毎回再確認する。
- GitHubの状態と配信状態は別。公開先、配信commit、Pages設定、DNS、送受信は別の証跡で確認し、未確認ならそのまま報告する。Secretsの値を報告へ出さない。

## 2. GitHubだけで戻れる範囲

Current media配信の構成・生成・route・cache / conditional request境界は [Media delivery design](MEDIA_DELIVERY.md) を実装入口として確認する。

`src/content/legacy/`、`public/_redirects`、`migration/`、media manifest / mapping、Pages Functions実装、lockfileはGitHubにあります。canonical media binary本体はGitHubではなくprivate R2 `hatchman-media` にあります。READMEのinstall / check / build / devで静的サイト部分を復元できますが、Production相当のmedia配信にはR2 bindingが必要です。元SQLや発掘台帳は通常buildの必須入力ではありません。

`pnpm run dev` は起動し続けるので終了はCtrl+C。表示処理を変えていない復旧作業でも、公開記事とdraftを分けて確認します。静的buildだけではCloudflare Function、Amazon資格、メール、本番配信を確認したことにはなりません。

## 3. 必要なローカル資産

元バックアップを再照合するときだけ、管理者からrepository外の保管先を確認します。PC固有の既定パスや旧台帳に書かれた絶対パスを前提にしません。

```text
<backup-root>/
  mysql55_20260921.zip   # 中に .sql.gz がある元SQLバックアップ
  public_html/          # 再移行時のみ必要な展開済み旧Web資産
```

`public_html.zip` は保管用アーカイブであり、スクリプトは自動展開しません。再移行用の展開済み資産がなければ保管担当者に確認します。SQL / 旧Web一式 / Secretsをrepositoryへコピーせず、旧PHP等も実行しません。

任意の保存先を `--backup-root` で渡せます。相対パスは実行時のcurrent directory基準、`~`も使用可能です。環境変数よりCLI指定を優先します。未指定・不足時は出力を作る前に停止します。

PowerShell例（placeholderは実在するrepository外の保存先へ置換）:

```powershell
$env:HATCHMAN_BACKUP_ROOT = '<backup-root>'
pnpm run build
pnpm run validate
```

同等の直接指定:

```console
pnpm run validate --backup-root "<backup-root>"
```

`python` の名前が使えない環境では、同じPython 3.12環境の実行ファイルで `scripts/validate_migration.py --backup-root "<backup-root>"` を実行できます。NodeだけでできるbuildとPythonが必要な元データ照合を分けてください。

`validate` はSQLをZIP内から読み取り、407件の本文ハッシュ、公開404件・draft3件、旧URL、383転送、素材、生成HTML等を検査します。元資料は変更せず、新しい結果は `.recovery/validation.json` に保存します。`reports/validation.json` は過去記録として残ります。

検証の限界: 元SQLのハッシュと台帳の照合はMarkdown本文全体の同一性保証ではありません。外部リンクの現存性や内容の正確性も検証しません。内部リンクの件数は出力で確認してください（既存validatorは内部リンク欠落だけでは非zero exitにしません）。`total_html_pages` は `index.html` の数で、`404.html` は含みません。

バックアップが見つからなければSQL照合・再移行を止め、GitHubだけの復元結果と未確認事項を報告します。欠けた原本やハッシュを推測で補いません。

### Recovery tooling guard

Recovery / migration入口のfail-closed条件を変更する場合は、[tests/test_recovery.py](../tests/test_recovery.py) を現在の安全guardとして確認する。

```console
python -m unittest tests.test_recovery
```

通常onboardingで再移行を実行する意味ではなく、Recovery tooling自体を変更したときのregression確認に使う。

## 4. 再移行は別作業

`migrate` は既存 `src/content/legacy/` とmigration由来資産を再生成し、migration台帳やredirect関連成果を上書きし得ます。現在のProduction mediaはprivate R2構成なので、再移行結果をそのままR2やProductionへ反映しません。通常確認の前処理ではありません。

必要な指示を受けた場合だけ、変更を保全したうえで新しい使い捨てcheckoutを作り、元バックアップを外部指定します。

```console
pnpm run migrate --backup-root "<backup-root>"
pnpm run check
pnpm run build
pnpm run validate --backup-root "<backup-root>"
git diff --stat
git status --short
```

原稿・素材・URL・台帳の差分を確認してから採否を判断します。`scripts/extract_affiliates.py` もmappingを再生成するため、onboardingで実行しません。既存の承認状態や未統合成果を上書きし得ます。

## 5. 歴史資料と未解決事項

`HATCHMAN_ARCHAEOLOGY.md` は元作業領域の `hatchman-archaeology/` にある発掘時の資料です。SHA-256と調査範囲は [Recovery調査](../reports/RECOVERY_AUDIT_2026-09-23.md) を参照します。保管場所を管理者へ確認し、日付と実物を照合してください。この資料がなくても現在の静的サイトはbuildできます。

資料中の移行案・旧パスを現在の手順へ自動適用しません。現行台帳と実装を優先し、矛盾や不足はBODへ返します。Amazon Previewの統合、商品採用、Domain / Mailの方式・切替、全体Architectureの判断はこの復旧手順の範囲外です。


## 6. Production復旧チェック

Production障害時は次を分離して確認します。

1. GitHub
   - `main` のSHA
   - open PR / 未統合branch
   - `pnpm check`
   - `pnpm build`
   - media / Functions関連test
2. Cloudflare Pages
   - project `hatchman`
   - Production branch `main`
   - latest Production deployment
   - custom domain `hatchman.org`
3. Cloudflare DNS
   - `hatchman.org` zoneがActiveか
   - authorityがCloudflare nameserverか
   - Pages custom domainと矛盾する旧origin recordがないか
4. R2
   - private bucket `hatchman-media`
   - Pages binding `MEDIA`
   - canonical object存在
5. 実HTTP
   - homepage / article
   - canonical `/media/*`
   - old media URL -> canonical 301
   - `?p=` / `?page_id=`
   - old slug
   - Range
   - ETag / If-None-Match
   - 404 / 405
   - cache header

注意:

- PreviewでPASSしてもProduction固有の挙動を省略しない。2026-09-30にはR2 conditional GETがProductionで500になりhotfixした。
- Cloudflare Browser Cache TTLがorigin `Cache-Control` を上書きしていないか確認する。
- HEADで `Content-Length` がないobjectは、GET body size / Content-Type / 必要ならSHA-256へfallbackして判定する。
- XServerはWeb hostingのRecovery先ではない。Registrarとhostingを混同しない。
