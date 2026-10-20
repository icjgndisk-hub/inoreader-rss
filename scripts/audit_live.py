"""Explicit, bounded live audit. Not run on every scheduled collection."""
import io,json,sys,tomllib,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from rsskit.http import Client
from rsskit.storage import load,atomic
from rsskit.common import stamp
from rsskit.rss import ready
from rsskit.adapters import ADAPTERS
ROOT=Path(__file__).resolve().parents[1]
config=tomllib.loads((ROOT/'config.toml').read_text())
def check(key):
    client=Client(config['app']);adapter=ADAPTERS[key](config['sites'][key],client,{},2)
    rows=[]
    items=ready(load(ROOT/'state'/f'{key}.json')['items'].values())[:500]
    sample=[e for e in items if e.get('image_info',{}).get('status')=='ok' and e.get('image')][:3]
    for e in sample:
        row={'article_url':e['url'],'image_url':e['image'],'saved_publication':e['published'],'date_precision':e.get('date_precision')}
        try:
            found=adapter.enrich(e['url'])
            row.update(article_http_ok=True,article_title_found=bool(found.get('title')),article_publication=found.get('published'),image_in_article_candidates=e['image'] in [x['url'] for x in found.get('images',[])])
        except Exception as exc:row.update(article_http_ok=False,article_error=str(exc))
        try:
            with client.stream(e['image']) as response:
                chunks=[];size=0
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size>8*1024*1024:raise ValueError('audit image exceeds 8MB limit')
                    chunks.append(chunk)
                raw=b''.join(chunks);im=Image.open(io.BytesIO(raw));width,height=im.size;im.verify()
                row.update(image_http_status=response.status_code,mime=response.headers.get('Content-Type'),width=width,height=height,bytes=len(raw),image_file_verified=True)
        except Exception as exc:row.update(image_file_verified=False,image_error=str(exc))
        rows.append(row)
    return key,rows
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=dict(pool.map(check,config['sites']))
    report={'checked_at':stamp(),'sample_policy':'Latest 3 already HTTP/header-verified feed images per site; selection is not random. Full image bytes checked by Pillow.verify; no image files retained. No Inoreader UI verification.','sites':results}
    atomic(ROOT/'reports'/'live-sample-audit.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    for key,rows in results.items():print(key,'article',sum(r['article_http_ok'] for r in rows),'image',sum(r['image_file_verified'] for r in rows),'/',len(rows))
    sys.exit(0 if all(r['article_http_ok'] and r['image_file_verified'] for rows in results.values() for r in rows) else 1)
