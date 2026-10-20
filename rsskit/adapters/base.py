import feedparser
from ..common import soup,entry,canonical,unique,article_ld,text,date_value
from ..images import extract,first_img,valid_image

class Adapter:
    image_selectors=()
    def __init__(self,config,client,state,budget):
        self.config=config;self.client=client;self.state=state;self.budget=budget;self.errors=[];self.pages=0;self.coverage=[]
    def fetch(self,url):
        try:
            data=self.client.get(url);self.pages+=1;return data
        except Exception as e:
            self.errors.append({'url':url,'error':str(e)});return None
    def feed(self,url):
        raw=self.fetch(url)
        if raw is None:return []
        parsed=feedparser.parse(raw)
        if not parsed.entries:
            self.errors.append({'url':url,'error':'feed-empty-or-invalid'});return []
        out=[]
        for e in parsed.entries:
            u=canonical(e.get('link',''))
            if not u:continue
            item=entry(u,e.get('title',''),e.get('published',''));images=[]
            for key in ('media_content','media_thumbnail','enclosures'):
                for img in e.get(key,[]):
                    val=img.get('url') or img.get('href','')
                    if valid_image(val):images.append({'url':val,'source':'rss-'+key})
            for content in [e.get('summary','')]+[x.get('value','') for x in e.get('content',[])]:
                val=first_img(soup(content).find('img'),u)
                if val:images.append({'url':val,'source':'rss-html'})
            item['images']=images;out.append(item)
        return unique(out)
    def article(self,url):
        raw=self.client.get(url);s=soup(raw);nodes=article_ld(s)
        h=s.select_one('meta[property="og:title"]');title=h.get('content','') if h else ''
        date=''
        for n in nodes:
            title=n.get('headline') or title;date=n.get('datePublished') or date
        if not date:
            m=s.select_one('meta[property="article:published_time"], meta[itemprop="datePublished"]')
            if m:date=m.get('content','')
        if not date:
            t=s.select_one('time.published[datetime], time[datetime]')
            if t:date=t.get('datetime','')
        return s,entry(url,title,date),extract(s,url,self.image_selectors)
    def enrich(self,url):
        s,item,images=self.article(url);item['images']=images;return item
    def sequential(self,start,parse,bootstrap=False):
        url=start;seen=set();items=[];old=self.state.get('items',{})
        for page in range(self.budget):
            if not url or url in seen:break
            seen.add(url);raw=self.fetch(url)
            if raw is None:break
            batch,next_url=parse(raw,url);items.extend(batch)
            if not batch:
                self.errors.append({'url':url,'error':'listing-empty'});break
            # Traverse at least two pages; a known page is a recovery frontier, not one known article.
            if not bootstrap and page>=1 and all(x['url'] in old for x in batch):
                self.coverage.append('known-frontier');break
            url=next_url
        else:
            if url:self.coverage.append('page-budget-reached; recovery cursor retained')
        self.state['backfill_cursor']=url if url and url not in seen else ''
        return unique(items)

    def paginated_discovery(self,start,parse,bootstrap=False):
        cursor=self.state.get('resume_cursor','')
        mode=self.state.get('backfill_mode','bootstrap' if not self.state.get('last_success') else 'recovery')
        if mode=='bootstrap' and len(self.state.get('items',{}))>=500:
            cursor=''
        first=self.sequential(start,parse,bootstrap)
        next_cursor=self.state.get('backfill_cursor','')
        if cursor:
            first+=self.sequential(cursor,parse,mode=='bootstrap')
            next_cursor=self.state.get('backfill_cursor','')
        if bootstrap or not self.state.get('last_success'):mode='bootstrap'
        elif not cursor:mode='recovery'
        self.state['resume_cursor']=next_cursor
        self.state['backfill_mode']=mode
        return unique(first)
