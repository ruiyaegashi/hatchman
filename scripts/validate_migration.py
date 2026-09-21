from __future__ import annotations
import collections, hashlib, html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import migrate_legacy as migration

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.images=[]; self.danger=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs); t=tag.lower()
        if t in {'iframe','object','embed','form'} or (t=='script' and a.get('type')!='module'): self.danger.append(t)
        if t=='a' and a.get('href'): self.links.append(a['href'])
        if t in {'img','source'} and a.get('src'): self.images.append(a['src'])
        for k,v in attrs:
            if k.lower().startswith('on') or (v and re.match(r'\s*(javascript|vbscript|data):',v,re.I)): self.danger.append(k)

def output_for(path):
    clean=unquote(path.split('?',1)[0].split('#',1)[0]).strip('/')
    if not clean: return ROOT/'dist/index.html'
    direct=ROOT/'dist'/clean
    if direct.is_file(): return direct
    return direct/'index.html'

def main():
    inventory=json.loads((ROOT/'migration/inventory.json').read_text(encoding='utf-8'))
    assets=json.loads((ROOT/'migration/asset-map.json').read_text(encoding='utf-8'))
    redirects=json.loads((ROOT/'migration/old-slugs.json').read_text(encoding='utf-8'))
    markdown=list((ROOT/'src/content/legacy').glob('*.md'))
    public=[x for x in inventory if x['status']=='publish']; drafts=[x for x in inventory if x['status']=='draft']
    tables=migration.read_tables(); source={int(p['ID']):p for p in tables['wp_posts'] if p['post_type'] in {'post','page'} and p['post_status'] in {'publish','draft'}}
    hash_mismatch=[]
    for item in inventory:
        actual=hashlib.sha256((source[item['wp_id']]['post_content'] or '').encode()).hexdigest()
        if actual!=item['source_content_sha256']: hash_mismatch.append(item['wp_id'])
    paths=[x['legacy_path'] for x in public]; duplicate_paths=[p for p,n in collections.Counter(paths).items() if n>1]
    missing_pages=[x['legacy_path'] for x in public if not output_for(x['legacy_path']).exists()]
    draft_pages=[x['legacy_path'] for x in drafts if x['legacy_path'] not in {'','/','//'} and output_for(x['legacy_path']).exists()]
    redirect_lines=[x for x in (ROOT/'dist/_redirects').read_text(encoding='utf-8').splitlines() if x.strip()]
    redirect_sources=[x['from'] for x in redirects]; redirect_conflicts=[p for p,n in collections.Counter(redirect_sources).items() if n>1]
    redirect_missing_targets=[x for x in redirects if not output_for(x['to']).exists()]
    bad_assets=[]
    for row in assets:
        if row['public_path'] and not (ROOT/'dist'/row['public_path'].lstrip('/')).is_file(): bad_assets.append(row)
    parsers={}; all_links=[]; all_images=[]; danger=[]; unresolved_shortcodes=[]; old_media=[]
    for item in public:
        file=output_for(item['legacy_path']); text=file.read_text(encoding='utf-8',errors='replace'); parser=Links(); parser.feed(text); parsers[item['wp_id']]=parser
        all_links.extend((item['wp_id'],u) for u in parser.links); all_images.extend((item['wp_id'],u) for u in parser.images)
        danger.extend((item['wp_id'],x) for x in parser.danger)
        visible=re.sub(r'<aside class="legacy-disabled legacy-shortcode">.*?</aside>','',html.unescape(text),flags=re.I|re.S)
        if re.search(r'\[(?:amazonjs|browser-shot)\b',visible,re.I): unresolved_shortcodes.append(item['wp_id'])
        if re.search(r'(?:https?:)?//(?:www\.)?hatchman\.org/(?:images|wp-content/uploads)/',text,re.I): old_media.append(item['wp_id'])
    built_routes={x['legacy_path'] for x in public}|{'/','/archive/','/categories/'}
    built_routes|={f"/categories/{c}/" for c in {c for x in public for c in x['categories']}}
    broken=[]
    ignored_prefixes=('/wp-content/','/feed/','/tag/','/author/','/page/')
    for wp,url in all_links:
        p=urlsplit(html.unescape(url))
        if p.scheme in {'mailto','tel'} or (p.netloc and p.netloc.lower() not in {'hatchman.org','www.hatchman.org'}): continue
        path=unquote(p.path or '/')
        if path.startswith('#') or path in built_routes or output_for(path).exists(): continue
        if any(path.startswith(x) for x in ignored_prefixes): continue
        broken.append({'wp_id':wp,'url':url})
    missing_rendered_images=[]
    for wp,url in all_images:
        p=urlsplit(html.unescape(url))
        if p.netloc: continue
        if not (ROOT/'dist'/unquote(p.path).lstrip('/')).exists(): missing_rendered_images.append({'wp_id':wp,'url':url})
    security_patterns={'wordpress_hash':r'\$(?:P|H)\$[./0-9A-Za-z]{20,}','session_token':r'session_tokens','db_secret':r'DB_(?:PASSWORD|USER|HOST)|AUTH_KEY|SECURE_AUTH_KEY','php':r'<\?php'}
    security={name:0 for name in security_patterns}
    for file in markdown:
        text=file.read_text(encoding='utf-8',errors='replace')
        for name,rx in security_patterns.items(): security[name]+=len(re.findall(rx,text,re.I))
    external_assets=[x for x in assets if x['status']=='external-disabled']; statuses=collections.Counter(x['status'] for x in assets)
    result={
      'counts':{'markdown':len(markdown),'inventory':len(inventory),'public':len(public),'drafts':len(drafts),'generated_legacy_pages':len(public)-len(missing_pages),'total_html_pages':len(list((ROOT/'dist').rglob('index.html')))},
      'source_integrity':{'hash_mismatches':hash_mismatch},
      'urls':{'unique_public_paths':len(set(paths)),'duplicate_paths':duplicate_paths,'missing_public_pages':missing_pages,'draft_pages_generated':draft_pages,'redirect_records':len(redirects),'redirect_lines':len(redirect_lines),'redirect_source_conflicts':redirect_conflicts,'redirect_targets_missing':redirect_missing_targets},
      'assets':{'references':len(assets),'statuses':dict(statuses),'missing_copied_or_built':bad_assets,'rendered_images_missing':missing_rendered_images,'external_disabled':len(external_assets)},
      'rendered_security':{'dangerous_elements_or_attributes':danger,'unresolved_shortcodes':sorted(set(unresolved_shortcodes)),'old_hatchman_media_dependencies':sorted(set(old_media)),'secret_markers':security},
      'links':{'internal_broken_count':len(broken),'internal_broken':broken},
    }
    fatal=[]
    if len(markdown)!=407 or len(public)!=404 or len(drafts)!=3: fatal.append('content counts')
    if hash_mismatch or duplicate_paths or missing_pages or draft_pages: fatal.append('content integrity/routes')
    if len(redirects)!=383 or len(redirect_lines)!=383 or redirect_conflicts or redirect_missing_targets: fatal.append('redirects')
    if bad_assets or missing_rendered_images or statuses.get('missing',0): fatal.append('assets')
    if danger or unresolved_shortcodes or old_media or any(security.values()): fatal.append('security')
    result['fatal']=fatal
    (ROOT/'reports/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({**result,'links':{'internal_broken_count':len(broken)}},ensure_ascii=False,indent=2))
    raise SystemExit(1 if fatal else 0)
if __name__=='__main__': main()
