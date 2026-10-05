const TEST_KEY = 'content/ydi-step68-normal-operation.png';

async function snapshot(env) {
  const objects = [];
  let cursor;
  do {
    const page = await env.MEDIA.list({ limit: 1000, cursor });
    for (const object of page.objects ?? []) {
      objects.push({ key: object.key, size: object.size });
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);

  return {
    count: objects.length,
    total_bytes: objects.reduce((sum, object) => sum + object.size, 0),
    test_exists: objects.some((object) => object.key === TEST_KEY),
  };
}

export async function onRequestGet({ env }) {
  return Response.json(await snapshot(env), {
    headers: { 'cache-control': 'no-store' },
  });
}

export async function onRequestPost({ request, env }) {
  const body = await request.arrayBuffer();
  if (!body.byteLength) return new Response('empty body', { status: 400 });

  await env.MEDIA.put(TEST_KEY, body, {
    httpMetadata: { contentType: 'image/png' },
  });

  return Response.json(await snapshot(env), {
    headers: { 'cache-control': 'no-store' },
  });
}

export async function onRequestDelete({ env }) {
  await env.MEDIA.delete(TEST_KEY);
  return Response.json(await snapshot(env), {
    headers: { 'cache-control': 'no-store' },
  });
}
