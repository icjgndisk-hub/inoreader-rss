from __future__ import annotations
import argparse,concurrent.futures,datetime as dt,json,logging,os,sys,tomllib
from pathlib import Path
from .common import now,stamp,unique,date_rank
from .http import Client
from .images import probe,valid_image
from .adapters import ADAPTERS
from .storage import load,save,atomic
from .rss import ready,make,validate
LOG=logging.getLogger('rss')

def priority(image):
    source=image.get('source','')
    if 'og:image' in source:return 0
    if 'twitter' in source:return 1
    if 'weekly-list-large' in source:return 2
    if 'jsonld' in source:return 3
    if 'list' in source or 'metadata' in source:return 4
    if 'rss' in source:return 5
    return 6

def merge(old,new):
    before={k:old.get(k) for k in ('title','published','date_precision','image')}
    keep_date=bool(old.get('published')) and date_rank(old)>date_rank(new)
    for k,v in new.items():
        if k in ('published','date_precision') and keep_date:continue
        if k=='images':
            candidates={x['url']:x for x in old.get('images',[])}
            for image in v:
                if valid_image(image['url']):
                    u=image['url']
                    if u not in candidates or priority(image)<priority(candidates[u]):candidates[u]=image
            old['images']=sorted(candidates.values(),key=priority)[:12]
        elif v not in ('',None,[]):old[k]=v
    if before!={k:old.get(k) for k in before}:old['content_changed_at']=stamp()
    return old

def due(value,hours):
    if not value:return True
    return (now()-dt.datetime.fromisoformat(value)).total_seconds()>=hours*3600

def update(key,site,app,root,args):
    path=root/'state'/f'{key}.json';state=load(path);items=state['items'];started=stamp()
    if not args.force and not args.bootstrap and not due(state.get('last_attempt'),site['interval_minutes']/60):
        return key,{'status':'not_due','stored':len(items)}
    state['last_attempt']=started;client=Client(app);adapter=ADAPTERS[key](site,client,state,args.pages or app['max_list_pages'])
    candidates=adapter.discover(args.bootstrap)
    old_urls=set(items);new_count=0
    for candidate in candidates:
        url=candidate['url']
        if url not in items:
            items[url]={'url':url,'first_seen':started,'images':[]};new_count+=1
        merge(items[url],candidate)
    # Commit discovery before slow enrichment, so a terminated run retains the queue.
    save(path,state)
    errors=adapter.errors[:]
    discovered_urls={x['url'] for x in candidates}
    # Required metadata is retried on later runs. Reserve a quarter of budget for old backlog.
    required=[];refresh=[]
    for e in items.values():
        if not due(e.get('article_error_at'),1):continue
        missing=not e.get('title') or not e.get('published') or not e.get('images')
        tiny_only=bool(e.get('images')) and all('/s/' in x['url'] for x in e['images'])
        if (missing or tiny_only) and due(e.get('article_checked_at'),app['recheck_hours']):required.append(e)
        elif e['url'] in discovered_urls and due(e.get('article_checked_at'),app['recheck_hours']):refresh.append(e)
    required.sort(key=lambda e:e.get('published') or e.get('sitemap_modified') or e['first_seen'],reverse=True)
    budget=args.articles or app['max_article_requests']
    fresh=[e for e in required if e['url'] not in old_urls];backlog=[e for e in required if e['url'] in old_urls]
    selected=backlog[:max(1,budget//4)]+fresh
    selected+=backlog[max(1,budget//4):]
    selected=selected[:budget]
    # Use spare capacity for at most 8 article refreshes, favouring the newest entries.
    refresh.sort(key=lambda e:e.get('published',''),reverse=True)
    selected+=refresh[:min(8,max(0,budget-len(selected)))]
    article_ok=0
    for position,e in enumerate(selected):
        try:
            found=adapter.enrich(e['url']);merge(e,found);e['article_checked_at']=stamp();e.pop('article_error_at',None);article_ok+=1
        except Exception as exc:
            e['article_error_at']=stamp();errors.append({'url':e['url'],'error':str(exc)})
        if position%20==19:save(path,state)
    # Prefer verified public images. Unchecked images are explicitly marked in the report.
    publishable=ready(items.values())
    for e in publishable:
        options=[x for x in e.get('images',[]) if valid_image(x['url'])]
        e['images']=options
        if e.get('image') and not valid_image(e['image']):
            e['image']='';e['image_info']={'status':'no-article-image'}
        if not e.get('image') and options and e.get('image_info',{}).get('status')!='failed':
            e['image']=options[0]['url'];e['image_info']={'status':'unverified'}
    checks=0;image_ok=0
    for e in publishable[:app['feed_limit']]:
        if checks>=(args.images if args.images is not None else app['max_image_checks']):break
        if e.get('image_info',{}).get('status')=='ok' and not due(e.get('image_checked_at'),24*7):continue
        if not getattr(args,'retry_failed',False) and not due(e.get('image_error_at'),6):continue
        options=e.get('images',[])
        if not options:continue
        checks+=1;success=False
        for image in options[:4]:
            if not valid_image(image['url']):continue
            try:
                info=probe(client,image['url']);old=e.get('image');e['image']=image['url'];e['image_info']=info;e['image_checked_at']=stamp();e.pop('image_error_at',None)
                if old!=e['image']:e['content_changed_at']=stamp()
                image_ok+=1;success=True;break
            except Exception as exc:errors.append({'url':image['url'],'error':'image: '+str(exc)})
        if not success:
            e['image_error_at']=stamp();e['image']='';e['image_info']={'status':'failed'}
        if checks%20==0:save(path,state)
    if candidates:state['last_success']=started
    state['errors']=errors[-30:]
    # Retain ALL historical metadata; only the public feed has a sliding 500-item limit.
    save(path,state)
    feed=ready(items.values())[:app['feed_limit']]
    if feed:
        raw=make(site['name'],site['home'],feed,app['base_url'].rstrip('/')+'/'+key+'.xml' if app['base_url'] else '',site['interval_minutes'])
        validate(raw);atomic(root/'public'/f'{key}.xml',raw)
    report={'status':'ok' if candidates and not errors else 'partial' if candidates else 'failed',
        'checked_at':started,'discovered':len(candidates),'new':new_count,'stored':len(items),'feed_items':len(feed),
        'pending_metadata':len(items)-len(ready(items.values())),
        'images_in_feed':sum(bool(e.get('image')) for e in feed),
        'verified_images_in_feed':sum(e.get('image_info',{}).get('status')=='ok' and bool(e.get('image')) for e in feed),
        'article_attempts':len(selected),'article_successes':article_ok,'image_checks':checks,'image_successes':image_ok,
        'http_requests':client.requests,'pages':adapter.pages,'errors':errors[-30:], 'coverage':adapter.coverage,
        'newest_publication':feed[0]['published'] if feed else None,'oldest_in_feed':feed[-1]['published'] if feed else None}
    LOG.info('%s %s',key,json.dumps({k:v for k,v in report.items() if k not in ('errors','coverage')},ensure_ascii=False))
    return key,report

def write_index(root,config,reports):
    import html
    base=config['app']['base_url'].rstrip('/');rows=[]
    combined=[]
    for key,site in config['sites'].items():
        p=root/'state'/f'{key}.json'
        if not p.exists():continue
        for e in load(p)['items'].values():combined.append(dict(e,site_name=site['name']))
        r=reports.get(key,{});rows.append(f'<tr><td>{html.escape(site["name"])}</td><td><a href="{key}.xml">RSS</a></td><td>{r.get("feed_items","—")}</td><td>{r.get("images_in_feed","—")}</td><td>{html.escape(r.get("status","unknown"))}</td></tr>')
    items=ready(combined)[:config['app']['combined_limit']]
    if items:
        raw=make('4サイト統合',base or 'https://weekly.ascii.jp/',items,base+'/all.xml' if base else '')
        validate(raw);atomic(root/'public'/'all.xml',raw)
    page='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta name="robots" content="noindex"><title>Personal News RSS</title><style>body{font:16px system-ui;max-width:850px;margin:50px auto;padding:0 20px;line-height:1.7}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}a{color:#075a9e}table{border-collapse:collapse}</style><h1>Personal News RSS</h1><p>見出し・公開日時・元サイトの画像リンク。本文は配信元で読む。</p><table><tr><th>配信元</th><th>購読URL</th><th>記事</th><th>画像URLあり</th><th>収集状況</th></tr>'''+''.join(rows)+'''</table><p><a href="all.xml">4サイト統合RSS</a> · <a href="feeds.opml">OPML一括登録</a> · <a href="status.json">稼働状況・未検証画像数</a></p><p>RSS生成は15〜30分間隔の予定。GitHub Actionsの遅延とInoreader側の巡回間隔があるため、表示までの時間は保証されない。</p><p>画像は配信元から直接参照。Inoreader上の表示確認とは別に、画像URLのHTTP応答を検証している。</p></html>'''
    if not base:page=page.replace(' · <a href="feeds.opml">OPML一括登録</a>','')
    atomic(root/'public'/'index.html',page.encode());atomic(root/'public'/'.nojekyll',b'')
    # No robots exclusion for XML: feed readers must be allowed to retrieve it.
    atomic(root/'public'/'robots.txt',b'User-agent: *\nDisallow: /index.html\nDisallow: /status.json\n')
    if base:
        import xml.etree.ElementTree as ET
        opml=ET.Element('opml',version='2.0');head=ET.SubElement(opml,'head');ET.SubElement(head,'title').text='Personal News RSS';body=ET.SubElement(opml,'body')
        for key,site in config['sites'].items():ET.SubElement(body,'outline',{'text':site['name'],'title':site['name'],'type':'rss','xmlUrl':base+'/'+key+'.xml','htmlUrl':site['home']})
        atomic(root/'public'/'feeds.opml',ET.tostring(opml,encoding='utf-8',xml_declaration=True))
    atomic(root/'public'/'status.json',(json.dumps(reports,ensure_ascii=False,indent=2)+'\n').encode())

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--site',choices=['all',*ADAPTERS],default='all')
    parser.add_argument('--force',action='store_true');parser.add_argument('--bootstrap',action='store_true');parser.add_argument('--pages',type=int);parser.add_argument('--articles',type=int);parser.add_argument('--images',type=int);parser.add_argument('--base-url');parser.add_argument('--render-only',action='store_true');parser.add_argument('--retry-failed',action='store_true')
    args=parser.parse_args(argv);root=args.root.resolve();config=tomllib.loads((root/'config.toml').read_text('utf-8'));app=config['app']
    app['base_url']=args.base_url or os.environ.get('FEED_BASE_URL') or app['base_url']
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    p=root/'public'/'status.json';reports=json.loads(p.read_text()) if p.exists() else {};results={}
    if not args.render_only:
        keys=list(config['sites']) if args.site=='all' else [args.site]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            jobs={pool.submit(update,key,config['sites'][key],app,root,args):key for key in keys}
            for job in concurrent.futures.as_completed(jobs):
                key=jobs[job]
                try:_,report=job.result()
                except Exception as exc:
                    LOG.exception('%s failed; existing feed preserved',key);report={'status':'failed','checked_at':stamp(),'errors':[{'error':str(exc)}]}
                results[key]=report
                if report['status']!='not_due':reports[key]=report
    else:
        for key,site in config['sites'].items():
            p=root/'state'/f'{key}.json'
            if p.exists():
                items=ready(load(p)['items'].values())[:app['feed_limit']]
                if items:
                    raw=make(site['name'],site['home'],items,app['base_url'].rstrip('/')+'/'+key+'.xml' if app['base_url'] else '',site['interval_minutes']);validate(raw);atomic(root/'public'/f'{key}.xml',raw)
    write_index(root,config,reports)
    report_path=root/'reports'/'latest-run.json';atomic(report_path,(json.dumps({'generated_at':stamp(),'sites':reports},ensure_ascii=False,indent=2)+'\n').encode())
    return 1 if any(r['status']=='failed' for r in results.values()) else 0
if __name__=='__main__':raise SystemExit(main())
