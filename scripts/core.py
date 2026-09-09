from __future__ import annotations
import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse

UTC=timezone.utc
def now_iso():return datetime.now(UTC).isoformat()

def parse_date(value):
    if not value:return None
    if isinstance(value,list):value=value[0] if value else ''
    value=str(value).strip()
    try:dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:
        try:dt=parsedate_to_datetime(value)
        except (ValueError,TypeError,OverflowError):
            dt=None
            m=re.search(r'(20\d{2})[年/.-](\d{1,2})[月/.-](\d{1,2})',value)
            if m:
                try:dt=datetime(*map(int,m.groups()),tzinfo=UTC)
                except ValueError:return None
            if not dt:
                m=re.search(r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+20\d{2}',value,re.I)
                if m:
                    for fmt in ['%b %d, %Y','%B %d, %Y','%b %d %Y','%B %d %Y']:
                        try:dt=datetime.strptime(m[0],fmt);break
                        except ValueError:pass
            if not dt:return None
    return dt.replace(tzinfo=dt.tzinfo or UTC).astimezone(UTC).isoformat()

def canonical_url(url):
    p=urlparse(url)
    if p.scheme not in ('https','http') or not p.hostname:return None
    params=[(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k not in ['fbclid','gclid']]
    return urlunparse((p.scheme,p.netloc.lower(),p.path.rstrip('/') or '/',p.params,urlencode(params),''))

def clean_text(value):
    from bs4 import BeautifulSoup
    return re.sub(r'\s+',' ',BeautifulSoup(str(value or ''),'html.parser').get_text(' ',strip=True)).strip()

def parse_feed(content,base_url):
    if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():raise ValueError('Feed contains unsupported DTD')
    root=ET.fromstring(content)
    local=lambda x:x.tag.rsplit('}',1)[-1]
    if local(root) not in ['rss','feed','RDF']:raise ValueError('Response is not RSS or Atom')
    rows=[]
    for node in root.iter():
        if local(node) not in ['item','entry']:continue
        fields={};links=[]
        for child in node:
            key=local(child)
            fields[key]=''.join(child.itertext())
            if key=='link':links.append(child)
        link=next((x.attrib.get('href') or x.text for x in links if x.attrib.get('rel','alternate')=='alternate'),None)
        if not link:continue
        url=canonical_url(urljoin(base_url,link.strip()))
        if not url:continue
        rows.append(dict(title=clean_text(fields.get('title')),url=url,
          published_at=parse_date(fields.get('pubDate') or fields.get('published') or fields.get('date')),
          updated_at=parse_date(fields.get('updated')),
          summary=clean_text(fields.get('description') or fields.get('summary') or fields.get('encoded') or fields.get('content'))[:900]))
    return rows

def has_term(text,term):
    if re.search(r'[\u4e00-\u9fff]',term):return term.casefold() in text.casefold()
    return bool(re.search(r'(?<![a-z0-9])'+re.escape(term)+r'(?![a-z])',text,re.I))

def classify(row,source):
    title=row['title']; lead=(row.get('summary') or '')[:350]; text=title+' '+lead
    if not title:return None
    if source.get('terms') and not any(has_term(text,t) for t in source['terms']):return None
    category=source['categories'][0]
    if len(source['categories'])>1:category='phone' if re.search(r'\bpixel\s*(?:\d|fold|phone)',text,re.I) else 'ai'
    if category=='phone':
        if not re.search(r'iphone|smartphone|\bphone\b|galaxy\s*[szamf]\s*\d|pixel\s*(?:\d|fold)|redmagic\s*\d|手机',text,re.I):return None
        if re.search(r'accessor|\bcases?\s+for\b|\bchargers?\b|配件|保护壳|充电器',title,re.I):return None
        if re.search(r'\b(case|cases|charger|cooler|earbuds|headphones|watch|tablet)\b',title,re.I) and not re.search(r'\bphone|iphone|smartphone|手机',title,re.I):return None
    else:
        if not re.search(r'model|gpt|claude|gemini|gemma|grok|qwen|deepseek|mistral|ministral|codestral|devstral|voxtral|flux|stable diffusion|nemotron|cosmos|nova|titan|phi-|mai-|midjourney|模型|minimax|sora|veo|imagen|lyria',text,re.I):return None
        if re.search(r'funding|acqui[rs]|partnership|appoint|economic|system card|safety overview|safeguard|hardware standard|\bplugin\b|journalism|\bpolicy\b|\breport\b|\bhow\b|\bwith\s+(?:gpt|claude|gemini)|融资|收购|任命',title,re.I):return None
        # "GPT" must not match the ChatGPT app name. Model family must be in the
        # headline, or an explicit model release must be described in the lead.
        model_title=re.search(r'(?<![a-z])(?:gpt(?:-|\s|\d)|claude|gemini|gemma|grok|qwen|deepseek|mistral|ministral|codestral|devstral|voxtral|flux|stable diffusion|nemotron|cosmos|nova|titan|phi-|mai-|minimax|sora|veo|imagen|lyria)|\bmodels?\b|模型',title,re.I)
        explicit_lead=re.search(r'(?:introduc\w*|releas\w*|launch\w*)\s+(?:our\s+|the\s+|a\s+|new\s+|latest\s+){0,3}(?:[A-Za-z0-9.-]+\s+){0,3}model\b',lead,re.I)
        if not model_title and not explicit_lead:return None
    preview=r'coming soon|sneak peek|preview|teaser|即将|预告|预览|官宣定档'
    available=r'pre.order|available now|now available|on sale|开售|预售|现已上线|开放 API|开放API'
    launched=r'introduc|announc|launch|releas|unveil|meet\b|发布|推出|登场|正式上线|亮相|\bnew\b'
    if re.search(preview,title,re.I):event_type='preview'
    elif re.search(available,title,re.I):event_type='available'
    elif re.search(launched,title,re.I):event_type='release'
    elif re.search(r'^(?:gpt|claude|gemini|grok|qwen|deepseek|mistral|flux|minimax)[ -]?(?:[a-z]+[ -]){0,2}[vV]?\d',title,re.I) or (category=='ai' and explicit_lead):event_type='signal'
    elif category=='phone' and re.search(r'^(?:the\s+)?(?:pixel\s*\d|iphone\s*\d|honor\s+(?:magic\s*)?\d)',title,re.I):event_type='signal'
    else:return None
    return category,event_type

def domestic_phone_url(url, source):
    if not source.get('enabled') or source.get('region') != 'CN' or 'phone' not in source.get('categories', []):
        return False
    parsed = urlparse(canonical_url(url))
    for prefix in source.get('article_prefixes', []):
        allowed = urlparse(prefix)
        if parsed.scheme == allowed.scheme and parsed.netloc == allowed.netloc and (
            parsed.path == allowed.path or parsed.path.startswith(allowed.path.rstrip('/') + '/')
        ):
            return True
    return False


def filter_domestic_phones(items, sources):
    by_id = {s['id']: s for s in sources}
    return [item for item in items if item.get('category') != 'phone' or any(
        domestic_phone_url(item.get('url', ''), by_id.get(sid, {})) for sid in item.get('source_ids', [])
    )]


def normalize(row,source,catalog,checked_at):
    result=classify(row,source)
    if not result:return None
    category,event_type=result
    if category == 'phone' and not domestic_phone_url(row.get('url', ''), source):return None
    entries=[e for e in catalog if e['id'] in source['catalog_ids'] and e['category']==category]
    matched=[e for e in entries if any(has_term(row['title'],a) for a in e['aliases'])]
    if not matched:matched=entries[:1]
    if not matched:return None
    url=canonical_url(row['url'])
    if not url:return None
    region='中国' if source.get('region')=='CN' else '全球 / 原文地区'
    return dict(id=hashlib.sha256(url.encode()).hexdigest()[:20],category=category,event_type=event_type,
       title=row['title'],summary=row.get('summary','')[:420],url=url,
       published_at=row.get('published_at'),updated_at=row.get('updated_at'),first_seen_at=checked_at,
       source_ids=[source['id']],source_name=source['name'],catalog_ids=[e['id'] for e in matched],
       vendor=matched[0]['vendor'],family=matched[0]['family'],region=region,
       confidence='rule',evidence='依据官方标题与摘要规则筛选，发布阶段以原文为准')

def merge_items(previous,current,now,retention_days=180):
    by_url={}
    for item in previous+current:
        key=canonical_url(item['url'])
        if not key:continue
        if key in by_url:
            old=by_url[key]
            item={**old,**item,'first_seen_at':old['first_seen_at'],
                  'source_ids':sorted(set(old['source_ids']+item['source_ids']))}
        by_url[key]=item
    result=[]
    for item in by_url.values():
        # Unknown publication dates remain explicitly unknown, never rewritten to collection time.
        timestamp=parse_date(item.get('published_at') or item.get('first_seen_at'))
        if not timestamp:continue
        age=(now-datetime.fromisoformat(timestamp)).total_seconds()/86400
        if age < -1 or age>retention_days:continue
        result.append(item)
    # Exact headline syndication within the same vendor, region and UTC day.
    # Different stages and dates stay separate; all original links are retained.
    events={}
    for item in result:
        signature=(item.get('category'),item.get('vendor') or item['url'],item.get('region'),item.get('event_type'),
                   (item.get('published_at') or item['url'])[:10],
                   re.sub(r'\W+','',item['title']).casefold())
        if signature in events:
            old=events[signature]
            old['source_ids']=sorted(set(old['source_ids']+item['source_ids']))
            old['related_urls']=sorted(set(old.get('related_urls',[old['url']])+item.get('related_urls',[item['url']])))
            if len(item.get('summary',''))>len(old.get('summary','')):old['summary']=item['summary']
        else:events[signature]=item
    return sorted(events.values(),key=lambda x:x.get('published_at') or '',reverse=True)
