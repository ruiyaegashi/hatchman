export interface Step51Env {
  MEDIA: R2Bucket;
}

type Context = {
  request: Request;
  env: Step51Env;
};

const EXPECTED_COUNT = 4995;
const EXPECTED_BYTES = 674646234;
const SOURCE_PREFIX = 'legacy/';
const DEST_PREFIX = 'content/asset-';
const BATCH_SIZE = 50;

function destinationKey(sourceKey: string): string {
  const match = /^legacy\/legacy-(\d{6})\.([A-Za-z0-9]+)$/.exec(sourceKey);
  if (!match) throw new Error(`unexpected source key: ${sourceKey}`);
  return `content/asset-${match[1]}.${match[2]}`;
}

async function sha256Hex(buffer: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

function metadataShape(object: R2ObjectBody): string {
  const h = object.httpMetadata ?? {};
  return JSON.stringify({
    contentType: h.contentType ?? null,
    contentLanguage: h.contentLanguage ?? null,
    contentDisposition: h.contentDisposition ?? null,
    contentEncoding: h.contentEncoding ?? null,
    cacheControl: h.cacheControl ?? null,
    cacheExpiry: h.cacheExpiry ? h.cacheExpiry.toISOString() : null,
    customMetadata: Object.fromEntries(
      Object.entries(object.customMetadata ?? {}).sort(([a], [b]) => a.localeCompare(b)),
    ),
  });
}

async function listSummary(bucket: R2Bucket, prefix: string) {
  let cursor: string | undefined;
  let count = 0;
  let bytes = 0;
  do {
    const page = await bucket.list({ prefix, limit: 1000, cursor });
    for (const object of page.objects) {
      count += 1;
      bytes += object.size;
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return { count, bytes };
}

async function copyOne(bucket: R2Bucket, sourceKey: string) {
  const targetKey = destinationKey(sourceKey);
  const source = await bucket.get(sourceKey);
  if (!source) throw new Error(`source missing: ${sourceKey}`);

  const sourceBuffer = await source.arrayBuffer();
  const sourceHash = await sha256Hex(sourceBuffer);
  const sourceMetadata = metadataShape(source);

  let target = await bucket.get(targetKey);
  let created = false;

  if (!target) {
    await bucket.put(targetKey, sourceBuffer, {
      httpMetadata: source.httpMetadata,
      customMetadata: source.customMetadata,
    });
    created = true;
    target = await bucket.get(targetKey);
  }

  if (!target) throw new Error(`target missing: ${targetKey}`);

  const targetBuffer = await target.arrayBuffer();
  const targetHash = await sha256Hex(targetBuffer);

  if (source.size !== target.size) throw new Error(`size mismatch: ${sourceKey}`);
  if (sourceHash !== targetHash) throw new Error(`sha256 mismatch: ${sourceKey}`);
  if (sourceMetadata !== metadataShape(target)) throw new Error(`metadata mismatch: ${sourceKey}`);

  return { created, bytes: source.size, sourceKey, targetKey };
}

async function copyBatch(bucket: R2Bucket, cursor?: string) {
  const page = await bucket.list({ prefix: SOURCE_PREFIX, limit: BATCH_SIZE, cursor });
  const results = new Array<Awaited<ReturnType<typeof copyOne>>>(page.objects.length);
  let next = 0;

  const workers = Array.from({ length: Math.min(8, page.objects.length) }, async () => {
    while (true) {
      const index = next++;
      if (index >= page.objects.length) return;
      results[index] = await copyOne(bucket, page.objects[index].key);
    }
  });

  await Promise.all(workers);

  return {
    processed: results.length,
    created: results.filter(r => r.created).length,
    verifiedExisting: results.filter(r => !r.created).length,
    bytes: results.reduce((sum, r) => sum + r.bytes, 0),
    first: results[0]?.sourceKey ?? null,
    last: results.at(-1)?.sourceKey ?? null,
    nextCursor: page.truncated ? page.cursor : null,
    truncated: page.truncated,
  };
}

export async function handleStep51(context: Context): Promise<Response> {
  try {
    const url = new URL(context.request.url);

    if (context.request.method === 'GET') {
      const [source, destination] = await Promise.all([
        listSummary(context.env.MEDIA, SOURCE_PREFIX),
        listSummary(context.env.MEDIA, DEST_PREFIX),
      ]);

      if (source.count !== EXPECTED_COUNT || source.bytes !== EXPECTED_BYTES) {
        throw new Error(`source accounting mismatch: ${source.count}/${source.bytes}`);
      }
      if (destination.count > EXPECTED_COUNT || destination.bytes > EXPECTED_BYTES) {
        throw new Error(`destination accounting impossible: ${destination.count}/${destination.bytes}`);
      }

      return Response.json({ ready: true, source, destination }, {
        headers: { 'cache-control': 'no-store' },
      });
    }

    if (context.request.method !== 'POST') {
      return new Response(null, { status: 405, headers: { Allow: 'GET, POST' } });
    }

    const cursor = url.searchParams.get('cursor') || undefined;
    const result = await copyBatch(context.env.MEDIA, cursor);
    return Response.json({ status: 'ok', ...result }, {
      headers: { 'cache-control': 'no-store' },
    });
  } catch (error) {
    return Response.json({
      status: 'error',
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500, headers: { 'cache-control': 'no-store' } });
  }
}
