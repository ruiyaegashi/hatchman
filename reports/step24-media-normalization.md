# STEP 24 — Media正規化のローカル実施結果

実施日: 2026-09-28。BOD `Issues/Hatchman-Production.md` のSTEP 23確定仕様に基づきSTEP 24を実施。

## 結果

| 項目 | 結果 |
|---|---:|
| 旧KEEP canonical実体 | 5,000 / 675,034,180 bytes |
| site/（旧KEEP） | 5 |
| legacy/（旧KEEP） | 4,995 |
| 現行サイトの安全な外部画像placeholder | 別枠1（site/） |
| 現行画像の旧実体数 → canonical実体数 | 3,371 → 3,348 |
| SHA-256完全一致の重複統合 | 23 / 2,923,119 bytes |
| 更新した記事ファイル | 403 |
| 更新したmedia参照 | 3,439（placeholderを含む） |
| canonical media aliases | 20,276 |
| 保持した既存routing条件 | 16,466 |
| build | PASS / 419ページ |
| 公開記事 / draft | 404 / 3（draftは未生成） |
| 既存記事redirect | 383、変更なし |
| 参照欠落 / 非canonical参照 / 内部リンク切れ | 0 / 0 / 0 |
| mapping競合 / chain / loop / target欠落 | 0 / 0 / 0 / 0 |
| KEEP保持 / REDIRECT保持 | 5,000 / 11,111 |
| 元16,111実体のSHA-256・容量・mtime・属性差分 | 0 |
| 元実体合計 | 881,265,711 bytes、変更なし |

`wallpaper_design.pdf` はKEEPとしてcanonical stagingに保持。`articles/` は今回未使用。採番は元パスのUnicode codepoint順で初回だけ実施し、永続台帳で固定。拡張子の大小文字も維持した。

元のKEEP／REDIRECTと、元repoの`public/legacy-media/`は削除していない。統合結果はcanonical集合の実体数であり、PC全体の空き容量増加ではない。

## 検証Evidence

- 元manifestの最終分類（BODの3件判断適用）と削除後16,111実体を全件SHA-256照合。
- stagingの全5,000 KEEP＋placeholderについてSHA-256を検証。同一SHA-256のcanonical重複0。
- 現行画像3,371パスすべてで変更前とcanonicalのSHA-256一致。画像再圧縮・crop変更なし。
- 元の全src blobを基準に、記事変更がURLトークン置換だけであることを検証。本文・markup・改行形式は不変。
- `check_media_build.mjs`でbuild用3,349実体のハッシュを確認し、Astro build成功。
- `validate_media.py`: 419 HTMLのcanonical参照3,439件、参照欠落0、source差分0。
- `validate_migration.py`: 元SQLの407本文ハッシュ一致、404公開記事、draft漏出0、既存383 redirect維持、画像欠落0、内部リンク切れ0、fatal空。
- 参照変換の再実行は変更0ファイル／0置換。
- ローカルブラウザで`/ramen-kodawariramenwakatora/`のレイアウトとcanonical画像6件の読込成功を確認。

## Runtime Reality / 停止点

current main `6f1c205fbeeccb120fb8af9fe56a43c913498679`と同一tree `36a0e87badf960dfdd188aa74ea183336d05543c`を基準に、独立したローカル作業用repoで変更した。元のローカルrepoは古いcommitだったため、GitHubで2ファイルの差分を取得し、基準tree一致まで確認した。GitHubへのpush、PR作成、main更新は行っていない。

依存フォルダを既存checkoutから参照する構成ではpnpmの自動依存確認が拒否したため、package scriptと同じbuild guardとAstro CLIを直接実行した。Astro telemetryを無効化し、Astro/Viteキャッシュを作業用repoの`.astro/`に分離してbuild成功。依存のインストール・更新はしていない。

ローカルcanonical stagingと検証用`public/media/`を作成。新規binaryはGit管理対象外。旧URL台帳は生成しただけでroutingへ未適用。R2 upload・bucket作成、Pages Functions実装、Preview／Production deploy、本番変更、REDIRECT削除は未実施。

STEP 24完了で停止。canonical配信の実装前にこの参照変更を本番へ出さない。詳細な再現方法とContent-Type留意点は`docs/MEDIA_NORMALIZATION.md`を参照。
