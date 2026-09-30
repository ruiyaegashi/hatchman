"""STEP 24 local normalization. Never uploads, deploys, or deletes source assets."""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = {'images/favicon.ico', 'images/icon160.png', 'images/logo-1.png',
        'images/logo.png', 'images/logo_title.png'}
OVERRIDES = {'wallpaper_design.pdf': 'KEEP',
 'wp-content/uploads/cocoon-resources/blog-card-cache/7183f3692da296da4ede1d25e5a91233.jpg': 'DELETE',
 'wp-content/uploads/cocoon-resources/blog-card-cache/d52446b93c1132d08d036fd907fa12f9.jpg': 'DELETE'}
PLACEHOLDER = '/legacy-media/external-image-disabled.svg'

def require(ok, message):
    if not ok: raise ValueError(message)

def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def read_json(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def safe(root, relative):
    require(not Path(relative).is_absolute() and '..' not in Path(relative).parts and ':' not in relative,
            'Unsafe path: '+relative)
    p = root / relative
    require(p.resolve().is_relative_to(root.resolve()), 'Path escapes root: '+relative)
    return p

def snapshot(root):
    result = {}
    for p in root.rglob('*'):
        require(not p.is_symlink() and not p.is_junction(), 'Link in source: '+str(p))
        if p.is_file():
            s = p.stat()
            result[p.relative_to(root).as_posix()] = {'bytes':s.st_size, 'sha256':digest(p),
                'mtime_ns':s.st_mtime_ns, 'attributes':s.st_file_attributes}
    return result

def apply_canonical_references(root=ROOT):
    """Also used after the historic SQL migration, so regeneration retains fixed IDs."""
    ledger_path = root/'migration/media-canonical.json'
    if not ledger_path.exists(): return {'files':0, 'replacements':0}
    ledger = read_json(ledger_path)
    aliases = {r['source']:r['target'] for r in ledger['aliases']}
    assets_path = root/'migration/asset-map.json'
    assets = read_json(assets_path)
    sources = {r['source']:r['canonical_url'] for r in ledger['source_mapping']}
    for a in assets:
        if a.get('source') and a.get('public_path'):
            old = a.get('previous_public_path', a['public_path'])
            target = sources[a['source'].lstrip('/')]
            require(aliases.get(old, target) == target, 'Asset mapping conflict')
            a['previous_public_path'] = old
            a['public_path'] = target
    write_json(assets_path, assets)
    # Match complete URL tokens; no basename, case-fold, or substring substitution.
    rx = re.compile(r'(?:(?:https?:)?//(?:www\.)?hatchman\.org)?/(?:legacy-media|images|wp-content/uploads)/[^\s<>"\'?#)]+')
    stats = {'files':0, 'replacements':0}
    for p in sorted((root/'src').rglob('*')):
        if not p.is_file() or p.suffix not in {'.md','.mdx','.astro','.ts','.js','.css'}: continue
        text = p.read_bytes().decode('utf-8')
        def replace(m):
            url = m.group(0)
            key = re.sub(r'^(?:https?:)?//(?:www\.)?hatchman\.org', '', url)
            require(key in aliases, 'Unmapped current reference: '+url)
            stats['replacements'] += 1
            return aliases[key]
        changed = rx.sub(replace, text)
        if changed != text:
            p.write_bytes(changed.encode('utf-8')); stats['files'] += 1
    return stats

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--analysis-root', type=Path, required=True)
    parser.add_argument('--staging', type=Path, required=True)
    args=parser.parse_args()
    root=args.source_root.resolve(); stage=args.staging.resolve()
    require(not stage.is_relative_to(root) and not root.is_relative_to(stage), 'Staging overlaps source')
    inputs={n:digest(args.analysis_root/n) for n in ['public_html_manifest.csv','cleanup_report.md','legacy_redirects.json']}
    rows=list(csv.DictReader((args.analysis_root/'public_html_manifest.csv').open(encoding='utf-8-sig')))
    for row in rows: row['classification']=OVERRIDES.get(row['path'],row['classification'])
    require(collections.Counter(r['classification'] for r in rows)=={'KEEP':5000,'REDIRECT':11111,'DELETE':20922}, 'Classification mismatch')
    by_source={r['path']:r for r in rows}
    require(len(by_source)==len(rows), 'Duplicate source path')
    print('Reading and hashing all 16,111 source files...', flush=True)
    before=snapshot(root)
    expected={r['path'] for r in rows if r['classification']!='DELETE'}
    require(set(before)==expected, 'Source file set mismatch')
    for source,info in before.items():
        r=by_source[source]
        require(info['bytes']==int(r['size']) and info['sha256']==r['sha256'], 'Source differs: '+source)
    write_json(ROOT/'.recovery/step24-source-before.json', before)
    keep=sorted((r for r in rows if r['classification']=='KEEP'),key=lambda r:r['path'])
    old_path=ROOT/'migration/media-canonical.json'
    old=read_json(old_path) if old_path.exists() else None
    fixed={o['sha256']:o['object_key'] for o in old['objects']} if old else {}
    next_id=max([int(m.group(1)) for key in fixed.values() if (m:=re.match(r'legacy/legacy-(\d{6})\.',key))]+[0])+1
    objects={}; source_objects={}; used_keys={k:h for h,k in fixed.items()}
    for r in keep:
        h=r['sha256']; source=r['path']
        if h not in objects:
            if h in fixed: key=fixed[h]
            elif source in SITE: key='site/'+Path(source).name
            else:
                key=f'legacy/legacy-{next_id:06d}'+Path(source).suffix; next_id+=1
            require(key not in used_keys or used_keys[key]==h, 'Canonical key collision')
            used_keys[key]=h
            objects[h]={'object_key':key,'canonical_url':'/media/'+key,'sha256':h,
                'bytes':int(r['size']),'source_paths':[], 'origin':'legacy_KEEP'}
        objects[h]['source_paths'].append(source); source_objects[source]=objects[h]
    for r in rows:
        if r['classification']=='REDIRECT':
            target=r['target_source_path']
            require(target in source_objects and by_source[target]['classification']=='KEEP', 'Redirect target is not KEEP: '+r['path'])
            source_objects[r['path']]=source_objects[target]
    aliases={}
    def alias(source,target):
        require(source not in aliases or aliases[source]==target, 'Conflicting alias: '+source)
        require(source!=target, 'Self redirect')
        aliases[source]=target
    for source,obj in source_objects.items(): alias('/'+source,obj['canonical_url'])
    assets=read_json(ROOT/'migration/asset-map.json')
    current={}
    for a in assets:
        if not a.get('source') or not a.get('public_path'): continue
        source=a['source'].lstrip('/'); obj=source_objects[source]
        previous=a.get('previous_public_path',a['public_path'])
        require(digest(safe(ROOT/'public',previous.lstrip('/')))==obj['sha256'], 'Current content not identical to KEEP: '+previous)
        require(previous not in current or current[previous]==obj['canonical_url'], 'Current URL collision')
        current[previous]=obj['canonical_url']; alias(previous,obj['canonical_url'])
    raw=read_json(args.analysis_root/'legacy_redirects.json')
    routes=[]
    for original in raw['redirects']:
        r=dict(original)
        if r['kind'] not in {'old_slug','wp_query'}:
            target=r.get('target_source_path')
            canonical=source_objects[target]['canonical_url'] if target else aliases.get(r['target'])
            require(canonical is not None, 'Missing canonical route target: '+r['source'])
            r['previous_target']=r['target']; r['target']=canonical
            r['state']='canonical_mapping_only_not_deployed'
            r['target_availability']='local_canonical_staging_requires_R2'
            alias(r['source'],canonical)
        routes.append(r)
    placeholder=ROOT/'public'/PLACEHOLDER.lstrip('/')
    ph={'object_key':'site/external-image-disabled.svg','canonical_url':'/media/site/external-image-disabled.svg',
        'sha256':digest(placeholder),'bytes':placeholder.stat().st_size,'source_paths':[], 'origin':'current_site_placeholder'}
    require(ph['sha256'] not in objects, 'Unexpected placeholder duplicate')
    objects[ph['sha256']]=ph; alias(PLACEHOLDER,ph['canonical_url'])
    object_list=sorted(objects.values(),key=lambda o:o['object_key'])
    urls={o['canonical_url'] for o in object_list}
    require(all(t in urls for t in aliases.values()), 'Unresolved alias')
    require(not set(aliases)&urls, 'Redirect chain or canonical collision')
    conditions=set()
    for r in routes:
        condition=(r['source'],json.dumps(r.get('query_match',{}),sort_keys=True))
        require(condition not in conditions, 'Duplicate route condition'); conditions.add(condition)
    require(not set(aliases)&{r['path'] for r in raw['preserve_routes']}, 'Media alias collides with page')
    ledger={'schema_version':1,'bucket':'hatchman-media','state':'local_only_not_deployed',
        'source_main_commit':'6f1c205fbeeccb120fb8af9fe56a43c913498679',
        'allocation':'Initial Unicode codepoint source-path order; IDs persisted by SHA-256; never renumber existing objects.',
        'input_sha256':inputs,'objects':object_list,
        'source_mapping':[{'source':s,'classification':by_source[s]['classification'],
            'canonical_url':o['canonical_url']} for s,o in sorted(source_objects.items())],
        'aliases':[{'source':s,'target':t,'status_code':301} for s,t in sorted(aliases.items())]}
    if old: require(old==ledger, 'Existing fixed ledger would change; review required')
    write_json(old_path,ledger)
    write_json(ROOT/'migration/media-routes.json',{'schema_version':1,'state':'not_deployed',
        'preserve_routes':raw['preserve_routes'],'redirects':routes})
    print('Copying canonical staging; source assets remain untouched...', flush=True)
    for o in object_list:
        source=safe(root,o['source_paths'][0]) if o['source_paths'] else placeholder
        dest=safe(stage,o['object_key']); dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists(): require(digest(dest)==o['sha256'],'Staging differs: '+str(dest))
        else: shutil.copyfile(source,dest)
        require(digest(dest)==o['sha256'],'Staging hash mismatch')
    require({p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}=={o['object_key'] for o in object_list}, 'Unexpected staging file')
    changes=apply_canonical_references()
    # Hydrate only current assets for local build, without adding binary files to Git.
    for url in set(current.values())|{ph['canonical_url']}:
        key=url.removeprefix('/media/'); dest=safe(ROOT/'public/media',key)
        dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(safe(stage,key),dest)
    after=snapshot(root)
    require(before==after,'Source KEEP/REDIRECT changed')
    require(all(digest(args.analysis_root/n)==h for n,h in inputs.items()),'Analysis input changed')
    stats={'status':'PASS','keep_source_count':5000,'redirect_source_count':11111,
        'source_files_unchanged':len(after),'source_bytes':sum(x['bytes'] for x in after.values()),
        'canonical_keep_objects':len(object_list)-1,'canonical_keep_bytes':sum(o['bytes'] for o in object_list if o['origin']=='legacy_KEEP'),
        'site_keep_objects':sum(o['object_key'].startswith('site/') and o['origin']=='legacy_KEEP' for o in object_list),
        'legacy_objects':sum(o['object_key'].startswith('legacy/') for o in object_list),
        'site_placeholder_objects':1,'current_previous_objects':len(current),'current_unique_objects':len(set(current.values())),
        'current_duplicate_objects_consolidated':len(current)-len(set(current.values())),
        'canonical_aliases':len(aliases),'preserved_route_conditions':len(routes),
        'mapping_conflicts':0,'missing_targets':0,'chains':0,'loops':0,
        'source_differences':0,'reference_changes_this_run':changes,
        'runtime':'Local only. No R2, Functions, push, preview or production change. REDIRECT source files retained.'}
    write_json(ROOT/'.recovery/media-normalization.json',stats)
    print(json.dumps(stats,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__': main()
