import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://hatchman.org',
  output: 'static',
  trailingSlash: 'always',
  markdown: { shikiConfig: { wrap: true } },
});
