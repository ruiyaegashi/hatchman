from __future__ import annotations

import argparse, collections, gzip, hashlib, html, json, os, re, shutil, sys, zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
def resolve_backup_root(value=None, *, require_web=False):
    """Resolve an explicit local source; never guess a machine-specific path."""
    value = value or os.environ.get('HATCHMAN_BACKUP_ROOT')
    if not value:
        raise SystemExit('Set --backup-root or HATCHMAN_BACKUP_ROOT (see docs/RECOVERY.md).')
    root = Path(value).expanduser().resolve()
    if root == ROOT or ROOT in root.parents or root in ROOT.parents:
        raise SystemExit('Backup root must be outside and separate from the repository.')
    if not (root / 'mysql55_20260921.zip').is_file():
        raise SystemExit('Backup root must contain mysql55_20260921.zip.')
    if require_web and not (root / 'public_html').is_dir():
        raise SystemExit('Migration requires the extracted public_html directory.')
    return root

FIELDS = {
 "wp_posts": ["ID","post_author","post_date","post_date_gmt","post_content","post_title","post_excerpt","post_status","comment_status","ping_status","post_password","post_name","to_ping","pinged","post_modified","post_modified_gmt","post_content_filtered","post_parent","guid","menu_order","post_type","post_mime_type","comment_count"],
 "wp_postmeta": ["meta_id","post_id","meta_key","meta_value"],
 "wp_terms": ["term_id","name","slug","term_group","term_order"],
 "wp_term_taxonomy": ["term_taxonomy_id","term_id","taxonomy","description","parent","count"],
 "wp_term_relationships": ["object_id","term_taxonomy_id","term_order"],
 "wp_options": ["option_id","option_name","option_value","autoload"],
}
SAFE_IMAGE_EXT = {'.jpg','.jpeg','.png','.gif','.webp','.ico'}
SAFE_MEDIA_EXT = SAFE_IMAGE_EXT | {'.pdf'}
IMAGE_SIG = {
 '.jpg': lambda b: b.startswith(b'\xff\xd8\xff'), '.jpeg': lambda b: b.startswith(b'\xff\xd8\xff'),
 '.png': lambda b: b.startswith(b'\x89PNG\r\n\x1a\n'), '.gif': lambda b: b.startswith((b'GIF87a',b'GIF89a')),
 '.webp': lambda b: b.startswith(b'RIFF') and b[8:12] == b'WEBP',
 '.ico': lambda b: b.startswith(b'\x00\x00\x01\x00'),
 '.pdf': lambda b: b.startswith(b'%PDF-'),
}

def mysql_unescape(s):
    repl={'0':'\0','n':'\n','r':'\r','t':'\t','b':'\b','Z':'\x1a','\\':'\\',"'":"'",'"':'"'}
    return re.sub(r"\\(.)", lambda m: repl.get(m.group(1),m.group(1)), s)
def token(v):
    v=v.strip()
    if v=='NULL': return None
    if v.startswith('0x'): return bytes.fromhex(v[2:]).decode('utf-8','replace')
    if len(v)>1 and v[0]=="'" and v[-1]=="'": return mysql_unescape(v[1:-1])
    try: return int(v)
    except ValueError: return v
def tuples(payload):
    row=[]; buf=[]; depth=0; quoted=False; escape=False
    for c in payload:
        if quoted:
            buf.append(c)
            if escape: escape=False
            elif c=='\\': escape=True
            elif c=="'": quoted=False
        elif c=="'": quoted=True; buf.append(c)
        elif c=='(' and depth==0: depth=1; row=[]; buf=[]
        elif c==',' and depth==1: row.append(token(''.join(buf))); buf=[]
        elif c==')' and depth==1: row.append(token(''.join(buf))); yield row; depth=0
        elif depth==1: buf.append(c)
def read_tables(backup_root):
    out={k:[] for k in FIELDS}; rx=re.compile(r"^INSERT INTO `([^`]+)` VALUES (.*);$")
    with zipfile.ZipFile(backup_root / 'mysql55_20260921.zip') as z:
        inner=next(n for n in z.namelist() if n.endswith('.sql.gz'))
        with z.open(inner) as compressed, gzip.GzipFile(fileobj=compressed) as raw:
            for binary in raw:
                if not binary.startswith(b'INSERT INTO `'): continue
                line=binary.decode('utf-8','replace').rstrip('\r\n'); m=rx.match(line)
                if not m or m.group(1) not in FIELDS: continue
                name,payload=m.groups(); fields=FIELDS[name]
                for vals in tuples(payload):
                    if len(vals)!=len(fields): raise ValueError(f'{name}: {len(vals)} values')
                    out[name].append(dict(zip(fields,vals)))
    return out
def canonical(post, pattern):
    if post['post_type']=='page': return '/' + str(post['post_name']).strip('/') + '/'
    p=pattern
    for k,v in {'%postname%':post['post_name'],'%year%':str(post['post_date'])[:4],'%monthnum%':str(post['post_date'])[5:7],'%day%':str(post['post_date'])[8:10],'%post_id%':str(post['ID'])}.items(): p=p.replace(k,str(v))
    return '/' + p.strip('/') + '/'
def yaml_string(value): return json.dumps(str(value),ensure_ascii=False)
def frontmatter(data):
    lines=['---']
    for k,v in data.items():
        if isinstance(v,list): lines.append(f'{k}: '+json.dumps(v,ensure_ascii=False))
        elif isinstance(v,bool): lines.append(f'{k}: '+str(v).lower())
        elif isinstance(v,int): lines.append(f'{k}: {v}')
        else: lines.append(f'{k}: {yaml_string(v)}')
    return '\n'.join(lines+['---',''])

def image_refs(text):
    found=[]
    for m in re.finditer(r'<(?:img|source)\b[^>]*?(?:src|srcset)=["\']([^"\']+)', text, re.I):
        for part in m.group(1).split(','):
            url=html.unescape(part.strip().split()[0]) if part.strip() else ''
            if url: found.append(url)
    return found
def safe_name(slug, wp_id):
    cleaned=re.sub(r'[^A-Za-z0-9._-]+','-',str(slug)).strip('-')[:100] or 'untitled'
    return f'wp-{int(wp_id):06d}-{cleaned}.md'

class StaticSanitizer(HTMLParser):
    blocked={'script','iframe','object','embed','form','input','button','textarea','select','option','meta','link','base'}
    void={'br','hr','img','source','area','col','wbr'}
    def __init__(self, rewrite_url): super().__init__(convert_charrefs=False); self.out=[]; self.stack=[]; self.rewrite_url=rewrite_url; self.stats=collections.Counter()
    def handle_starttag(self,tag,attrs):
        t=tag.lower()
        if t in self.blocked:
            self.stack.append(t); self.stats[t]+=1
            src=next((v for k,v in attrs if k.lower() in {'src','href'}),None)
            label=f'旧{t}埋め込み（安全のため停止）'
            if src: label+=f': {src}'
            self.out.append('<aside class="legacy-disabled">'+html.escape(label)+'</aside>')
            return
        if self.stack: return
        safe=[]
        for k,v in attrs:
            kl=k.lower()
            if kl.startswith('on') or kl in {'srcdoc'}: self.stats['removed_attribute']+=1; continue
            if kl=='style':
                if re.search(r'url\s*\(|expression\s*\(|behavior\s*:|@import|-moz-binding',v or '',re.I): self.stats['removed_style']+=1; continue
            if kl in {'href','src','poster'} and v:
                if re.match(r'\s*(?:javascript|vbscript|data):',v,re.I): self.stats['removed_url']+=1; continue
                v=self.rewrite_url(v, t, kl)
            if kl=='srcset' and v:
                pieces=[]
                for item in v.split(','):
                    bits=item.strip().split()
                    if bits: pieces.append(' '.join([self.rewrite_url(bits[0],t,kl)]+bits[1:]))
                v=', '.join(pieces)
            safe.append((k,v))
        rendered=''.join(' '+k+('' if v is None else '="'+html.escape(v,quote=True)+'"') for k,v in safe)
        self.out.append('<'+tag+rendered+'>')
    def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        t=tag.lower()
        if self.stack:
            if t==self.stack[-1]: self.stack.pop()
            return
        if t not in self.blocked and t not in self.void: self.out.append('</'+tag+'>')
    def handle_data(self,data):
        if not self.stack: self.out.append(data)
        elif self.stack[-1]=='script' and data.strip(): self.out.append('<details class="legacy-source"><summary>停止した旧スクリプトの記録</summary><pre><code>'+html.escape(data)+'</code></pre></details>')
    def handle_entityref(self,n):
        if not self.stack: self.out.append('&'+n+';')
    def handle_charref(self,n):
        if not self.stack: self.out.append('&#'+n+';')
    def handle_comment(self,d):
        if not self.stack and d.strip().lower()!='more': self.out.append('<!--'+d+'-->')

def shortcode_placeholders(text, stats):
    def repl(name, value):
        rx=re.compile(r'\['+re.escape(name)+r'\b[^\]]*\](?:.*?\[/'+re.escape(name)+r'\])?',re.I|re.S)
        def one(m): stats[name]+=1; return '<aside class="legacy-disabled legacy-shortcode"><strong>旧'+name+'（停止）</strong><details><summary>原文</summary><code>'+html.escape(m.group(0))+'</code></details></aside>'
        return rx.sub(one,value)
    return repl('browser-shot',repl('amazonjs',text))

def main():
    parser = argparse.ArgumentParser(description='Regenerate migrated content in a disposable checkout; reads the original backup only.')
    parser.add_argument('--backup-root', help='Directory containing mysql55_20260921.zip and public_html; overrides HATCHMAN_BACKUP_ROOT')
    args = parser.parse_args()
    backup_root = resolve_backup_root(args.backup_root, require_web=True)
    web = backup_root / 'public_html'
    tables=read_tables(backup_root); options={r['option_name']:r['option_value'] for r in tables['wp_options']}; pattern=options.get('permalink_structure') or '/%postname%/'
    targets=[p for p in tables['wp_posts'] if p['post_type'] in {'post','page'} and p['post_status'] in {'publish','draft'}]
    terms={r['term_id']:r for r in tables['wp_terms']}; tax={r['term_taxonomy_id']:r for r in tables['wp_term_taxonomy']}; assigned=collections.defaultdict(list)
    for r in tables['wp_term_relationships']:
        x=tax.get(r['term_taxonomy_id']); term=terms.get(x['term_id']) if x else None
        if x and term: assigned[r['object_id']].append((x['taxonomy'],term['name']))
    meta=collections.defaultdict(list)
    for r in tables['wp_postmeta']:
        if r['meta_key']=='_wp_old_slug': meta[r['post_id']].append(r['meta_value'])
    files={}; folded=collections.defaultdict(list)
    for f in web.rglob('*'):
        if f.is_file():
            rel='/'+f.relative_to(web).as_posix(); files[rel]=f; folded[rel.casefold()].append(rel)
    out=ROOT/'src/content/legacy'; media=ROOT/'public/legacy-media'; migration=ROOT/'migration'; reports=ROOT/'reports'
    for d in (out,media,migration,reports):
        if d.exists() and d in (out,media): shutil.rmtree(d)
        d.mkdir(parents=True,exist_ok=True)
    (media/'external-image-disabled.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120" viewBox="0 0 640 120"><rect width="640" height="120" fill="#f1efe9"/><text x="320" y="64" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#625d55">旧外部画像（自動読み込み停止）</text></svg>',encoding='utf-8')
    asset_map=[]; copied={}; transform_stats=collections.Counter(); redirect_rows=[]; inventory=[]
    canonical_by_id={int(p['ID']):canonical(p,pattern) for p in targets if p['post_status']=='publish'}
    old_path_to_current={f'/post-{wp}/':path for wp,path in canonical_by_id.items()}
    def resolve_asset(url,wp_id,kind='inline-image'):
        parsed=urlsplit(html.unescape(url)); host=parsed.netloc.lower()
        if host and host not in {'hatchman.org','www.hatchman.org'}:
            asset_map.append({'wp_id':wp_id,'kind':kind,'original':url,'status':'external-disabled','source':None,'public_path':None})
            return '/legacy-media/external-image-disabled.svg'
        path=unquote(parsed.path); candidates=[path]
        if path.startswith('/wp-content/uploads/'): candidates.append('/images/'+path.rsplit('/',1)[-1])
        match=next((c for c in candidates if c in files),None); status='exact'
        if not match:
            match=next((folded[c.casefold()][0] for c in candidates if folded.get(c.casefold())),None); status='case-insensitive'
        if not match:
            asset_map.append({'wp_id':wp_id,'kind':kind,'original':url,'status':'missing','source':None,'public_path':None}); return url
        source=files[match]; ext=source.suffix.lower(); header=source.read_bytes()[:16]
        detected=next((candidate for candidate,check in IMAGE_SIG.items() if check(header)),None)
        if ext not in SAFE_MEDIA_EXT or not detected:
            asset_map.append({'wp_id':wp_id,'kind':kind,'original':url,'status':'unsafe-type-disabled','source':match,'public_path':None}); return url
        output_ext=ext
        if not IMAGE_SIG[ext](header):
            status='signature-corrected'; output_ext='.jpg' if detected=='.jpeg' else detected
        key=match.casefold()
        if key not in copied:
            suffix=Path(match).stem+output_ext; digest=hashlib.sha256(match.encode()).hexdigest()[:12]
            public=f'/legacy-media/{digest}-{suffix}'
            dest=ROOT/'public'/public.lstrip('/'); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,dest); copied[key]=public
        public=copied[key]
        asset_map.append({'wp_id':wp_id,'kind':kind,'original':url,'status':status,'source':match,'public_path':public})
        return public
    for post in sorted(targets,key=lambda p:(str(p['post_date']),int(p['ID']))):
        wp=int(post['ID']); body=post['post_content'] or ''; per_stats=collections.Counter(); body=shortcode_placeholders(body,per_stats); transform_stats.update(per_stats)
        def rewrite(url,tag,attr):
            parsed=urlsplit(html.unescape(url)); host=parsed.netloc.lower()
            if tag in {'img','source'} and attr in {'src','srcset'}:
                mapped=resolve_asset(url,wp)
                if mapped==url and host and host not in {'hatchman.org','www.hatchman.org'}:
                    return mapped
                return mapped
            local_path=unquote(parsed.path)
            if tag=='a' and attr=='href' and Path(local_path).suffix.lower() in SAFE_MEDIA_EXT and (not host or host in {'hatchman.org','www.hatchman.org'}):
                return resolve_asset(url,wp,'linked-media')
            if not host or host in {'hatchman.org','www.hatchman.org'}:
                if local_path in old_path_to_current: return old_path_to_current[local_path]
            if host in {'hatchman.org','www.hatchman.org'}: return (parsed.path or '/') + (('?'+parsed.query) if parsed.query else '')
            return url
        sanitizer=StaticSanitizer(rewrite); sanitizer.feed(body); sanitizer.close(); transform_stats.update(sanitizer.stats); rendered=''.join(sanitizer.out)
        legacy=canonical(post,pattern); former=[str(x) for x in meta[wp]]
        data={'title':post['post_title'],'wp_id':wp,'content_type':post['post_type'],'status':post['post_status'],'published_at':post['post_date'],'modified_at':post['post_modified'],'legacy_url':'https://hatchman.org'+legacy,'legacy_path':legacy,'legacy_slug':post['post_name'],'former_slugs':former,'parent_wp_id':int(post['post_parent'] or 0),'categories':[n for t,n in assigned[wp] if t=='category'],'tags':[n for t,n in assigned[wp] if t=='post_tag'],'source_content_sha256':hashlib.sha256((post['post_content'] or '').encode()).hexdigest(),'source_content_chars':len(post['post_content'] or ''),'migration_review':'review' if per_stats or sanitizer.stats else 'passed'}
        filename=safe_name(post['post_name'],wp); (out/filename).write_text(frontmatter(data)+rendered+'\n',encoding='utf-8')
        inventory.append({**data,'file':'src/content/legacy/'+filename,'transforms':dict(per_stats+sanitizer.stats)})
        if post['post_status']=='publish':
            for old in former: redirect_rows.append({'wp_id':wp,'from':'/'+old.strip('/')+'/','to':legacy})
    (migration/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
    (migration/'asset-map.json').write_text(json.dumps(asset_map,ensure_ascii=False,indent=2),encoding='utf-8')
    (migration/'old-slugs.json').write_text(json.dumps(redirect_rows,ensure_ascii=False,indent=2),encoding='utf-8')
    redirects='\n'.join(f"{r['from']} {r['to']} 301" for r in redirect_rows)+'\n'
    (ROOT/'public/_redirects').write_text(redirects,encoding='utf-8')
    summary={'contents':len(inventory),'public':sum(x['status']=='publish' for x in inventory),'drafts':sum(x['status']=='draft' for x in inventory),'redirects':len(redirect_rows),'inline_image_references':sum(x['kind']=='inline-image' for x in asset_map),'linked_media_references':sum(x['kind']=='linked-media' for x in asset_map),'asset_status':dict(collections.Counter(x['status'] for x in asset_map)),'unique_local_assets':len(copied),'transforms':dict(transform_stats)}
    (migration/'migration-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
