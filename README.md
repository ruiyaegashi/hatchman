# Hatchman 2.0

2012〜2020年の旧WordPressブログを保存するAstro製の静的アーカイブです。

## 着任・復旧の入口

部署の責任・情報flowはYDIの [Organization](https://github.com/ruiyaegashi/YDI/blob/main/docs/Organization.md) / [Information Flow](https://github.com/ruiyaegashi/YDI/blob/main/docs/Information_Flow.md) を参照します（private repositoryへのアクセスが必要です）。

- [Recovery手順](docs/RECOVERY.md): main・全branch・未反映変更の確認、通常build、元バックアップ照合、再移行の区別。
- [2026-09-23 Recovery調査](reports/RECOVERY_AUDIT_2026-09-23.md): 未統合Amazon成果、発掘台帳の所在、調査時点の不明点。
- [移行レポート](reports/MIGRATION_REPORT.md) / [保存済み検証結果](reports/validation.json): 過去の検証記録。現在のbuild・公開状態の証明とは区別します。

## 通常のローカル確認（元バックアップ不要）

Node.jsは `package.json` のengines、pnpmはpackageManager、依存関係はlockfileに従います。

```console
pnpm install --frozen-lockfile
pnpm run check
pnpm run build
pnpm run dev
```

`dev` はローカル開発サーバーです。Cloudflare Pages Functionsや本番DNS・メール・Amazon APIの動作確認にはなりません。

`src/content/legacy/` が移行後コンテンツの正本です。`status: draft` の3件は保存されますが、サイトには生成されません。

## 元バックアップを使う作業

Python 3.12で検証しています。`python` がPATH上で使える状態で、[Recovery手順](docs/RECOVERY.md)に従って `--backup-root` または `HATCHMAN_BACKUP_ROOT` を指定します。Pythonスクリプトは `.env` を自動読込しません。

- `pnpm run validate --backup-root "<バックアップの保存先>"`: build後にSQLと照合。結果はGit管理外の `.recovery/validation.json` へ出力します。
- `pnpm run migrate --backup-root "<バックアップの保存先>"`: 原稿・素材・移行台帳・転送を再生成する別作業です。通常のonboardingでは実行せず、再生成が必要な場合だけ使い捨てcheckoutで実行します。

旧バックアップはデータとして読みます。旧PHP、テーマ、プラグイン、JavaScriptは実行もコピーもしません。バックアップや秘密情報はrepository外で保管してください。
