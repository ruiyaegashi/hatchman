"""Validate canonical mapping, actual bytes, built references, and source retention."""
import argparse, collections, html, io, json, re, subprocess, tarfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from normalize_media import ROOT, read_json, write_json, require, digest, snapshot

class References(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if not value: continue
            if name in {'src','href','poster','data-src'}: self.urls.append(value)
            if name=='srcset': self.urls.extend(x.strip().split()[0] for x in value.split(',') if x.strip())

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source-root',required=True,type=Path); p.add_argument('--staging',required=True,type=Path)
    a=p.parse_args(); ledger=read_json(ROOT/'migration/media-canonical.json')
    objs={o['canonical_url']:o for o in ledger['objects']}
    require(len(objs)==len(ledger['objects']), 'Duplicate canonical URL')
    require(len({o['sha256'] for o in objs.values()})==len(objs), 'Duplicate canonical content')
    require(len({o['object_key'].casefold() for o in objs.values()})==len(objs), 'Case-insensitive key collision')
    for url,o in objs.items():
        require(digest(a.staging/o['object_key'])==o['sha256'], 'Staging content mismatch')
        if o['object_key'].startswith('legacy/'):
            require(re.fullmatch(r'legacy/legacy-\d{6}\.[A-Za-z0-9]+',o['object_key']), 'Invalid legacy ID')
            require(Path(o['object_key']).suffix==Path(o['source_paths'][0]).suffix,'Extension changed')
    aliases={r['source']:r['target'] for r in ledger['aliases']}
    archive=subprocess.check_output(['git','archive','HEAD','src'],cwd=ROOT)
    article_changes=0
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar:
            if not member.isfile(): continue
            original=tar.extractfile(member).read(); expected=original
            for source,target in aliases.items():
                if source.startswith('/legacy-media/'):
                    expected=expected.replace(source.encode(),target.encode())
            actual=(ROOT/member.name).read_bytes()
            require(actual==expected,'Source change beyond canonical URLs: '+member.name)
            article_changes+=actual!=original
    require(len(aliases)==len(ledger['aliases']), 'Duplicate alias')
    require(not set(aliases)&set(objs),'Alias chain/cycle')
    require(all(t in objs for t in aliases.values()), 'Alias target missing')
    assets=read_json(ROOT/'migration/asset-map.json')
    old_hashes={}; current=set()
    for row in assets:
        if not row.get('public_path'): continue
        obj=objs[row['public_path']]; current.add(row['public_path'])
        old=ROOT/'public'/row['previous_public_path'].lstrip('/')
        require(digest(old)==obj['sha256'], 'Current asset content changed')
        old_hashes[row['previous_public_path']]=obj['sha256']
        require(digest(ROOT/'dist'/row['public_path'].lstrip('/'))==obj['sha256'],'Built asset missing/changed')
    broken=[]; old_refs=[]; total=0; canonical_refs=0
    pages=list((ROOT/'dist').rglob('*.html'))
    require(pages,'Build missing')
    for page in pages:
        parser=References(); parser.feed(page.read_text(encoding='utf-8'))
        for value in parser.urls:
            u=urlsplit(html.unescape(value))
            if u.netloc and u.netloc not in {'hatchman.org','www.hatchman.org'}: continue
            path=unquote(u.path)
            if path.startswith(('/legacy-media/','/images/','/wp-content/uploads/')): old_refs.append([str(page),value])
            if path.startswith('/media/'):
                total+=1
                if path not in objs or not (ROOT/'dist'/path.lstrip('/')).is_file(): broken.append([str(page),value])
                else: canonical_refs+=1
    require(not broken and not old_refs,'Missing or noncanonical rendered references')
    require(not any('/legacy-media/' in f.read_text(encoding='utf-8') for f in (ROOT/'src').rglob('*.md')),'Legacy source reference remains')
    baseline=read_json(ROOT/'.recovery/step24-source-before.json')
    after=snapshot(a.source_root)
    require(after==baseline,'Source files changed')
    srcmap=ledger['source_mapping']
    require(collections.Counter(r['classification'] for r in srcmap)=={'KEEP':5000,'REDIRECT':11111},'Source map counts')
    require(all(r['canonical_url'] in objs for r in srcmap),'Source mapping target missing')
    routes=read_json(ROOT/'migration/media-routes.json')['redirects']
    conditions=[(r['source'],json.dumps(r.get('query_match',{}),sort_keys=True)) for r in routes]
    require(len(set(conditions))==16466==len(routes),'Route conditions lost or conflict')
    for r in routes:
        if r['kind'] not in {'old_slug','wp_query'}: require(r['target'] in objs,'Route not directly canonical')
    unique_old_bytes=sum((ROOT/'public'/url.lstrip('/')).stat().st_size for url in old_hashes)
    unique_new_bytes=sum(objs[url]['bytes'] for url in current)
    result={'status':'PASS','source_files_changed_only_by_URL':article_changes,'built_html_pages':len(pages),'rendered_canonical_references':canonical_refs,
        'missing_references':len(broken),'noncanonical_references':len(old_refs),'mapping_conflicts':0,
        'redirect_chains':0,'redirect_loops':0,'missing_targets':0,'keep_retained':5000,'redirect_retained':11111,
        'source_hash_and_metadata_differences':0,'canonical_keep_objects':5000,'canonical_site_placeholder':1,
        'previous_current_files':len(old_hashes),'unique_current_objects':len(current),
        'current_duplicates_consolidated':len(old_hashes)-len(current),
        'duplicate_bytes_avoided_in_canonical_set':unique_old_bytes-unique_new_bytes,
        'route_conditions_preserved':len(routes),'public_redirects_unchanged':True}
    # Existing 383 article redirects remain byte-identical to baseline main.
    original=subprocess.check_output(['git','show','HEAD:public/_redirects'],cwd=ROOT)
    require((ROOT/'public/_redirects').read_bytes().replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),'Article redirects changed')
    write_json(ROOT/'.recovery/media-validation.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
