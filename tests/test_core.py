import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from rsskit.common import canonical,date_value,soup,entry,unique
from rsskit.images import extract,img_urls
from rsskit.runner import merge,update
from rsskit.rss import make,validate,ready
from rsskit.storage import save,load
from rsskit.adapters.ina import Ina
from rsskit.adapters.shinmai import Shinmai

class CoreTests(unittest.TestCase):
    def test_canonical(self):
        self.assertEqual(canonical('https://weekly.ascii.jp/elem/000/004/443/4443908/?p=2&utm_source=x#foo'),'https://weekly.ascii.jp/elem/000/004/443/4443908/')
        self.assertEqual(canonical('https://ina-dani.net/topics/detail?id=69475&utm_source=x'),'https://ina-dani.net/topics/detail/?id=69475')
        self.assertEqual(canonical('https://evil.example/news/article/123'),'')
    def test_date_precision_timezone(self):
        self.assertEqual(date_value('2026年10月20日 08時00分更新')[0],'2026-10-20T08:00:00+09:00')
        self.assertEqual(date_value('Thu, 03 Sep 2026 09:07:59 +0000')[0],'2026-09-03T18:07:59+09:00')
        self.assertEqual(date_value('2026-10-19'),('2026-10-19T00:00:00+09:00','day'))
        self.assertEqual(date_value('not known'),('',''))
    def test_article_ld_not_logo(self):
        s=soup('<script type="application/ld+json">{"@type":"Organization","image":"https://a.example/brand.jpg"}</script><script type="application/ld+json">{"@type":"NewsArticle","image":{"url":"/news.jpg"},"publisher":{"logo":"/brand.jpg"}}</script>')
        self.assertEqual(extract(s,'https://a.example/a',[]),[{'url':'https://a.example/news.jpg','source':'article-jsonld'}])
    def test_lazy_srcset(self):
        s=soup('<img src="/loading.gif" data-src="/small.jpg" data-srcset="/small.jpg 320w, /large.jpg 1200w">')
        self.assertEqual(img_urls(s.img,'https://a.example/a')[0],'https://a.example/large.jpg')
        self.assertNotIn('https://a.example/loading.gif',img_urls(s.img,'https://a.example/a'))
    def test_rss_escape_enclosure(self):
        e=entry('https://ina-dani.net/topics/detail/?id=1','A & B <C>','2026-10-20','https://img.example/a.jpg?a=1&b=2','test');e['image']=e['images'][0]['url'];e['image_info']={'mime':'image/jpeg','length':123,'width':1200,'height':800}
        raw=make('テスト','https://example.com/',[e]);self.assertEqual(validate(raw),1)
        self.assertIn(b'&amp;',raw);self.assertIn(b'media:thumbnail',raw);self.assertIn(b'length="123"',raw)
    def test_unknown_date_quarantined(self):self.assertEqual(ready([entry('https://example.com/a','Title')]),[])
    def test_merge_preserves_date(self):
        e=entry('u','title','2026-10-19','https://i.example/one.jpg','list');merge(e,entry('u','changed','','https://i.example/one.jpg','list'))
        self.assertEqual(e['title'],'changed');self.assertEqual(e['published'],'2026-10-19T00:00:00+09:00');self.assertEqual(len(e['images']),1)
    def test_state_backup_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';save(p,{'version':2,'items':{'a':{'url':'a'}}});save(p,{'version':2,'items':{'a':{'url':'a'},'b':{'url':'b'}}})
            self.assertEqual(len(load(p)['items']),2);self.assertEqual(len(load(str(p)+'.bak')['items']),1);p.write_text('{broken')
            with self.assertRaises(ValueError):load(p)
    def test_listing_date_pagination(self):
        a=Ina({},None,{},3);items,n=a.listing(b'<li><a href="/topics/detail/?id=1"><h4>News</h4><time datetime="2026-10-19"></time><img src="/uploads/topic/image/1/a.jpg"></a></li><a href="/topics/result?page=2">2</a>','https://ina-dani.net/topics/result')
        self.assertEqual(items[0]['date_precision'],'day');self.assertEqual(n,'https://ina-dani.net/topics/result?page=2')
    def test_shinmai_public_fields_only(self):
        obj={'props':{'pageProps':{'__APOLLO_STATE__':{'ArticleNode:1':{'__typename':'ArticleNode','_id':'gf01test','headline':'Title','publishDate':'2026-10-20T06:05:00+09:00','body':'MUST NOT COPY','image':{'low':'/web-image/a.jpg'}}}}}}
        a=Shinmai({'home':'https://www.shinmai.co.jp/'},None,{},3);out=a.listing('<script id="__NEXT_DATA__">'+json.dumps(obj)+'</script>')
        self.assertEqual(len(out),1);self.assertNotIn('MUST NOT COPY',json.dumps(out))
    def test_sitemap_lastmod_is_not_pubdate(self):
        class Fake:
            def get(self,url):return b'<urlset><url><loc>https://www.shinmai.co.jp/news/article/gf01test</loc><lastmod>2026-10-20</lastmod></url></urlset>' if 'sitemap' in url else b'<html></html>'
        a=Shinmai({'home':'https://www.shinmai.co.jp/','listings':[],'sitemap':'https://www.shinmai.co.jp/sitemap.xml'},Fake(),{},3)
        out=a.discover();self.assertEqual(out[0]['published'],'');self.assertTrue(out[0]['sitemap_modified'])
    def test_outage_preserves_existing(self):
        import tomllib
        config=tomllib.loads((Path(__file__).resolve().parents[1]/'config.toml').read_text());app=config['app']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);e=entry('https://ina-dani.net/topics/detail/?id=1','Old title','2026-10-19');e.update(first_seen='2026-10-19T01:00:00+09:00',article_checked_at='2099-01-01T00:00:00+09:00')
            save(root/'state'/'ina-dani.json',{'version':2,'items':{e['url']:e}})
            with patch('rsskit.http.Client.get',side_effect=ConnectionError('offline')):
                _,r=update('ina-dani',config['sites']['ina-dani'],app,root,SimpleNamespace(force=True,bootstrap=False,pages=1,articles=1,images=0))
            self.assertEqual(r['status'],'failed');self.assertEqual(len(load(root/'state'/'ina-dani.json')['items']),1);self.assertEqual(validate((root/'public'/'ina-dani.xml').read_bytes()),1)
    def test_duplicate_merge(self):
        a=entry('a','A','2026-10-20');b=entry('a','A edited','')
        self.assertEqual(len(unique([a,b])),1);self.assertEqual(unique([a,b])[0]['published'],a['published'])
if __name__=='__main__':unittest.main()
