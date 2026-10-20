import datetime as dt
from .base import Adapter
from ..common import soup,text,canonical,entry,unique,now
from ..images import first_img

class Weekly(Adapter):
    image_selectors=('.article__body #contents_detail img',)
    def listing(self,raw):
        s=soup(raw);out=[]
        for a in s.select('a.articleList__inner[href]'):
            u=canonical(a['href'],self.config['home'])
            if u:out.append(entry(u,text(a.select_one('.articleList__text--title')),text(a.select_one('.articleList__text--date')),first_img(a.find('img'),u),'weekly-list-large'))
        return out
    def discover(self,bootstrap=False):
        items=self.feed(self.config['feed'])
        raw=self.fetch(self.config['home'])
        if raw:items+=self.listing(raw)
        # Month archives recover entries that have already rolled out of the 32-item source feed.
        last=self.state.get('last_success','')
        d=now().replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        frontier=dt.datetime.fromisoformat(last).replace(day=1) if last else d
        cursor=self.state.get('archive_cursor')
        months=[d]
        if cursor:
            candidate=dt.datetime.fromisoformat(cursor)
            if candidate<d:months.append(candidate)
        if bootstrap or frontier<d:
            if len(months)<2:months.append(d-dt.timedelta(days=1))
        for month in months[:self.config.get('archive_months_per_run',2)]:
            raw=self.fetch(f'{self.config["home"]}archive/top/{month:%Y%m}/')
            if raw:items+=self.listing(raw)
        oldest=months[-1].replace(day=1)
        self.state['archive_cursor']=(oldest-dt.timedelta(days=1)).replace(day=1).isoformat() if oldest>frontier else ''
        self.coverage.append('rss + top + monthly archives')
        return unique(items)
    def enrich(self,url):
        s,item,images=self.article(url)
        item['title']=item['title'].removesuffix(' - 週刊アスキー')
        if not item['published']:
            from ..common import date_value
            item['published'],item['date_precision']=date_value(text(s.select_one('p.date')))
        item['images']=images;return item
