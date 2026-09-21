# Hatchman 2.0

2012〜2020年の旧WordPressブログを保存するAstro製の静的アーカイブです。

## ローカル確認

```console
pnpm install
pnpm run migrate
pnpm run check
pnpm run build
pnpm run validate
pnpm run dev
```

`scripts/migrate_legacy.py` は旧バックアップをデータとして読み、本文Markdown、旧slugリダイレクト、本文参照画像の許可リストを再生成します。旧PHP、テーマ、プラグイン、JavaScriptは実行もコピーもしません。

`src/content/legacy/` が移行後コンテンツの正本です。`status: draft` の3件は保存されますが、サイトには生成されません。
