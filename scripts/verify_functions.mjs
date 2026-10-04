import fs from 'node:fs';
import assert from 'node:assert/strict';
import { gzipSync } from 'node:zlib';
import crypto from 'node:crypto';

const bundle=fs.readFileSync('.wrangler/step28-build/index.js');
const managed=JSON.parse(fs.readFileSync('public/_routes.json'));
const deployed=JSON.parse(fs.readFileSync('dist/_routes.json'));
assert.deepEqual(deployed,managed,'Build must ship the source-managed invocation routes');
assert.deepEqual(managed.include,['/api/*','/media/*']);
assert(bundle.length<64*1024*1024,'Functions bundle exceeds limit');
assert(!fs.existsSync('dist/media')&&!fs.existsSync('dist/legacy-media'));

const result={
  pass:true,
  uncompressed_bytes:bundle.length,
  gzip_bytes:gzipSync(bundle).length,
  limit_bytes:64*1024*1024,
  sha256:crypto.createHash('sha256').update(bundle).digest('hex'),
  source_managed_routes:managed,
  static_media_binaries:0,
  legacy_redirect_contract:false
};
fs.mkdirSync('.recovery',{recursive:true});fs.writeFileSync('.recovery/functions-verification.json',JSON.stringify(result,null,2)+'\n');console.log(result);
