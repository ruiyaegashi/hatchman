# Hatchman Amazonアソシエイト復旧設計

## 発掘結果

- 公開記事: 404
- Amazon表現を確認した記事: 68
- 旧商品出現: 167
- 一意な旧ASIN: 70
- 記事単位のASIN割当: 140（high）
- 解決前のAmazon短縮URL: 8（medium）
- 商品を割り当てていない記事: 337
- 旧アソシエイトタグ: 原稿から特定できず

全404記事を `affiliate/mapping.json` に収録した。旧ASINが明示されない記事へ、収益目的で商品を自動追加していない。

## 実装方式

原稿Markdownは変更せず、WP IDからmappingを引く。`display_status: approved` の商品だけを記事末尾に表示する。商品名・商品画像・Amazon発行URLはCloudflare Pages FunctionがAmazon Creators APIから取得する。画像はAmazonのURLを参照し、リポジトリや公開素材へ保存しない。価格・在庫は表示しない。

API応答はCDNで6時間、ブラウザで1時間までキャッシュする。認証トークンは実行中の分離環境内だけで再利用し、リポジトリやHTMLへ出力しない。Functionはmappingで承認済みのASINだけを受け付ける。

PA-API 5.0は2026-05-15に廃止されたため、新実装はCreators APIを使用する。必要な秘密情報はCloudflareのSecretとして設定する。

## 未完了

- Creators APIで旧ASINの現在状態を確認
- 旧商品、後継、代替の人間確認
- Hatchman用Associate tracking IDの確認
- `display_status` の承認

認証情報がない現段階では全商品を `pending` とし、公開ページに商品カードを出さない。
