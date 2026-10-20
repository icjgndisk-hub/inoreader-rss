import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rsskit.rss import validate
import feedparser
root=Path(__file__).resolve().parents[1]
for name in ['weekly-ascii','goguynet-matsumoto','shinmai','ina-dani','all']:
    p=root/'public'/f'{name}.xml'
    if not p.exists():raise SystemExit('Missing feed: '+str(p))
    count=validate(p.read_bytes());f=feedparser.parse(p.read_bytes())
    if f.bozo:raise SystemExit(f'Feed parser rejected {p}: {f.bozo_exception}')
    if count==0:raise SystemExit('Empty feed: '+str(p))
    print(name,count,'items',p.stat().st_size,'bytes; XML and feedparser OK')
