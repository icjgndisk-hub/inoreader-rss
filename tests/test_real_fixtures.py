import unittest
from pathlib import Path
from rsskit.adapters import ADAPTERS
import tomllib
ROOT=Path(__file__).resolve().parents[1];CONFIG=tomllib.loads((ROOT/'config.toml').read_text())
class Fixtures(unittest.TestCase):
    def data(self,name):return (ROOT/'tests'/'fixtures'/(name+'.html')).read_bytes()
    def adapter(self,key,data=None):
        class Client:
            def get(self,url):return data
        return ADAPTERS[key](CONFIG['sites'][key],Client(),{},3)
    def test_weekly_actual_list(self):
        rows=self.adapter('weekly-ascii').listing(self.data('weekly-list'))
        self.assertEqual(len(rows),3);self.assertIn('HUB',rows[0]['title']);self.assertIn('/l/',rows[0]['images'][0]['url']);self.assertEqual(rows[0]['published'],'2026-10-20T08:00:00+09:00')
    def test_goguynet_actual_list(self):
        rows,n=self.adapter('goguynet-matsumoto').listing(self.data('goguynet-list'),'https://matsumoto.goguynet.jp/')
        self.assertEqual(len(rows),3);self.assertEqual(n,'https://matsumoto.goguynet.jp/page/2/');self.assertTrue(rows[0]['published'].startswith('2026-09-03'))
    def test_ina_actual_list(self):
        rows,n=self.adapter('ina-dani').listing(self.data('ina-list'),'https://ina-dani.net/topics/result')
        self.assertEqual(len(rows),3);self.assertEqual(rows[0]['title'],'南信州SSC 全国大会出場報告');self.assertEqual(n,'https://ina-dani.net/topics/result?page=2')
    def test_shinmai_actual_metadata(self):
        rows=self.adapter('shinmai').listing(self.data('shinmai-list'))
        self.assertEqual(len(rows),3);self.assertTrue(all(r['published'] and r['title'] for r in rows))
    def test_weekly_actual_article(self):
        e=self.adapter('weekly-ascii',self.data('weekly-article')).enrich('https://weekly.ascii.jp/elem/000/004/443/4443908/')
        self.assertEqual(e['published'],'2026-10-20T08:00:00+09:00');self.assertTrue(e['images'][0]['url'].endswith('/l/e43fdc0db41f631b.jpg'))
    def test_goguynet_original_date_not_october_update(self):
        e=self.adapter('goguynet-matsumoto',self.data('goguynet-article')).enrich('https://matsumoto.goguynet.jp/2026/09/03/mamorioh-heavyrain/')
        self.assertEqual(e['published'],'2026-09-03T18:07:59+09:00')
    def test_shinmai_actual_article(self):
        e=self.adapter('shinmai',self.data('shinmai-article')).enrich('https://www.shinmai.co.jp/news/article/gf01dbavkrlk0fh4r7aqevg0')
        self.assertEqual(e['published'],'2026-10-20T06:05:00+09:00');self.assertIn('シャトレーゼ',e['title']);self.assertIn('_M.jpg',e['images'][0]['url'])
    def test_ina_actual_article(self):
        e=self.adapter('ina-dani',self.data('ina-article')).enrich('https://ina-dani.net/topics/detail/?id=69475')
        self.assertEqual(e['title'],'南信州SSC 全国大会出場報告');self.assertEqual(e['date_precision'],'day');self.assertIn('/69475/',e['images'][0]['url'])
