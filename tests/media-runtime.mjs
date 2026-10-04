import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

await build({entryPoints:['src/media/handler.ts'],bundle:true,platform:'node',format:'esm',outfile:'.wrangler/tests/handler.mjs'});
const {handleMedia}=await import(pathToFileURL(path.resolve('.wrangler/tests/handler.mjs')));
const invoke=JSON.parse(fs.readFileSync('public/_routes.json'));
const matches=p=>invoke.include.some(r=>r.endsWith('*')?p.startsWith(r.slice(0,-1)):p===r)&&!invoke.exclude.some(r=>r.endsWith('*')?p.startsWith(r.slice(0,-1)):p===r);
let assertions=0;
const eq=(actual,expected)=>{assert.deepEqual(actual,expected);assertions++;};
const request=async (p,init={},bucket={head:async()=>null,get:async()=>null})=>handleMedia({request:new Request('https://example.test'+p,init),env:{MEDIA:bucket},next:async()=>new Response('static',{status:200,headers:{'x-test-static':'1'}})});

eq(matches('/media/legacy/example.jpg'),true);
eq(matches('/api/amazon'),true);
for(const p of ['/','/?p=8260','/post-8260/','/images/0-04.png','/wp-content/uploads/example.jpg','/legacy-media/example.jpg']){
  eq((await request(p)).headers.get('x-test-static'),'1');
}

const key='legacy/legacy-000001.png', url='/media/'+key;
let reads=0,options;
const metadata={size:10,httpEtag:'"test-etag"',uploaded:new Date('2026-01-01T00:00:00Z'),writeHttpMetadata:h=>h.set('content-type','image/png')};
const bucket={head:async requested=>requested===key?metadata:null,get:async (requested,opt)=>{if(requested!==key)return null;reads++;options=opt;return {...metadata,range:opt.range,body:new Blob([opt.range?'0123456789'.slice(opt.range.offset,opt.range.offset+opt.range.length):'0123456789']).stream()};}};

let r=await request(url,{},bucket);eq(r.status,200);eq(await r.text(),'0123456789');eq(r.headers.get('etag'),'"test-etag"');eq(r.headers.get('cache-control'),'public, max-age=31536000, immutable');
const before=reads;r=await request(url,{method:'HEAD'},bucket);eq(r.status,200);eq(await r.text(),'');eq(r.headers.get('content-length'),'10');eq(reads,before);
for(const method of ['POST','PUT','DELETE','PATCH']){r=await request(url,{method},bucket);eq(r.status,405);eq(r.headers.get('allow'),'GET, HEAD');}
eq((await request('/media/legacy/missing.png',{},bucket)).status,404);
for(const [headers,status] of [[{'if-none-match':'W/"test-etag"'},304],[{'if-none-match':'*'},304],[{'if-match':'"wrong"'},412],[{'if-match':'W/"test-etag"'},412],[{'if-modified-since':'Thu, 01 Jan 2026 00:00:00 GMT'},304],[{'if-unmodified-since':'Wed, 01 Jan 2025 00:00:00 GMT'},412],[{'if-none-match':'"different"','if-modified-since':'Thu, 01 Jan 2026 00:00:00 GMT'},200],[{'if-match':'"test-etag"','if-unmodified-since':'Wed, 01 Jan 2025 00:00:00 GMT'},200]])eq((await request(url,{headers},bucket)).status,status);
for(const [range,status,body,contentRange] of [['bytes=2-4',206,'234','bytes 2-4/10'],['bytes=8-',206,'89','bytes 8-9/10'],['bytes=-2',206,'89','bytes 8-9/10'],['bytes=10-',416,'','bytes */10'],['bytes=-0',416,'','bytes */10'],['bytes=0-99',206,'0123456789','bytes 0-9/10'],['bytes=0-1,4-5',200,'0123456789',null],['bytes=bad',200,'0123456789',null]]){r=await request(url,{headers:{range}},bucket);eq(r.status,status);eq(await r.text(),body);eq(r.headers.get('content-range'),contentRange);}
r=await request(url,{headers:{range:'bytes=2-4','if-range':'"old"'}},bucket);eq(r.status,200);eq(await r.text(),'0123456789');
r=await request(url,{headers:{range:'bytes=2-4','if-range':'"test-etag"'}},bucket);eq(r.status,206);eq(options.range,{offset:2,length:3});
eq((await request(url,{}, {head:async()=>metadata,get:async()=>null})).status,404);
eq((await request(url,{headers:{'if-none-match':'"new"'}},{head:async()=>metadata,get:async()=>({...metadata,httpEtag:'"new"'})})).status,304);

const result={pass:true,assertions,media_contract:'/media/* -> R2 key',legacy_redirects:0,wp_query_redirects:0};
fs.mkdirSync('.recovery',{recursive:true});fs.writeFileSync('.recovery/media-tests.json',JSON.stringify(result,null,2)+'\n');console.log(result);
