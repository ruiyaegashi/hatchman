# Hatchman

Hatchman is a small Astro site that keeps the rescued articles and their media online.

## Production requirements

1. Existing articles remain available, including their images and files.
2. Markdown lives in GitHub. Images and other binary files live in Cloudflare R2.
3. New articles can be added as Markdown.

Everything else from the old WordPress migration is intentionally outside the production design.

## Structure

- `src/content/legacy/`: article Markdown. Existing rescued articles stay here; new articles can be added here too.
- `src/pages/index.astro`: article list.
- `src/pages/[...legacy].astro`: article pages.
- `functions/_middleware.ts` + `src/media/handler.ts`: minimal `/media/*` delivery from R2.
- `wrangler.toml`: Cloudflare Pages / R2 binding.

The current article Markdown already points to `/media/...` for rescued media.

## Add an article

Create a Markdown file under `src/content/legacy/` with at least:

```yaml
---
title: "Article title"
published_at: "2026-10-04 12:00:00"
path: "/article-path/"
status: publish
---
```

Then write the article body below the front matter. Upload any images/files to R2 and reference them as `/media/<object-key>`.

## Local check

```console
pnpm install --frozen-lockfile
pnpm run check
pnpm run build
pnpm run dev
```

The site is intentionally minimal. The original Hatchman top header is the only visual element planned for restoration.
