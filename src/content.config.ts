import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const articles = defineCollection({
  loader: glob({ base: './src/content/legacy', pattern: '**/*.md' }),
  schema: z.object({
    title: z.string(),
    published_at: z.string(),
    status: z.enum(['publish', 'draft']).default('publish'),
    path: z.string().optional(),
    legacy_path: z.string().optional(),
  }).refine((data) => Boolean(data.path ?? data.legacy_path), {
    message: 'path or legacy_path is required',
  }),
});

export const collections = { articles };
