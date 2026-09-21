import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const legacy = defineCollection({
  loader: glob({ base: './src/content/legacy', pattern: '**/*.md' }),
  schema: z.object({
    title: z.string(), wp_id: z.number(), content_type: z.enum(['post', 'page']),
    status: z.enum(['publish', 'draft']), published_at: z.string(), modified_at: z.string(),
    legacy_url: z.string(), legacy_path: z.string(), legacy_slug: z.string(),
    former_slugs: z.array(z.string()), parent_wp_id: z.number(),
    categories: z.array(z.string()), tags: z.array(z.string()),
    source_content_sha256: z.string(), source_content_chars: z.number(),
    migration_review: z.enum(['passed', 'review']),
  }),
});

export const collections = { legacy };
