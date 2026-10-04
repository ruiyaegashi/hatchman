export interface MediaEnv {
  MEDIA: Pick<R2Bucket, 'get' | 'head'>;
}

type Context = {
  request: Request;
  env: MediaEnv;
  next: () => Promise<Response>;
};

function headersFor(object: R2Object) {
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set('etag', object.httpEtag);
  headers.set('last-modified', object.uploaded.toUTCString());
  headers.set('cache-control', 'public, max-age=3600');
  return headers;
}

export async function handleMedia(context: Context): Promise<Response> {
  const { request } = context;
  const url = new URL(request.url);

  let pathname: string;
  try {
    pathname = decodeURIComponent(url.pathname);
  } catch {
    return context.next();
  }

  if (!pathname.startsWith('/media/')) return context.next();

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return new Response(null, { status: 405, headers: { Allow: 'GET, HEAD' } });
  }

  const key = pathname.slice('/media/'.length);
  if (!key) return new Response(null, { status: 404 });

  if (request.method === 'HEAD') {
    const object = await context.env.MEDIA.head(key);
    if (!object) return new Response(null, { status: 404 });
    const headers = headersFor(object);
    headers.set('content-length', String(object.size));
    return new Response(null, { headers });
  }

  const object = await context.env.MEDIA.get(key);
  if (!object) return new Response(null, { status: 404 });

  const headers = headersFor(object);
  headers.set('content-length', String(object.size));
  return new Response(object.body, { headers });
}
