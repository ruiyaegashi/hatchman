# R2 / Pages Functions配信（STEP 28）

2026-09-29時点の実装。STEP 24で固定したcanonical key・記事参照を維持する。
R2実資産の投入とPreview / Productionへの反映は後続工程で行う。

## 再現手順

Node 22.12以降、package.json指定のpnpmを使用する。

```text
pnpm install --frozen-lockfile
pnpm media:check
pnpm build
pnpm check
pnpm functions:build
pnpm test:media
pnpm test:worker
pnpm functions:verify
```

`test:worker`は実際のbundleをローカルworkerdで実行する。一時的な10バイトの合成データのみをローカルR2へ書き、終了時に破棄する。Cloudflareへの接続や旧資産のuploadは行わない。

## データ生成

固定入力は `migration/media-canonical.json`、`migration/media-routes.json`、`migration/inventory.json`。
`scripts/generate_media_runtime.mjs`がmanifest、exact lookup table、公開記事ID table、`public/_routes.json`を決定的に生成する。

初回または実体再照合には次を使う。

```text
pnpm media:generate --staging <STEP24のcanonical stagingディレクトリ>
```

全実体のSHA-256とsizeを照合してから、実データのsignatureでContent-Typeを確定する。拡張子と内容が異なる画像も再圧縮しない。
通常buildは生成済みmanifestから再生成結果を照合し、未更新table・対象外route・target欠落・競合があれば失敗する。
採番やcanonical mappingを振り直さない。旧KEEP 5,000 source recordと、現行placeholder 1件は別に数える。今回の一意key数は5,001。

## 配信とroute

- `/media/`以下はmanifest掲載keyのみを `MEDIA` bindingからGET / HEADで取得する。PUT / DELETE等は405、未登録key・R2欠落は404。
- R2 metadata、ETag、Last-Modifiedを反映する。条件付きrequestは304 / 412、単一Rangeは206 / 416を返す。複数Rangeと不正Rangeは無視して通常GETとする。HEADではRangeを無視する。
- `legacy/`は1年間immutable、`site/`は1時間のHTTP cacheとする。Cache APIは使わない。
- 旧media pathnameをexact lookupしcanonicalへ直接301する。queryは引き継がない。未登録pathは静的Pagesへ渡す。
- root `/`の `p` / `page_id` は公開記事IDに限り301する。不明ID・複数指定・queryなしは静的homepageへ渡す。
- 通常記事404件と旧slug redirect383件はFunctions invocation対象外。
- source-managed `_routes.json`の7ルールをdistへコピーする。Wranglerの生成route一覧はmiddlewareにより `/*` になるが、これを配信用 `_routes.json`へ上書きしない。
- `/wallpaper_design.pdf`も旧media台帳に存在するためexact invocation ruleに含める。

旧台帳には `/index.php` のquery条件404件もある。STEP 27の「root `/`のみ」という確定仕様に従い、今回これらは有効化しない。元台帳は保持する。後続の旧URL全件検証では、この差異を明示して扱う。

## 設定と秘密情報

`wrangler.toml`は `wrangler pages download config hatchman` による2026-09-29の取得結果から作成した。既存compatibility date `2026-09-21`、project名、dist、非secret変数を維持し、Preview / Production両方に `MEDIA -> hatchman-media`を宣言する。
このファイルの追加だけではリモートbindingは変更されない。今回deployは行っていない。

取得結果のPreview変数に `AMAZON_CREATORS_CREDENTIAL_ID` / `AMAZON_CREATORS_CREDENTIAL_SECRET` が含まれていたため、値をローカル設定・保存用baseline・ログから除外した。Git管理しない。Cloudflare側は変更していない。Previewへ反映する前に、この2項目をCloudflareのSecretとして管理することを確認する。

`hatchman-media`はprivate、Public Access無効、Standard。r2.devやcustom domainで公開しない。runtimeはread処理だけを提供し、upload toolingとは分離する。
R2 binding自体はread-only権限を強制する仕組みではないため、アプリケーションが `get` / `head`だけを使用する構造にしている。

## binaryと次工程

STEP 28作業コピーでは `public/legacy-media/`を配信対象から外した。元STEP 24 repoとcanonical stagingは維持し、作業コピー内でも旧binaryを `.recovery/legacy-media/`へ退避している。
`public/media/`や`public/legacy-media/`が戻るとbuildを失敗させる。旧STEP 24正規化スクリプトのlocal hydrationは配信手順ではない。

STEP 29ではmanifestの一意keyだけを投入し、size・SHA-256・Content-Typeを検証する。STEP 30以降にPreviewで疎通を確認する。STEP 28のローカルPASSは実R2配信・公開済みを意味しない。

参考: [R2 Workers API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)、[Pages設定](https://developers.cloudflare.com/pages/functions/wrangler-configuration/)。
