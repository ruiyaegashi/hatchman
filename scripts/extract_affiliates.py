from __future__ import annotations
import argparse, collections, html, json, re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

FM=re.compile(r'^---\s*\n(.*?)\n---\s*\n',re.S)
URL=re.compile(r"https?://[^\s<>'\"]+|//(?:www\.)?(?:amazon\.[^/\s]+|amzn\.to)/[^\s<>'\"]+",re.I)
ASIN_PATH=re.compile(r'/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:[/?]|$)',re.I)
SHORTCODE=re.compile(r'\[amazonjs\b([^\]]*)\]',re.I)

def scalar(block,key,default=''):
    m=re.search(rf'(?m)^{re.escape(key)}:\s*(.+)$',block)
    if not m:return default
    value=m.group(1).strip()
    try:return json.loads(value)
    except Exception:return value.strip('"\'')

def extract_product_url(url):
    clean=html.unescape(url).rstrip(').,;"\'')
    p=urlsplit('https:'+clean if clean.startswith('//') else clean)
    asin=None
    m=ASIN_PATH.search(p.path)
    if m: asin=m.group(1).upper()
    q=parse_qs(p.query)
    if not asin:
        values=q.get('asins') or q.get('ASIN') or q.get('asin') or []
        if values and re.fullmatch(r'[A-Z0-9]{10}',values[0],re.I): asin=values[0].upper()
    tags=(q.get('tag') or q.get('t') or [])
    return clean,asin,tags

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--site',required=True); ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); args=ap.parse_args()
    root=args.root.resolve(); articles=[]; observed_tags=collections.Counter(); signal_articles=0; unique_asins=set(); short_urls=set(); occurrences=0
    for path in sorted((root/'src/content/legacy').glob('*.md')):
        text=path.read_text(encoding='utf-8'); m=FM.match(text)
        if not m: continue
        fm=m.group(1); body=html.unescape(text[m.end():]); status=scalar(fm,'status')
        if status!='publish': continue
        item={'wp_id':int(scalar(fm,'wp_id',0)),'slug':scalar(fm,'legacy_slug',scalar(fm,'slug','')),'legacy_path':scalar(fm,'legacy_path',''),'title':scalar(fm,'title',''),'has_legacy_amazon':False,'selection_status':'no-product-selected','review_status':'not-needed','products':[],'unresolved_urls':[]}
        products={}
        for sm in SHORTCODE.finditer(body):
            attrs=sm.group(1); am=re.search(r'\basin\s*=\s*["\']([^"\']+)',attrs,re.I); tm=re.search(r'\btitle\s*=\s*["\']([^"\']*)',attrs,re.I)
            if am and re.fullmatch(r'[A-Z0-9]{10}',am.group(1),re.I):
                asin=am.group(1).upper(); occurrences+=1
                products.setdefault(asin,{'old_asin':asin,'current_asin':asin,'legacy_title':tm.group(1) if tm else None,'legacy_source':'amazonjs','selection_type':'legacy','confidence':'high','current_status':'unknown','display_status':'pending','reason':'旧amazonjsでASINを明示'})
        for raw in URL.findall(body):
            url,asin,tags=extract_product_url(raw)
            host=urlsplit('https:'+url if url.startswith('//') else url).netloc.lower()
            if 'amazon.' not in host and host not in {'amzn.to','www.amzn.to'}: continue
            for tag in tags: observed_tags[tag]+=1
            if asin:
                occurrences+=1; products.setdefault(asin,{'old_asin':asin,'current_asin':asin,'legacy_title':None,'legacy_source':'amazon-url','selection_type':'legacy','confidence':'high','current_status':'unknown','display_status':'pending','reason':'旧Amazon URLからASINを抽出'})
            elif host in {'amzn.to','www.amzn.to'}:
                short_urls.add(url); item['unresolved_urls'].append({'url':url,'type':'amazon-short-url','confidence':'medium','status':'unresolved'})
        # Amazon widget query strings can be HTML-escaped or appear without a complete URL.
        for asin in re.findall(r'(?:\?|&|&amp;)asins=([A-Z0-9]{10})',body,re.I):
            asin=asin.upper(); occurrences+=1; products.setdefault(asin,{'old_asin':asin,'current_asin':asin,'legacy_title':None,'legacy_source':'amazon-widget','selection_type':'legacy','confidence':'high','current_status':'unknown','display_status':'pending','reason':'旧Amazon widgetのasinsから抽出'})
        for tag in re.findall(r'(?:\?|&|&amp;)(?:tag|t)=([A-Za-z0-9_-]+-\d+)',body,re.I): observed_tags[tag]+=1
        item['products']=list(products.values()); item['has_legacy_amazon']=bool(products or item['unresolved_urls'] or re.search(r'Amazon|アマゾン',body,re.I))
        if item['has_legacy_amazon']:
            signal_articles+=1; item['selection_status']='legacy-extracted'; item['review_status']='pending'
        unique_asins.update(products); articles.append(item)
    out=root/'affiliate'; out.mkdir(exist_ok=True)
    inferred_tag=observed_tags.most_common(1)[0][0] if observed_tags else None
    mapping={'schema_version':1,'site':args.site,'source':'legacy-markdown','api':'Amazon Creators API','marketplace':'www.amazon.co.jp','associate_tag':inferred_tag,'articles':articles}
    (out/'mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'public_articles':len(articles),'articles_with_amazon_signals':signal_articles,'product_occurrences':occurrences,'unique_asins':len(unique_asins),'unresolved_short_urls':len(short_urls),'observed_associate_tags':dict(observed_tags),'high':sum(len(a['products']) for a in articles),'medium':sum(len(a['unresolved_urls']) for a in articles),'low':0,'articles_without_selected_product':sum(not a['products'] for a in articles)}
    (out/'audit-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
