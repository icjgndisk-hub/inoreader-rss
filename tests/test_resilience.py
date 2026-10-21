import unittest,tempfile,tomllib,json,datetime as dt
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import requests
from rsskit.common import entry,now
from rsskit.http import Client,FetchError
from rsskit.images import valid_image
from rsskit.runner import update
from rsskit.storage import save,load
from rsskit.adapters.ina import Ina
ROOT=Path(__file__).resolve().parents[1];CONFIG=tomllib.loads((ROOT/'config.toml').read_text())

class Resilience(unittest.TestCase):
    def response(self,status,body=b'',mime='text/plain',headers=None):
        r=requests.Response();r.status_code=status;r._content=body;r._content_consumed=True;r.headers['Content-Type']=mime;r.url='https://img.example/robots.txt'
        if headers:r.headers.update(headers)
        return r
    def client(self):
        app=dict(CONFIG['app'],request_delay=0,retries=2);return Client(app)
    def test_robots403_unavailable_but_article403_still_fails(self):
        c=self.client()
        with patch.object(c.session,'get',side_effect=[self.response(403),self.response(403)]):
            with self.assertRaises(requests.HTTPError):c.get('https://img.example/photo.jpg')
    def test_robots_disallow_does_not_fetch_target(self):
        c=self.client()
        with patch.object(c.session,'get',return_value=self.response(200,b'User-agent: *\nDisallow: /blocked')) as get:
            with self.assertRaises(FetchError):c.get('https://img.example/blocked')
            self.assertEqual(get.call_count,1)
    def test_server_error_retries_then_recovers(self):
        c=self.client()
        with patch.object(c.session,'get',side_effect=[self.response(404),self.response(503),self.response(200,b'OK')]),patch('rsskit.http.time.sleep'):
            self.assertEqual(c.get('https://img.example/feed'),b'OK');self.assertEqual(c.requests,3)
    def test_retry_after_is_deferred(self):
        c=self.client()
        with patch.object(c.session,'get',side_effect=[self.response(404),self.response(429,headers={'Retry-After':'120'})]):
            with self.assertRaisesRegex(FetchError,'retry-deferred'):c.get('https://img.example/feed')
    def test_nophoto_not_article_image(self):self.assertFalse(valid_image('https://image.shinmai.co.jp/web-image/noPhoto/noPhoto_S.jpg'))
    def test_backfill_stops_after_bootstrap_target(self):
        state={'items':{str(i):{} for i in range(500)},'last_success':'2026-10-20T00:00:00+09:00','backfill_mode':'bootstrap','resume_cursor':'https://ina-dani.net/topics/result?page=19'}
        a=Ina(CONFIG['sites']['ina-dani'],None,state,3)
        with patch.object(a,'sequential',return_value=[]) as seq:
            a.discover();self.assertEqual(seq.call_count,1)
    def test_failed_image_not_republished_during_cooldown(self):
        app=CONFIG['app'];e=entry('https://ina-dani.net/topics/detail/?id=1','Title','2026-10-19','https://ina-dani.net/uploads/topic/image/1/test.jpg','list')
        e.update(first_seen=now().isoformat(),article_checked_at=now().isoformat(),image='',image_info={'status':'failed'},image_error_at=now().isoformat())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);save(root/'state'/'ina-dani.json',{'version':2,'items':{e['url']:e}})
            with patch.object(Ina,'discover',return_value=[entry(e['url'],'Title','2026-10-19')]),patch('rsskit.runner.probe') as probe:
                update('ina-dani',CONFIG['sites']['ina-dani'],app,root,SimpleNamespace(force=True,bootstrap=False,pages=1,articles=1,images=10))
                self.assertFalse(probe.called)
            self.assertNotIn(b'<img', (root/'public'/'ina-dani.xml').read_bytes())
            self.assertEqual(load(root/'state'/'ina-dani.json')['items'][e['url']]['image'],'')
    def test_old_broken_listing_image_recovers_from_article_alternative(self):
        e=entry('https://ina-dani.net/topics/detail/?id=1','Old article','2026-10-01','https://ina-dani.net/uploads/topic/image/1/broken.jpg','list')
        e.update(first_seen=now().isoformat(),image='',image_info={'status':'failed'},image_error_at=now().isoformat())
        replacement='https://ina-dani.net/uploads/topic/image/1/main.jpg'
        current=entry('https://ina-dani.net/topics/detail/?id=2','New article','2026-10-20','https://ina-dani.net/uploads/topic/image/2/main.jpg','list')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);save(root/'state'/'ina-dani.json',{'version':2,'items':{e['url']:e}})
            def image_probe(client,url):
                if url.endswith('broken.jpg'):raise RuntimeError('404')
                return {'status':'ok','mime':'image/jpeg','width':640,'height':480,'length':1000}
            with patch.object(Ina,'discover',return_value=[current]),patch.object(Ina,'enrich',return_value=entry(e['url'],'Old article','2026-10-01',replacement,'og:image')) as enrich,patch('rsskit.runner.probe',side_effect=image_probe):
                update('ina-dani',CONFIG['sites']['ina-dani'],CONFIG['app'],root,SimpleNamespace(force=True,bootstrap=False,pages=1,articles=1,images=10))
            enrich.assert_called_once_with(e['url'])
            saved=load(root/'state'/'ina-dani.json')['items'];self.assertEqual(len(saved),2)
            self.assertEqual(saved[e['url']]['image'],replacement)
            self.assertEqual(saved[e['url']]['published'],e['published'])
if __name__=='__main__':unittest.main()

class Precision(unittest.TestCase):
    def test_precise_rss_date_survives_minute_listing(self):
        from rsskit.common import unique
        from rsskit.runner import merge
        a=entry('u','Title','Thu, 03 Sep 2026 09:07:59 +0000')
        b=entry('u','Title','2026/09/03 18:07')
        self.assertEqual(unique([a,b])[0]['published'],'2026-09-03T18:07:59+09:00')
        merge(a,b);self.assertEqual(a['published'],'2026-09-03T18:07:59+09:00')
