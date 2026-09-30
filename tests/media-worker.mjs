import { Miniflare, convertV4MiniflareOptions } from 'miniflare';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const mf=new Miniflare(convertV4MiniflareOptions({cf:false,modules:true,scriptPath:'.wrangler/step28-build/index.js',compatibilityDate:'2026-09-21',r2Buckets:['MEDIA'],serviceBindings:{ASSETS:()=>new Response('static',{headers:{'x-test-static':'1'}})}}));
let assertions=0;
const eq=(a,b)=>{assert.deepEqual(a,b);assertions++;};
try {
  // Synthetic ten-byte fixture in ephemeral local simulation only; no source assets or remote uploads.
  const bucket=await mf.getR2Bucket('MEDIA');
  const key='legacy/legacy-000001.png';
  await bucket.put(key,'0123456789',{httpMetadata:{contentType:'image/png'}});
  const fetch=(path,init={})=>mf.dispatchFetch('https://local.test'+path,init);
  let r=await fetch('/media/'+key);const etag=r.headers.get('etag');eq(r.status,200);eq(await r.text(),'0123456789');eq(r.headers.get('content-type'),'image/png');
  r=await fetch('/media/'+key,{method:'HEAD'});eq(r.status,200);eq(await r.text(),'');eq(r.headers.get('content-length'),'10');
  r=await fetch('/media/'+key,{headers:{'if-none-match':etag}});eq(r.status,304);
  r=await fetch('/media/'+key,{headers:{'if-none-match':'"different"'}});eq(r.status,200);eq(await r.text(),'0123456789');
  r=await fetch('/media/'+key,{headers:{'if-none-match':'*'}});eq(r.status,304);
  r=await fetch('/media/'+key,{headers:{'if-match':'"different"'}});eq(r.status,412);
  r=await fetch('/media/'+key,{headers:{'if-modified-since':'Wed, 30 Sep 2037 00:00:00 GMT'}});eq(r.status,304);
  for(const [range,expected,body,contentRange] of [['bytes=2-4',206,'234','bytes 2-4/10'],['bytes=-2',206,'89','bytes 8-9/10'],['bytes=10-',416,'','bytes */10']]){
    r=await fetch('/media/'+key,{headers:{range}});eq(r.status,expected);eq(await r.text(),body);eq(r.headers.get('content-range'),contentRange);
  }
  r=await fetch('/media/'+key,{headers:{range:'bytes=2-4','if-range':'"old"'}});eq(r.status,200);eq(await r.text(),'0123456789');
  r=await fetch('/media/'+key,{method:'PUT',body:'not allowed'});eq(r.status,405);eq(await (await bucket.get(key)).text(),'0123456789');
  eq((await fetch('/media/legacy/missing.png')).status,404);
  r=await fetch('/images/0-04.png?drop=yes',{redirect:'manual'});eq(r.status,301);eq(r.headers.get('location'),'/media/'+key);
  r=await fetch('/?p=8260',{redirect:'manual'});eq(r.status,301);eq(r.headers.get('location'),'/hamamatsushi-trip-amusementpark-palpal/');
  eq((await fetch('/')).headers.get('x-test-static'),'1');
  eq((await fetch('/images/missing.png')).headers.get('x-test-static'),'1');
  eq((await fetch('/api/amazon?asins=invalid')).status,400);
  const result={pass:true,assertions,runtime:'local workerd / Miniflare',remote_uploads:0,source_assets_uploaded:0,fixture:'ephemeral synthetic 10 bytes'};
  fs.writeFileSync('.recovery/media-worker-tests.json',JSON.stringify(result,null,2)+'\n');console.log(result);
} finally {await mf.dispose();}
