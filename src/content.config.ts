import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const articles = defineCollection({
  loader: glob({ base: './src/content/articles', pattern: '**/*.md' }),
  schema: z.object({
    title: z.string(),
    published_at: z.string(),
    status: z.enum(['publish', 'draft']).default('publish'),
    path: z.string().optional(),
  }).refine((data) => data.status === 'draft' || Boolean(data.path), {
    message: 'path is required for published articles',
  }),
});

export const collections = { articles };
