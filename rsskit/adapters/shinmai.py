import json,xml.etree.ElementTree as ET
from .base import Adapter
from ..common import soup,text,canonical,entry,unique,absolute

class Shinmai(Adapter):
    image_selectors=('article img[src*="image.shinmai.co.jp"]',)
    def listing(self,raw):
        s=soup(raw);items=[]
        # Public server-rendered metadata only. Do not read article body, entitlement fields or private APIs.
        node=s.select_one('script#__NEXT_DATA__')
        if node:
            data=json.loads(node.string or node.get_text());cache=data.get('props',{}).get('pageProps',{}).get('__APOLLO_STATE__',{})
            for obj in cache.values():
                if not isinstance(obj,dict) or obj.get('__typename')!='ArticleNode':continue
                u=canonical('/news/article/'+str(obj.get('_id','')),self.config['home'])
                if not u:continue
                image=obj.get('image') or {};path=image.get('medium') or image.get('low') or ''
                item=entry(u,obj.get('headline',''),obj.get('publishDate',''),absolute(path,'https://image.shinmai.co.jp/') if path else '', 'shinmai-public-metadata')
                item['paywall']=obj.get('keyMark') not in ('free','',None);items.append(item)
        return unique(items)
    def discover(self,bootstrap=False):
        items=[]
        for url in [self.config['home']]+self.config['listings']:
            raw=self.fetch(url)
            if raw:
                try:items+=self.listing(raw)
                except (ValueError,TypeError) as e:self.errors.append({'url':url,'error':str(e)})
        raw=self.fetch(self.config['sitemap'])
        if raw:
            try:
                root=ET.fromstring(raw)
                for node in root.findall('{*}url'):
                    u=canonical(node.findtext('{*}loc',''))
                    if not u:continue
                    it=entry(u);it['sitemap_modified']=node.findtext('{*}lastmod','');items.append(it)
            except ET.ParseError as e:self.errors.append({'url':self.config['sitemap'],'error':str(e)})
        self.coverage.append('public SSR listings + rolling sitemap; sitemap lastmod is NOT publication date')
        return unique(items)
