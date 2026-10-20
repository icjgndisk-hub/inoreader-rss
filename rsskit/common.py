from __future__ import annotations
import datetime as dt
import email.utils
import html
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs
from bs4 import BeautifulSoup

JST = dt.timezone(dt.timedelta(hours=9))

def now(): return dt.datetime.now(JST)
def stamp(): return now().isoformat(timespec='seconds')
def soup(raw): return BeautifulSoup(raw, 'html.parser')
def text(node): return ' '.join(node.get_text(' ', strip=True).split()) if node else ''
def clean(value): return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', html.unescape(str(value or ''))).strip()

def absolute(value, base):
    try:
        p = urlsplit(urljoin(base, html.unescape(value or '').strip()))
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password: return ''
        return urlunsplit(p._replace(fragment=''))
    except ValueError: return ''

def canonical(value, base=''):
    url = absolute(value, base)
    if not url: return ''
    p = urlsplit(url)
    if p.hostname == 'ina-dani.net' and p.path.rstrip('/') == '/topics/detail':
        id_ = parse_qs(p.query).get('id', [''])[0]
        return f'https://ina-dani.net/topics/detail/?id={id_}' if id_.isdigit() else ''
    if p.hostname == 'weekly.ascii.jp' and re.fullmatch(r'/elem/(?:\d+/){4}', p.path):
        return 'https://weekly.ascii.jp' + p.path
    if p.hostname == 'matsumoto.goguynet.jp' and re.fullmatch(r'/20\d{2}/\d{2}/\d{2}/[^/]+/', p.path):
        return 'https://matsumoto.goguynet.jp' + p.path
    if p.hostname == 'www.shinmai.co.jp' and re.fullmatch(r'/news/article/[\w-]+/?', p.path):
        return 'https://www.shinmai.co.jp' + p.path.rstrip('/')
    return ''

def date_value(value):
    """Return timezone-aware ISO date and precision. Never invent publication time."""
    value = clean(value)
    if not value: return '', ''
    try:
        d = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        precision = ('day' if re.fullmatch(r'\d{4}-\d\d-\d\d', value)
                     else 'second' if re.search(r'[T ]\d\d:\d\d:\d\d',value) else 'minute')
    except ValueError:
        try:
            d = email.utils.parsedate_to_datetime(value); precision = 'second'
        except (ValueError, TypeError):
            m = re.search(r'(20\d{2})[年/.-](\d{1,2})[月/.-](\d{1,2})日?(?:\s+(\d{1,2})[時:](\d{2})(?:[分:](\d{2}))?)?', value)
            if not m: return '', ''
            y,mo,day,h,mi,se = m.groups()
            try: d = dt.datetime(int(y),int(mo),int(day),int(h or 0),int(mi or 0),int(se or 0))
            except ValueError: return '', ''
            precision = 'second' if se else 'minute' if h else 'day'
    if not d.tzinfo: d = d.replace(tzinfo=JST)
    return d.astimezone(JST).isoformat(), precision

def entry(url, title='', published='', image='', source=''):
    published, precision = date_value(published)
    return {'url':url, 'title':clean(title), 'published':published, 'date_precision':precision,
            'images':[{'url':image,'source':source}] if image else []}

def unique(items):
    out = {}
    for item in items:
        if not item.get('url'): continue
        old = out.setdefault(item['url'], entry(item['url']))
        keep_date=bool(old.get('published')) and date_rank(old)>date_rank(item)
        for key,value in item.items():
            if key in ('published','date_precision') and keep_date:continue
            if key == 'images':
                for image in value:
                    if image['url'] not in {x['url'] for x in old['images']}: old['images'].append(image)
            elif value: old[key] = value
    return list(out.values())

def date_rank(item):
    return {'day':1,'minute':2,'second':3}.get(item.get('date_precision'),0)

def article_ld(s):
    """Only article nodes; never pick an Organization logo as article image."""
    nodes = []
    for script in s.select('script[type="application/ld+json"]'):
        try: stack = [json.loads(script.string or script.get_text())]
        except (ValueError,TypeError): continue
        while stack:
            v = stack.pop()
            if isinstance(v,list): stack.extend(v)
            elif isinstance(v,dict):
                kinds = v.get('@type',[]); kinds = [kinds] if isinstance(kinds,str) else kinds
                if any(t in ('NewsArticle','Article','BlogPosting','ReportageNewsArticle') for t in kinds): nodes.append(v)
                if '@graph' in v: stack.append(v['@graph'])
    return nodes
