# hatchman.org DNS・メール移行計画

調査日: 2026-09-22。今回は読み取り調査だけを行い、DNS、MX、メール配送、外部アカウントは変更していない。

## 現在の公開DNS

| 種別 | 現在値 |
|---|---|
| 権威DNS | `ns1.xserver.jp`〜`ns5.xserver.jp` |
| apex A | `183.90.250.44` |
| `www` A | `183.90.250.44` |
| `mail` A | `183.90.250.44` |
| MX | 優先度0、`hatchman.org` |
| SPF | `v=spf1 +a:sv1343.xserver.jp +a:hatchman.org +mx include:spf.sender.xserver.jp ~all` |
| DKIM | 調査した一般的selectorでは公開レコードを確認できず |
| DMARC | 公開TXTレコードなし |

現在はWeb、MX、mailが同じXServer IPへ集約されている。apexをCloudflare Pagesへ切り替えたままMXを `hatchman.org` に残すと、メール配送先もWeb側へ向く危険がある。

## 本番切替前の手順

1. XServer管理画面で、三つの既存メールボックスと送受信を確認する。
2. XServerが案内する最新のMX、SPF、DKIM値を管理画面から取得する。DKIMはDNSの推測値を使わない。
3. Cloudflare DNSへ、まず `mail.hatchman.org` のAレコード `183.90.250.44` を **DNS only** で作成する。
4. MXを `mail.hatchman.org` に向ける案をXServer仕様と照合する。XServerがapex MXを要求する場合は、その公式手順を優先する。
5. SPFを移植する。Webのapex A変更後は `+a:hatchman.org` の意味が変わるため、XServerが示す送信元を明示したレコードへ更新する。
6. XServerでDKIMを有効化し、提示されたselector/TXTをCloudflareへ登録する。
7. DMARCは最初に監視用 `p=none` から開始し、受信レポートを確認後に強化する。レポート用アドレスは人間が決める。
8. 三つのメールアドレスから送信、外部から受信、迷惑メール判定、SPF/DKIM/DMARC結果を確認する。
9. メール確認後にだけWebのapexと`www`をPagesへ接続する。

ネームサーバー、DNS、MX、メールサービスはまだ変更していない。
