import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://hatchman.org',
  output: 'static',
  cacheDir: './.astro/cache',
  vite: { cacheDir: '.astro/vite' },
  trailingSlash: 'always',
  markdown: { shikiConfig: { wrap: true } },
});
