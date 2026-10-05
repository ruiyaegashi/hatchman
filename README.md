# Hatchman

Hatchman is a small Astro site for articles and their media.

## Production requirements

1. Existing articles remain available, including their images and files.
2. Article Markdown lives in GitHub. Images and other binary files live in Cloudflare R2.
3. New articles can be added as Markdown.

## Structure

- `src/content/articles/`: article Markdown.
- `src/pages/index.astro`: article list.
- `src/pages/[...path].astro`: article pages generated from frontmatter `path`.
- `functions/_middleware.ts` + `src/media/handler.ts`: minimal `/media/*` delivery from R2.
- `wrangler.toml`: Cloudflare Pages / R2 binding.

## Add an article

Create a Markdown file under `src/content/articles/` with:

```yaml
---
title: "Article title"
published_at: "2026-10-05 12:00:00"
path: "/article-path/"
status: publish
---
```

Then write the article body below the front matter.

Draft articles may omit `path` until they are ready to publish.

## Media

Upload images and other binary files to the private R2 bucket and reference them through `/media/<object-key>`.
The runtime maps that URL directly to the same R2 object key.

## Local check

```console
pnpm install --frozen-lockfile
pnpm run check
pnpm run build
pnpm run functions:build
```

The site intentionally keeps the runtime and content model minimal.
