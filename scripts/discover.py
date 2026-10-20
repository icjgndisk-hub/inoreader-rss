"""Inspect declared RSS/Atom/JSON Feed. Does not enable untested scrapers."""
import sys,json,tomllib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rsskit.http import Client
from rsskit.common import soup,absolute
import feedparser
if len(sys.argv)!=2:raise SystemExit('Usage: python scripts/discover.py https://example.com/')
u=sys.argv[1];app=tomllib.loads((Path(__file__).resolve().parents[1]/'config.toml').read_text())['app'];client=Client(app);s=soup(client.get(u));results=[]
for link in s.select('link[rel="alternate"][href]'):
    kind=link.get('type','')
    if kind not in ('application/rss+xml','application/atom+xml','application/feed+json'):continue
    url=absolute(link['href'],u)
    try:
        data=client.get(url)
        if kind=='application/feed+json':
            p=json.loads(data);count=len(p.get('items',[]));images=sum(bool(x.get('image') or x.get('banner_image')) for x in p.get('items',[]));bozo=False
        else:
            p=feedparser.parse(data);count=len(p.entries);images=sum(bool(x.get('media_thumbnail') or x.get('media_content') or '<img' in x.get('summary','')) for x in p.entries);bozo=bool(p.bozo)
        results.append({'url':url,'type':kind,'entries':count,'image_hints':images,'parse_warning':bozo})
    except Exception as e:results.append({'url':url,'error':str(e)})
print(json.dumps({'site':u,'feeds':results,'next':'Site-specific adapter and image verification required.'},ensure_ascii=False,indent=2))
