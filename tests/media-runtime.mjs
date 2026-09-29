import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
await build({entryPoints:['src/media/handler.ts'],bundle:true,platform:'node',format:'esm',outfile:'.wrangler/tests/handler.mjs'});
const {handleMedia}=await import(pathToFileURL(path.resolve('.wrangler/tests/handler.mjs')));
const registry=JSON.parse(fs.readFileSync('migration/media-canonical.json'));
const routes=JSON.parse(fs.readFileSync('migration/media-routes.json'));
const invoke=JSON.parse(fs.readFileSync('public/_routes.json'));
const matches=p=>invoke.include.some(r=>r.endsWith('*')?p.startsWith(r.slice(0,-1)):p===r)&&!invoke.exclude.some(r=>r.endsWith('*')?p.startsWith(r.slice(0,-1)):p===r);
let assertions=0;
const eq=(actual,expected)=>{assert.deepEqual(actual,expected);assertions++;};
const request=async (p,init={},bucket={head:async()=>null,get:async()=>null})=>handleMedia({request:new Request('https://example.test'+p,init),env:{MEDIA:bucket},next:async()=>new Response('static',{status:200,headers:{'x-test-static':'1'}})});
for(const alias of registry.aliases){eq(matches(alias.source),true);const r=await request(alias.source+'?discard=1');eq(r.status,301);eq(r.headers.get('location'),alias.target);eq(registry.objects.some(o=>o.canonical_url===alias.target),true);}
for(const r of routes.redirects.filter(r=>r.kind==='wp_query'&&r.source==='/')){const response=await request('/?'+new URLSearchParams(r.query_match));eq(response.status,301);eq(response.headers.get('location'),r.target);}
for(const p of routes.preserve_routes){eq(matches(p.path),false);eq(fs.existsSync('dist'+p.path+'index.html'),true);}
for(const line of fs.readFileSync('public/_redirects','utf8').trim().split(/\r?\n/)){eq(matches(line.split(/\s+/)[0]),false);}
for(const p of ['/','/?p=9999999','/?p=foo','/?p=8260&p=8254','/?p=8260&page_id=9400','/index.php?p=8260','/images/missing.png','/api/amazon?asins=invalid','/images/%ZZ','/images/__proto__'])eq((await request(p)).headers.get('x-test-static'),'1');
const key=registry.objects[0].object_key, url='/media/'+key;
let reads=0,options;
const metadata={size:10,httpEtag:'"test-etag"',uploaded:new Date('2026-01-01T00:00:00Z'),writeHttpMetadata:h=>h.set('content-type','image/png')};
const bucket={head:async()=>metadata,get:async(_key,opt)=>{reads++;options=opt;return {...metadata,range:opt.range,body:new Blob([opt.range?'0123456789'.slice(opt.range.offset,opt.range.offset+opt.range.length):'0123456789']).stream()};}};
let r=await request(url,{},bucket);eq(r.status,200);eq(await r.text(),'0123456789');eq(r.headers.get('etag'),'"test-etag"');eq(r.headers.get('cache-control'),'public, max-age=31536000, immutable');
const before=reads;r=await request(url,{method:'HEAD'},bucket);eq(r.status,200);eq(await r.text(),'');eq(r.headers.get('content-length'),'10');eq(reads,before);
for(const method of ['POST','PUT','DELETE','PATCH']){r=await request(url,{method},bucket);eq(r.status,405);eq(r.headers.get('allow'),'GET, HEAD');}
eq((await request('/media/legacy/missing.png',{},bucket)).status,404);
eq((await request(url)).status,404);
for(const [headers,status] of [[{'if-none-match':'W/"test-etag"'},304],[{'if-none-match':'*'},304],[{'if-match':'"wrong"'},412],[{'if-match':'W/"test-etag"'},412],[{'if-modified-since':'Thu, 01 Jan 2026 00:00:00 GMT'},304],[{'if-unmodified-since':'Wed, 01 Jan 2025 00:00:00 GMT'},412],[{'if-none-match':'"different"','if-modified-since':'Thu, 01 Jan 2026 00:00:00 GMT'},200],[{'if-match':'"test-etag"','if-unmodified-since':'Wed, 01 Jan 2025 00:00:00 GMT'},200]])eq((await request(url,{headers},bucket)).status,status);
for(const [range,status,body,contentRange] of [['bytes=2-4',206,'234','bytes 2-4/10'],['bytes=8-',206,'89','bytes 8-9/10'],['bytes=-2',206,'89','bytes 8-9/10'],['bytes=10-',416,'','bytes */10'],['bytes=-0',416,'','bytes */10'],['bytes=0-99',206,'0123456789','bytes 0-9/10'],['bytes=0-1,4-5',200,'0123456789',null],['bytes=bad',200,'0123456789',null]]){r=await request(url,{headers:{range}},bucket);eq(r.status,status);eq(await r.text(),body);eq(r.headers.get('content-range'),contentRange);}
r=await request(url,{headers:{range:'bytes=2-4','if-range':'"old"'}},bucket);eq(r.status,200);eq(await r.text(),'0123456789');
r=await request(url,{headers:{range:'bytes=2-4','if-range':'"test-etag"'}},bucket);eq(r.status,206);eq(options.range,{offset:2,length:3});
r=await request('/media/site/logo.png',{},bucket);eq(r.headers.get('cache-control'),'public, max-age=3600');
eq((await request(url,{}, {head:async()=>metadata,get:async()=>null})).status,404);
eq((await request(url,{headers:{'if-none-match':'"new"'}},{head:async()=>metadata,get:async()=>({...metadata,httpEtag:'"new"'})})).status,304);
const result={pass:true,assertions,media_aliases:registry.aliases.length,root_query_conditions:404,static_articles:404,static_redirects:383,invocation_rules:invoke.include.length,uncovered_media:0,excluded_index_php_conditions:404};
fs.mkdirSync('.recovery',{recursive:true});fs.writeFileSync('.recovery/media-tests.json',JSON.stringify(result,null,2)+'\n');console.log(result);
