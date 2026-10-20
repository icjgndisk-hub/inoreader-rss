from __future__ import annotations
import re
from PIL import ImageFile
from .common import absolute, article_ld

BAD = re.compile(r'(?:logo|favicon|placeholder|no[_-]?(?:image|photo)|loading|spacer|blank\.|avatar|ogpsns|ico-sns|/banner|/ads/)',re.I)

def valid_image(url): return bool(url and not BAD.search(url) and not url.lower().endswith('.svg'))

def img_urls(tag, base):
    if not tag: return []
    values = []
    # Select a sufficiently large explicitly supplied candidate, never rewrite an image URL by guessing.
    for attr in ('data-srcset','srcset'):
        candidates = []
        for part in (tag.get(attr) or '').split(','):
            bits = part.strip().split()
            if bits:
                try: size=float(bits[1][:-1]) if len(bits)>1 else 0
                except ValueError: size=0
                candidates.append((size,bits[0]))
        values.extend(v for _,v in sorted(candidates,reverse=True))
    values.extend(tag.get(k,'') for k in ('data-src','data-original','data-lazy-src','src'))
    out=[]
    for value in values:
        if not value or value.startswith('data:'): continue
        u=absolute(value,base)
        if valid_image(u) and u not in out: out.append(u)
    return out

def first_img(tag,base): return next(iter(img_urls(tag,base)), '')

def extract(s, url, selectors):
    out=[]
    def add(value,source):
        u=absolute(value,url)
        if valid_image(u) and u not in {x['url'] for x in out}: out.append({'url':u,'source':source})
    for selector in ('meta[property="og:image"]','meta[name="twitter:image"]','meta[property="twitter:image"]','meta[name="twitter:image:src"]'):
        for tag in s.select(selector): add(tag.get('content',''),selector)
    def ldimages(v):
        if isinstance(v,str): add(v,'article-jsonld')
        elif isinstance(v,list):
            for x in v: ldimages(x)
        elif isinstance(v,dict): ldimages(v.get('url') or v.get('contentUrl') or '')
    for node in article_ld(s): ldimages(node.get('image') or node.get('thumbnailUrl') or '')
    for selector in selectors:
        for tag in s.select(selector)[:4]:
            for u in img_urls(tag,url): add(u,'article-main')
    return out

def probe(client,url):
    """No Referer spoofing, cookies or copying images into the published site."""
    parser=ImageFile.Parser()
    with client.stream(url) as r:
        mime=r.headers.get('Content-Type','').split(';')[0].lower()
        if not mime.startswith('image/'): raise ValueError('not-image-content-type: '+mime)
        size=0
        for chunk in r.iter_content(16384):
            parser.feed(chunk);size+=len(chunk)
            if parser.image: break
            if size > 524288: raise ValueError('image-header-too-large')
        if not parser.image: raise ValueError('unrecognized-image')
        width,height=parser.image.size
        if min(width,height)<80: raise ValueError(f'too-small: {width}x{height}')
        return {'status':'ok','mime':mime,'width':width,'height':height,'length':int(r.headers.get('Content-Length','0') or 0)}
