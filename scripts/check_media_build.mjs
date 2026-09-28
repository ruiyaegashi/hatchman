// Fail closed until local canonical assets are hydrated. STEP 24 is not deployable.
import fs from 'node:fs';
import crypto from 'node:crypto';
const ledger = JSON.parse(fs.readFileSync(new URL('../migration/media-canonical.json', import.meta.url)));
const assets = JSON.parse(fs.readFileSync(new URL('../migration/asset-map.json', import.meta.url)));
const objects = new Map(ledger.objects.map(o => [o.canonical_url, o]));
const used = new Set(assets.filter(a => a.public_path).map(a => a.public_path));
used.add('/media/site/external-image-disabled.svg');
for (const url of used) {
  const object = objects.get(url);
  if (!object) throw new Error(`No canonical object: ${url}`);
  const path = new URL(`../public${url}`, import.meta.url);
  if (!fs.existsSync(path)) throw new Error(`Local media missing: ${url}. Run scripts/normalize_media.py as documented in docs/MEDIA_NORMALIZATION.md. R2 delivery is not implemented; do not deploy STEP 24.`);
  const data = fs.readFileSync(path);
  if (data.length !== object.bytes || crypto.createHash('sha256').update(data).digest('hex') !== object.sha256) {
    throw new Error(`Canonical media differs: ${url}`);
  }
}
console.log(`Canonical local build assets verified: ${used.size}`);
