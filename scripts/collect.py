"""Fetch official sources, retain previous records, publish explicit health metadata."""
from __future__ import annotations
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime,timezone
from urllib.parse import urljoin,urlparse

ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'.cache/python').exists():sys.path.insert(0,str(ROOT/'.cache/python'))
sys.path.insert(0,str(ROOT))
import requests
from bs4 import BeautifulSoup
from scripts.core import clean_text,parse_date,parse_feed,normalize,merge_items,now_iso,canonical_url

HEADERS={'User-Agent':'ReleaseRadar/1.0 (official public announcements; hourly polling)','Accept':'application/rss+xml,application/atom+xml,application/xml,text/html;q=0.9,*/*;q=0.5'}

def fetch(url):
    error=None
    for attempt in range(2):
        try:
            with requests.get(url,headers=HEADERS,timeout=(8,22),stream=True) as r:
                r.raise_for_status()
                content=bytearray()
                for chunk in r.iter_content(65536):
                    content.extend(chunk)
                    if len(content)>8_000_000:raise ValueError('Response exceeds 8 MB')
                return bytes(content),r.url
        except requests.RequestException as exc:
            error=exc
            if attempt==0:time.sleep(1)
    raise error

def walk_json(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from walk_json(child)
    elif isinstance(value,list):
        for child in value:yield from walk_json(child)

def article_data(content,url,fallback_title='',fallback_date=None):
    soup=BeautifulSoup(content,'html.parser')
    def meta(*names):
        for name in names:
            tag=soup.find('meta',attrs={'property':name}) or soup.find('meta',attrs={'name':name})
            if tag and tag.get('content'):return tag['content']
    h1=soup.find('h1')
    title=clean_text(h1.get_text(' ',strip=True) if h1 else meta('og:title') or fallback_title)
    date=parse_date(meta('article:published_time','datePublished','date','pubdate'))
    summary=clean_text(meta('description','og:description') or '')
    for script in soup.find_all('script',attrs={'type':'application/ld+json'}):
        try:
            for obj in walk_json(json.loads(script.string or script.get_text())):
                if obj.get('datePublished'):date=date or parse_date(obj['datePublished'])
                if obj.get('headline') and not title:title=clean_text(obj['headline'])
        except (ValueError,TypeError):continue
    main=soup.find('main') or soup.find('article') or soup
    if not date:
        for tag in main.find_all('time'):
            date=parse_date(tag.get('datetime') or tag.get_text(' ',strip=True))
            if date:break
    if not date:date=parse_date(main.get_text(' ',strip=True)[:2200]) or fallback_date
    if not summary:
        paragraphs=[clean_text(p.get_text(' ',strip=True)) for p in main.find_all('p')]
        summary=' '.join(p for p in paragraphs if len(p)>50)[:900]
    return dict(title=title,url=canonical_url(url),published_at=date,summary=summary[:900])

def parse_html_source(content,url,source):
    soup=BeautifulSoup(content,'html.parser');links={}
    for a in soup.find_all('a',href=True):
        target=canonical_url(urljoin(url,a['href']))
        if not target or urlparse(target).hostname!=urlparse(url).hostname:continue
        if not re.search(source['pattern'],urlparse(target).path):continue
        text=a.get_text(' ',strip=True)
        # Prefer a heading inside the article card, not navigation labels.
        heading=a.find(re.compile('^h[1-6]$'))
        title=heading.get_text(' ',strip=True) if heading else text
        if len(title)<8:continue
        links.setdefault(target,(clean_text(title),parse_date(text)))
    if not links:raise ValueError('No article links matched; adapter needs review (possibly dynamic page)')
    # News indices are usually newest-first. Bound detail fetches per domain.
    results=[];errors=0
    for target,(title,date) in list(links.items())[:16]:
        try:
            data,final_url=fetch(target)
            results.append(article_data(data,final_url,title,date))
        except Exception:
            errors+=1
            # Retain sourced index title/date, but never fabricate a publication date.
            results.append(dict(title=title,url=target,published_at=date,summary=''))
    return results,errors

def collect_source(source,catalog,checked_at):
    start=time.monotonic()
    status=dict(id=source['id'],checked_at=checked_at,status='error',raw_count=0,matched_count=0)
    try:
        content,final_url=fetch(source['url'])
        if source['kind']=='rss':rows=parse_feed(content,final_url);detail_errors=0
        else:rows,detail_errors=parse_html_source(content,final_url,source)
        if not rows:raise ValueError('No entries parsed from source')
        # Atom feeds such as Apple sometimes omit published dates. Resolve the
        # official article date for matching records, rather than using updated.
        enrich=0
        for row in rows:
            if not row.get('published_at') and enrich<8 and normalize(row,source,catalog,checked_at):
                enrich+=1
                try:
                    detail,detail_url=fetch(row['url'])
                    info=article_data(detail,detail_url,row['title'])
                    row['published_at']=info['published_at']
                    if not row.get('summary'):row['summary']=info['summary']
                except Exception:detail_errors+=1
        items=[item for row in rows if (item:=normalize(row,source,catalog,checked_at))]
        dates=[r['published_at'] for r in rows if r.get('published_at')]
        status.update(status='partial' if detail_errors else 'ok',raw_count=len(rows),matched_count=len(items),
            newest_article_at=max(dates) if dates else None,final_url=final_url,
            detail_errors=detail_errors,error=None if not detail_errors else f'{detail_errors} article detail requests failed; index metadata retained')
    except Exception as exc:
        items=[]
        # Public diagnostic contains no request headers, tokens or environment variables.
        status['error']=str(exc).split('\n')[0][:240]
    status['duration_seconds']=round(time.monotonic()-start,2)
    return items,status

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only',help='Comma-separated source IDs');args=parser.parse_args()
    catalog=json.loads((ROOT/'config/catalog.json').read_text(encoding='utf-8'))
    sources=json.loads((ROOT/'config/sources.json').read_text(encoding='utf-8'))
    config=json.loads((ROOT/'config/site.json').read_text(encoding='utf-8'))
    enabled=[s for s in sources if s['enabled'] and (not args.only or s['id'] in args.only.split(','))]
    checked=now_iso(); cache=ROOT/'.cache/state.json'; output=ROOT/'data/latest.json'
    prior={}
    for path in [cache,output]:
        if path.exists():
            try:prior=json.loads(path.read_text(encoding='utf-8'));break
            except (ValueError,OSError):pass
    current=[]; statuses=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        pending={pool.submit(collect_source,s,catalog,checked):s for s in enabled}
        for future in concurrent.futures.as_completed(pending):
            items,status=future.result();current.extend(items);statuses.append(status)
            print(f'{status["id"]}: {status["status"]} / {status["raw_count"]} read / {status["matched_count"]} matched',flush=True)
    checked_ids={s['id'] for s in statuses}
    if args.only:statuses.extend(s for s in prior.get('source_status',[]) if s['id'] not in checked_ids)
    # Reapply current rules to historical records after a classifier correction.
    from scripts.core import classify
    source_map={s['id']:s for s in sources}
    history=[]
    for old in prior.get('items',[]):
        matched=next((result for sid in old['source_ids'] if sid in source_map and (result:=classify(old,source_map[sid]))),None)
        if matched:history.append({**old,'category':matched[0],'event_type':matched[1]})
    from scripts.core import filter_domestic_phones
    items=filter_domestic_phones(merge_items(history,current,datetime.now(timezone.utc),config['retention_days']),sources)
    success=sum(s['status'] in ['ok','partial'] for s in statuses if s['id'] in checked_ids)
    all_active={s['id'] for s in sources if s['enabled']}
    all_success=sum(s['status'] in ['ok','partial'] for s in statuses if s['id'] in all_active)
    payload=dict(schema_version=1,generated_at=checked,last_success_at=checked if success else prior.get('last_success_at'),
       collection_status='ok' if all_success==len(all_active) else 'partial' if all_success else 'error',
       items=items,source_status=sorted(statuses,key=lambda s:s['id']),catalog=catalog,sources=sources,site=config)
    for path in [cache,output]:
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(path)
    print(f'{len(items)} retained records; {success}/{len(enabled)} sources readable',flush=True)
    if not success:sys.exit('All selected sources failed; previous records retained locally, publication aborted.')

if __name__=='__main__':main()
