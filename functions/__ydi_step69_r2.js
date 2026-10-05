export async function onRequestGet({ env }) {
  const objects = [];
  let cursor;
  do {
    const page = await env.MEDIA.list({ limit: 1000, cursor });
    for (const object of page.objects ?? []) objects.push({ key: object.key, size: object.size });
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  objects.sort((a,b)=>a.key.localeCompare(b.key));
  return Response.json({
    count: objects.length,
    total_bytes: objects.reduce((n,o)=>n+o.size,0),
    objects
  }, {headers:{"cache-control":"no-store"}});
}
