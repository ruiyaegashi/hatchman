# STEP 24: local canonical media normalization

Decision: YDI `Issues/Hatchman-Production.md`, STEP 23 / STEP 24, 2026-09-28.
Source service main: `6f1c205fbeeccb120fb8af9fe56a43c913498679`.

This is a local preparation step. R2 upload, Pages Functions delivery, preview and production deployment have **not** been implemented or performed. Do not deploy these article URL changes until canonical delivery is implemented and validated in the later steps.

## Fixed canonical registry

- `migration/media-canonical.json` owns permanent object keys, SHA-256, source paths, source classifications and direct URL aliases.
- Exactly 5 confirmed old shared assets use `site/`: favicon.ico, icon160.png, logo-1.png, logo.png and logo_title.png. Their distinct roles are preserved; similar-looking logos are not content duplicates.
- The other 4,995 old KEEP objects use `legacy/legacy-XXXXXX.ext`. Initial IDs follow Unicode codepoint ordering of the complete source path. Original extension spelling is preserved, including uppercase extensions. Existing IDs are read from the registry by SHA-256 and are never renumbered. Changes to an existing registry require review.
- `articles/` is reserved for future articles and is unused here.
- Exact SHA-256 content is deduplicated. Similar images/crops are not treated as identical.
- The existing safe external-image placeholder is a separate current-site object, `site/external-image-disabled.svg`. It is not counted in the old KEEP 5,000.
- `migration/media-routes.json` preserves all 16,466 original route conditions. Media targets now point directly to canonical objects. Old slug and WordPress query conditions remain unchanged; this file is data only and is not wired into routing.
- `media-canonical.json` also records all KEEP URLs and current media URLs, giving 20,276 direct media aliases. This count is distinct from the 16,466 original mixed media/article/query conditions.
- `migration/asset-map.json` retains original/source evidence and adds `previous_public_path`; `public_path` is canonical. Original/source fields are provenance, not live page references.

The 3,371 previous current image paths converge to 3,348 canonical content objects, consolidating 23 duplicates. The old repository `public/legacy-media` files and all 11,111 local REDIRECT source files are intentionally retained during STEP 24. Canonical staging has one copy per content. No source deletion or rename is performed.

## Local reproduction

Use Python 3.12+, Node matching package.json, and installed repository dependencies. The analysis directory contains `public_html_manifest.csv`, `cleanup_report.md`, and `legacy_redirects.json`.

```powershell
python scripts/normalize_media.py --source-root C:\ChatGPT\YDI\Hatchman\backup\public_html --analysis-root C:\ChatGPT\YDI\Hatchman --staging C:\path\to\hatchman-media
$env:ASTRO_TELEMETRY_DISABLED='1'
pnpm run build
python scripts/validate_media.py --source-root C:\ChatGPT\YDI\Hatchman\backup\public_html --staging C:\path\to\hatchman-media
python scripts/validate_migration.py --backup-root C:\ChatGPT\YDI\Hatchman\backup
```

Normalization checks all source hashes, stages 5,000 old KEEP objects plus the placeholder, rewrites current references and hydrates only 3,348 current objects plus the placeholder into ignored `public/media/` for a local static build. Build checks every hydrated content hash and fails if assets are absent. Canonical binaries are not added to Git. An ordinary clean checkout cannot yet serve `/media/` without local hydration or the future R2 layer.

The original SQL migration calls `apply_canonical_references` when the canonical registry exists, so regenerated article references retain the fixed mapping. Source article byte comparisons verify that STEP 24 changes only URL tokens, preserving text, markup and original line endings.

Validation checks built references, staged content, direct mappings, preserved route conditions, old static image content, and all 16,111 source files including SHA-256, length, mtime and file attributes. The pre-normalization source snapshot and reports are local `.recovery/` files.

## Runtime notes

The local dependency directory in this execution was reused read-only from the existing Hatchman checkout. pnpm's automatic dependency check rejects that junction; the build guard and the same Astro CLI used by the package script were therefore executed directly. Telemetry was disabled and Astro/Vite caches were placed in this checkout's ignored `.astro/` directory. This does not require a production configuration change.

`images/02_31.png` contains JPEG bytes (already recorded as signature-corrected in the original migration). STEP 23 requires preserving the original extension, so its canonical key ends in `.png`; bytes are unchanged. The future R2 upload/delivery step must determine Content-Type from the actual content, not only the extension. No image transcoding is performed here.

Stop after STEP 24 verification. STEP 25/26 source re-scan and REDIRECT deletion, R2 implementation and uploads, routing activation, and any deployment remain separate work.
