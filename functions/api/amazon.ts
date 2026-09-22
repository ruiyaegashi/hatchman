import mapping from '../../affiliate/mapping.json';

interface Env {
  AMAZON_CREATORS_CREDENTIAL_ID: string;
  AMAZON_CREATORS_CREDENTIAL_SECRET: string;
  AMAZON_CREATORS_VERSION: string;
  AMAZON_ASSOCIATE_TAG: string;
}

type TestSearch = { key: string; keywords: string; search_index?: string; item_count?: number };
const config = mapping as typeof mapping & { test_searches?: TestSearch[] };
const allowedAsins = new Set(config.articles.flatMap((article) => article.products
  .filter((product) => ['approved', 'validation'].includes(product.display_status))
  .map((product) => product.current_asin)));
const allowedSearches = new Map((config.test_searches ?? []).map((search) => [search.key, search]));
let tokenCache: { value: string; expires: number } | undefined;

function tokenEndpoint(version: string) {
  return version.startsWith('3.3') ? 'https://api.amazon.co.jp/auth/o2/token'
    : version.startsWith('3.2') ? 'https://api.amazon.co.uk/auth/o2/token'
      : 'https://api.amazon.com/auth/o2/token';
}

async function accessToken(env: Env) {
  if (tokenCache && tokenCache.expires > Date.now() + 60_000) return tokenCache.value;
  const response = await fetch(tokenEndpoint(env.AMAZON_CREATORS_VERSION), {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ grant_type: 'client_credentials', client_id: env.AMAZON_CREATORS_CREDENTIAL_ID, client_secret: env.AMAZON_CREATORS_CREDENTIAL_SECRET, scope: 'creatorsapi::default' }),
  });
  if (!response.ok) throw new Error('Creators API authentication failed');
  const data = await response.json() as { access_token: string; expires_in: number };
  tokenCache = { value: data.access_token, expires: Date.now() + data.expires_in * 1000 };
  return data.access_token;
}

function product(item: any, associateTag: string) {
  let associateTagApplied = false;
  try { associateTagApplied = new URL(item.detailPageURL).searchParams.get('tag') === associateTag; } catch { /* invalid upstream URL */ }
  return { asin: item.asin, title: item.itemInfo?.title?.displayValue ?? item.asin, url: item.detailPageURL, image: item.images?.primary?.medium?.url, associateTagApplied };
}

export const onRequestGet = async (context: { request: Request; env: Env }) => {
  try {
    const url = new URL(context.request.url);
    const search = url.searchParams.get('search');
    const asins = (url.searchParams.get('asins') ?? '').split(',').filter(Boolean);
    const token = await accessToken(context.env);
    let response: Response;
    let mode: 'search' | 'items';

    if (search) {
      const request = allowedSearches.get(search);
      if (!request) return Response.json({ error: 'invalid search' }, { status: 400 });
      mode = 'search';
      response = await fetch('https://creatorsapi.amazon/catalog/v1/searchItems', {
        method: 'POST', headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', 'x-marketplace': 'www.amazon.co.jp' },
        body: JSON.stringify({ partnerTag: context.env.AMAZON_ASSOCIATE_TAG, keywords: request.keywords, searchIndex: request.search_index ?? 'All', itemCount: request.item_count ?? 5, marketplace: 'www.amazon.co.jp', resources: ['images.primary.medium', 'itemInfo.title'] }),
      });
    } else {
      if (asins.length < 1 || asins.length > 10 || asins.some((asin) => !/^[A-Z0-9]{10}$/.test(asin) || !allowedAsins.has(asin))) return Response.json({ error: 'invalid ASIN list' }, { status: 400 });
      mode = 'items';
      response = await fetch('https://creatorsapi.amazon/catalog/v1/getItems', {
        method: 'POST', headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', 'x-marketplace': 'www.amazon.co.jp' },
        body: JSON.stringify({ itemIds: asins, itemIdType: 'ASIN', marketplace: 'www.amazon.co.jp', partnerTag: context.env.AMAZON_ASSOCIATE_TAG, resources: ['images.primary.medium', 'itemInfo.title'] }),
      });
    }
    if (!response.ok) {
      let upstream: Array<{ code?: string; message?: string }> = [];
      try {
        const failure = await response.json() as any;
        upstream = (failure.errors ?? failure.Errors ?? []).slice(0, 3).map((item: any) => ({ code: item.code ?? item.Code, message: item.message ?? item.Message }));
        if (!upstream.length && (failure.type || failure.reason || failure.message)) upstream = [{ code: failure.reason ?? failure.type, message: failure.message }];
      } catch { /* Amazon did not return JSON */ }
      return Response.json({ error: 'Creators API request failed', status: response.status, upstream }, { status: 502 });
    }
    const data = await response.json() as any;
    const source = mode === 'search' ? data.searchResult?.items ?? [] : data.itemsResult?.items ?? [];
    return Response.json({ mode, items: source.map((item: any) => product(item, context.env.AMAZON_ASSOCIATE_TAG)), disclaimer: 'Amazonの商品情報は変更または削除される場合があります。' }, { headers: { 'cache-control': 'public, max-age=900, s-maxage=3600' } });
  } catch (error) {
    const message = error instanceof Error && error.message === 'Creators API authentication failed' ? error.message : 'Amazon product data is unavailable';
    return Response.json({ error: message }, { status: 503 });
  }
};
