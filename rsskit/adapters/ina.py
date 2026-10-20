from .base import Adapter
from ..common import soup,text,canonical,entry,unique,absolute
from ..images import first_img

class Ina(Adapter):
    image_selectors=('article img[src*="/uploads/topic/image/"]','img[src*="/uploads/topic/image/"]')
    def listing(self,raw,url):
        s=soup(raw);out=[]
        for a in s.select('a[href*="/topics/detail"]'):
            h=a.select_one('h4,h2,h3');t=a.select_one('time[datetime]');u=canonical(a['href'],url)
            if u and h:out.append(entry(u,text(h),t['datetime'] if t else '',first_img(a.find('img'),u),'ina-list'))
        from urllib.parse import urlsplit,parse_qs
        current=int(parse_qs(urlsplit(url).query).get('page',['1'])[0]);n=''
        for a in s.select('a[href*="page="]'):
            target=absolute(a['href'],url);p=parse_qs(urlsplit(target).query).get('page',[''])[0]
            if p==str(current+1):n=target;break
        return out,n
    def discover(self,bootstrap=False):
        return self.paginated_discovery(self.config['listing'],self.listing,bootstrap)
    def enrich(self,url):
        s,item,images=self.article(url)
        h=s.select_one('article h2, .topic-detail h2')
        if not h:
            hs=s.select('h2');h=hs[-1] if hs else None
        item['title']=text(h);item['images']=images;return item
