import { handleMedia } from '../src/media/handler';
import { handleStep51 } from '../src/media/step51';
import type { Step51Env } from '../src/media/step51';

export const onRequest: PagesFunction<Step51Env> = context => {
  const url = new URL(context.request.url);
  if (url.pathname === '/media/__step51-fixed-copy-20261005') {
    return handleStep51(context);
  }
  return handleMedia(context);
};
