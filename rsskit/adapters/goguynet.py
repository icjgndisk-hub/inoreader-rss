from .base import Adapter
from ..common import soup,text,canonical,entry,unique,absolute
from ..images import first_img

class Goguynet(Adapter):
    image_selectors=('article .singleBox01 img',)
    def listing(self,raw,url):
        s=soup(raw);items=[]
        for a in s.select('a.itemTitle01[href]'):
            u=canonical(a['href'],url)
            if u:items.append(entry(u,text(a.select_one('.itemTitle01In')),text(a.select_one('.listDate01')),first_img(a.find('img'),u),'goguynet-list'))
        n=s.select_one('a.nextpostslink[href], a[rel="next"][href], link[rel="next"][href]')
        return items,absolute(n['href'],url) if n else ''
    def discover(self,bootstrap=False):
        return unique(self.feed(self.config['feed'])+self.paginated_discovery(self.config['home'],self.listing,bootstrap))
