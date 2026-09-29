import { handleMedia } from '../src/media/handler';
import type { MediaEnv } from '../src/media/handler';
export const onRequest: PagesFunction<MediaEnv> = context => handleMedia(context);
