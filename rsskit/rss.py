import datetime as dt
import email.utils,html,json
import xml.etree.ElementTree as ET
from .common import clean
from .storage import atomic
MEDIA='http://search.yahoo.com/mrss/'
ATOM='http://www.w3.org/2005/Atom'
CONTENT='http://purl.org/rss/1.0/modules/content/'
for p,u in [('media',MEDIA),('atom',ATOM),('content',CONTENT)]:ET.register_namespace(p,u)

def ready(items):
    return sorted((e for e in items if e.get('title') and e.get('published')),key=lambda e:(e['published'],e['url']),reverse=True)

def make(name,home,items,self_url='',ttl=15):
    root=ET.Element('rss',version='2.0');ch=ET.SubElement(root,'channel')
    for k,v in [('title',name+'（画像付き・個人用）'),('link',home),('description',name+'の見出し・公開日時・画像リンク。本文は配信元で読む。'),('language','ja'),('ttl',str(ttl))]:ET.SubElement(ch,k).text=v
    if self_url:ET.SubElement(ch,'{'+ATOM+'}link',{'href':self_url,'rel':'self','type':'application/rss+xml'})
    # Stable serialization: an unchanged feed does not churn every 15 minutes.
    if items:
        latest=max(e.get('content_changed_at',e['published']) for e in items)
        ET.SubElement(ch,'lastBuildDate').text=email.utils.format_datetime(dt.datetime.fromisoformat(latest))
    for e in items:
        node=ET.SubElement(ch,'item')
        for k,v in [('title',e['title']),('link',e['url']),('guid',e['url']),('pubDate',email.utils.format_datetime(dt.datetime.fromisoformat(e['published'])))]:
            el=ET.SubElement(node,k);el.text=clean(v)
            if k=='guid':el.set('isPermaLink','true')
        source=e.get('site_name') or name
        img=e.get('image','');info=e.get('image_info',{})
        desc=''
        if img:
            dims=''
            if info.get('width') and info.get('height'):
                w=min(info['width'],640);h=round(info['height']*w/info['width']);dims=f' width="{w}" height="{h}"'
            desc=f'<p><a href="{html.escape(e["url"],quote=True)}"><img src="{html.escape(img,quote=True)}" alt="{html.escape(e["title"],quote=True)}"{dims} /></a></p>'
            attrs={'url':img}
            if info.get('width'):attrs.update(width=str(info['width']),height=str(info['height']))
            ET.SubElement(node,'{'+MEDIA+'}thumbnail',attrs)
            attrs=dict(attrs,medium='image')
            if info.get('mime'):attrs['type']=info['mime']
            ET.SubElement(node,'{'+MEDIA+'}content',attrs)
            if info.get('mime') and info.get('length',0)>0:
                ET.SubElement(node,'enclosure',{'url':img,'type':info['mime'],'length':str(info['length'])})
        desc+=f'<p>出典：{html.escape(source)} · <a href="{html.escape(e["url"],quote=True)}">元記事を読む</a></p>'
        if e.get('date_precision')=='day':desc+='<p>公開時刻は配信元に記載なし。日付のみを保持し、RSSでは日本時間00:00として表現。</p>'
        ET.SubElement(node,'description').text=desc
        ET.SubElement(node,'{'+CONTENT+'}encoded').text=desc
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def validate(raw):
    root=ET.fromstring(raw)
    if root.tag!='rss' or root.get('version')!='2.0':raise ValueError('not RSS 2.0')
    guids=set()
    for item in root.findall('./channel/item'):
        for field in ('title','link','guid','pubDate','description'):
            if not item.findtext(field):raise ValueError('missing '+field)
        guid=item.findtext('guid')
        if guid in guids:raise ValueError('duplicate guid')
        guids.add(guid)
        d=email.utils.parsedate_to_datetime(item.findtext('pubDate'))
        if not d.tzinfo:raise ValueError('missing timezone')
        enc=item.find('enclosure')
        if enc is not None and (not enc.get('type','').startswith('image/') or int(enc.get('length','0'))<=0):raise ValueError('invalid enclosure')
    return len(guids)
