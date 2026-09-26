# Issues

この文書は、Hatchman service固有の未実行topicと再開点を保持する。

ここにあるだけでは現在の仕事ではない。
Hatchmanユニットが実行する仕事は `YDI-Unit-Hatchman/Instruction.md` から開始する。
ユニットの `Issues.md`（UL → BODの未解決判断）とは用途が異なる。

GitHub Issues機能は現在の仕事管理には使わない。

## Production復帰 — 旧GitHub Issue #2

### 目的

救出済みのHatchmanを `hatchman.org` へ戻す。

Recovery成功とproduction復帰は別のRealityとして扱う。

### 帰宅前に見るもの

- Webを本番へ戻す
- DNS migration
- MX / SPF / account recovery path
- XServerにまだ何が住んでいるか
- AdSense等の昔の関係をどう扱うか

### Domain / Mail方針 — 2026-09-26

- 類・家族が所有する外部サービスAccountのメールは `fodero.net` を使う。
- `hatchman.org` / `mathrao.com` のメールは、将来そのサービスを第三者へ提供し、サービス自体の窓口が必要になった場合に限って使う。
- Domain保管先は当面維持:
  - `hatchman.org`: XServer
  - `mathrao.com`: お名前.com
- Registrarは当面統一しない。将来DNSをCloudflareへ集約し、必要ならRegistrarもCloudflareへ寄せる方向。
- `hatchman.org` はXServerの独自ドメイン永久無料特典を利用中。

### Mail migration

- `google@hatchman.org` → `r1.google@fodero.net`
- `amazon@hatchman.org` → `r1.amazon@fodero.net`
- `affiliate@hatchman.org` → `r1@fodero.net`

Affiliateは今後ほぼ運用しない予定。残す少数サービスだけを `r1@fodero.net` へ変更する。

現時点で `mathrao.com` / `hatchman.org` のメールで登録されているサービスとして確認できているのは、Hatchman側のGoogle Accountのみ。

### Mail Routing Reality

Google Accountのメールアドレス変更時、Cloudflare Email Routingの二段forwarding経路でtemporary errorを確認。

- fodero.net側: `421 4.3.0 Upstream error`
- zzzu.net側: Gmail `421 4.7.28` temporary rate limit

現時点ではMail Architectureを変更せず、一時的なrate limitとして観測する。
旧 `google@hatchman.org` は移行完了まで削除しない。

### Resume point

残タスク:

> Google Accountのメールアドレスを `google@hatchman.org` から `r1.google@fodero.net` へ変更する。

次回Hatchman再開時は、この変更の成否確認から始める。

その後に、

- `amazon@hatchman.org` の移行
- Affiliate serviceの整理
- XServer離脱に必要な残存dependency確認
- `hatchman.org` DNS / Web切替

へ進む。

## Amazon Preview — 旧GitHub Issue #3

Recoveryで、mainより先へ進んでいる歴史的Amazon Previewが発掘されている。

まだ採用判断はしない。

### 遊びのタネ

- 現在のmainとの差分を見る
- 当時何を解こうとしていたか掘る
- 旧ASIN / Preview validationの記録と照らす
- 「昔は良かった」と「今も必要」を分ける

歴史資料を現在の採用済み実装と混ぜない。

> 遺跡を掘りたくなったら戻る。
