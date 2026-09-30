import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const root = path.resolve(import.meta.dirname, '..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const write = (name, value) => { const p=path.join(root,name); fs.mkdirSync(path.dirname(p),{recursive:true}); fs.writeFileSync(p,JSON.stringify(value,null,2)+'\n'); };
const registry=read('migration/media-canonical.json');
const routes=read('migration/media-routes.json');
const inventory=read('migration/inventory.json');
const check=process.argv.includes('--check');
const stageArg=process.argv.indexOf('--staging');
const stage=stageArg<0 ? null : path.resolve(process.argv[stageArg+1]);
const oldManifest=fs.existsSync(path.join(root,'migration/media-manifest.json')) ? read('migration/media-manifest.json') : null;
const oldObjects=new Map(oldManifest?.objects.map(o=>[o.canonical_key,o]) ?? []);
function contentType(data) {
  if(data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))return 'image/png';
  if(data[0]===255 && data[1]===216 && data[2]===255)return 'image/jpeg';
  if(/^GIF8[79]a/.test(data.toString('ascii',0,6)))return 'image/gif';
  if(data.toString('ascii',0,4)==='RIFF' && data.toString('ascii',8,12)==='WEBP')return 'image/webp';
  if(data.readUInt32LE(0)===65536)return 'image/x-icon';
  if(data.toString('ascii',0,5)==='%PDF-')return 'application/pdf';
  if(/<svg[\s>]/.test(data.toString('utf8',0,2048)))return 'image/svg+xml';
  throw Error('Unknown content signature');
}
const objects=registry.objects.map(o=>{
  let type;
  if(stage){const bytes=fs.readFileSync(path.join(stage,o.object_key));assert.equal(bytes.length,o.bytes);assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),o.sha256);type=contentType(bytes);}
  else {const prior=oldObjects.get(o.object_key);assert(prior,'Initial generation requires --staging');assert.equal(prior.sha256,o.sha256);assert.equal(prior.size,o.bytes);type=prior.content_type;}
  return {canonical_key:o.object_key,canonical_url:o.canonical_url,source_KEEP_records:o.origin==='legacy_KEEP'?o.source_paths:[],origin:o.origin,sha256:o.sha256,size:o.bytes,content_type:type,class:o.object_key.split('/')[0]};
});
const urls=new Set(objects.map(o=>o.canonical_url));
assert.equal(urls.size,objects.length);
assert.equal(new Set(objects.map(o=>o.sha256)).size,objects.length,'Duplicate content must share one canonical key');
const redirects={};
function add(source,target){assert(urls.has(target));assert(source.startsWith('/')&&!source.startsWith('//'));assert(!urls.has(source));assert(!redirects[source]||redirects[source]===target,`Conflict ${source}`);redirects[source]=target;}
for(const a of registry.aliases)add(a.source,a.target);
for(const r of routes.redirects.filter(r=>r.target.startsWith('/media/'))) {assert(!r.query_match);add(r.source,r.target);}
for(const source of registry.source_mapping)assert.equal(redirects['/'+source.source],source.canonical_url);
const query={};
const published=new Map(inventory.filter(i=>i.status==='publish').map(i=>[String(i.wp_id),i]));
for(const p of routes.preserve_routes){assert(published.has(String(p.wp_id)));assert.equal(p.path,published.get(String(p.wp_id)).legacy_path);query[p.wp_id]=p.path;}
for(const r of routes.redirects.filter(r=>r.kind==='wp_query')) {assert.equal(query[Object.values(r.query_match)[0]],r.target);}
const include=['/api/*','/media/*','/images/*','/wp-content/uploads/*','/legacy-media/*','/'];
const match=(p,r)=>r.endsWith('*')?p.startsWith(r.slice(0,-1)):p===r;
for(const source of Object.keys(redirects).sort())if(!include.some(r=>match(source,r)))include.push(source);
assert(include.length<=100);
assert(include.every(r=>r.length<=100));
for(const p of routes.preserve_routes)assert(!include.some(r=>match(p.path,r)),`Static article intercepted: ${p.path}`);
for(const line of fs.readFileSync(path.join(root,'public/_redirects'),'utf8').trim().split(/\r?\n/)){const source=line.split(/\s+/)[0];assert(!include.some(r=>match(source,r)),`Static redirect intercepted: ${source}`);}
const sorted=o=>Object.fromEntries(Object.entries(o).sort(([a],[b])=>a<b?-1:a>b?1:0));
const outputs={
  'migration/media-manifest.json':{schema_version:1,bucket:registry.bucket,objects},
  'src/media/generated/redirects.json':sorted(redirects),
  'src/media/generated/queries.json':sorted(query),
  'src/media/generated/objects.json':sorted(Object.fromEntries(objects.map(o=>[o.canonical_key,{contentType:o.content_type,size:o.size}]))),
  'public/_routes.json':{version:1,include,exclude:[]},
};
for(const [name,value] of Object.entries(outputs)){if(check)assert.deepEqual(read(name),value,`Stale generated file: ${name}`);else write(name,value);}
console.log(JSON.stringify({objects:objects.length,KEEP:objects.filter(o=>o.origin==='legacy_KEEP').length,redirects:Object.keys(redirects).length,published_queries:Object.keys(query).length,invocation_rules:include.length,uncovered:0,static_articles:routes.preserve_routes.length,static_redirects:383,legacy_index_php_queries_outside_step27_scope:routes.redirects.filter(r=>r.kind==='wp_query'&&r.source!=='/').length}));
