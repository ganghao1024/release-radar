"""Build a portable static site and reproducible Markdown documentation."""
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from email.utils import format_datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KIND={'rss':'官方 RSS / Atom','html':'官方网页解析','candidate':'候选官方入口（未适配）'}
STATUS={'ok':'成功','partial':'部分成功','error':'失败','pending':'未验证','candidate':'未接入'}

def write_docs(data):
    docs=ROOT/'docs';docs.mkdir(exist_ok=True)
    catalog=data['catalog'];sources=data['sources'];statuses={s['id']:s for s in data.get('source_status',[])}
    lines=['# 厂商 → 品牌／模型家族 → 别名 → 官方来源','',
      '本文件由 `config/catalog.json` 和 `config/sources.json` 自动生成。品牌关系用于信息订阅，不构成法律股权说明。',
      '官方入口是采集候选目录；“有官网”不等于“有 RSS”，不代表已验证所有域名、持续发布新品或完成自动采集。',
      '短别名（如 Step、Yi、Nova）必须限制在对应厂商来源内匹配；不在全网单独匹配。',
      f'目录共 **{len(catalog)}** 条关系，其中手机 **{sum(e["category"]=="phone" for e in catalog)}** 条、AI **{sum(e["category"]=="ai" for e in catalog)}** 条。','']
    for category,title in [('phone','手机'),('ai','AI 模型（含科研机构、图像、视频、音频）')]:
        lines.extend([f'## {title}','','| 厂商 | 品牌／模型家族 | 别名 | 官方入口 | 自动采集源 |','|---|---|---|---|---|'])
        for e in catalog:
            if e['category']!=category:continue
            active=[s['name'] for s in sources if s['enabled'] and e['id'] in s['catalog_ids']]
            lines.append(f'| {e["vendor"]} | {e["family"]} | {"、".join(e["aliases"])} | [官方入口]({e["official_url"]}) | {"；".join(active) or "候选，未接入"} |')
        lines.append('')
    (docs/'厂商与品牌关系.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=['# 数据源列表与运行状态','',f'本次检查时间（UTC）：{data.get("generated_at","未运行")}。',
      '由配置和实际采集结果生成；HTTP 200 但无法解析文章会记为失败，不会记作成功。成功且匹配数为 0 表示可读取，但本批文章无符合规则的发布线索。',
      'RSS 通常只提供最近若干篇文章，网页解析每次最多读取 16 个详情；首次抓取不保证补全历史。部分源可读不代表全目录覆盖。',
      '来源故障时保留已采集记录；全部来源故障会令 Actions 失败并保留上次线上部署。','',
      '## 已配置自动采集的来源','','| ID | 来源及地址 | 方式 | 本次状态 | 原始/匹配数 | 最近文章（UTC） | 说明 |','|---|---|---|---|---|---|---|']
    for s in sources:
        if not s['enabled']:continue
        health=statuses.get(s['id'],{});state=health.get('status','pending')
        note='；'.join(str(x) for x in [s.get('note'),health.get('error')] if x).replace('|','/').replace('\n',' ')
        lines.append(f'| {s["id"]} | [{s["name"]}]({s["url"]}) | {KIND[s["kind"]]} | {STATUS[state]} | {health.get("raw_count","—")} / {health.get("matched_count","—")} | {health.get("newest_article_at") or "未知"} | {note} |')
    lines.extend(['','## 候选官方入口（没有启用自动采集）','','这些条目保留完整关注范围；不是经过验证的原生 RSS。后续需要核实网址、适配解析器并进行实际抓取验收。','','| 厂商／家族 | 官方入口 | 状态 |','|---|---|---|'])
    for s in sources:
        if not s['enabled']:lines.append(f'| {s["name"]} | [入口]({s["url"]}) | 待核实、待适配 |')
    lines.extend(['','## 新增或修复来源','','1. 在 `config/catalog.json` 添加厂商、家族和来源范围内的别名。','2. 在 `config/sources.json` 配置 RSS，或 HTML 文章链接正则；只接入官方公开来源。','3. 执行 `python scripts/collect.py --only SOURCE_ID`，检查原始条数、文章日期、匹配结果和错误。','4. 执行 `python scripts/build.py`，检查网页来源页及本文件，不能只凭 HTTP 200 判定成功。','5. 推送代码，确认 GitHub Actions 和 Pages 实际部署成功。','', '采集数据只包含标题、短摘要、日期和官方链接；规则判定是发布线索，最终发布阶段以原文为准。'])
    (docs/'数据源列表.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def rss(data,destination):
    root=ET.Element('rss',version='2.0');ch=ET.SubElement(root,'channel')
    base=data['site'].get('url') or 'https://example.invalid/'
    for key,value in [('title','发布雷达 · 手机与 AI 模型'),('link',base),('description','经过规则筛选的官方发布线索；阶段以原文为准。'),('language','zh-cn')]:ET.SubElement(ch,key).text=value
    for entry in data['items'][:100]:
        item=ET.SubElement(ch,'item')
        for key,value in [('title',entry['title']),('link',entry['url']),('description',entry['summary']),('category',entry['category'])]:ET.SubElement(item,key).text=value
        ET.SubElement(item,'guid',isPermaLink='true').text=entry['url']
        if entry.get('published_at'):ET.SubElement(item,'pubDate').text=format_datetime(datetime.fromisoformat(entry['published_at']).astimezone(timezone.utc))
    ET.indent(root);ET.ElementTree(root).write(destination,encoding='utf-8',xml_declaration=True)

def main():
    file=ROOT/'data/latest.json'
    if not file.exists():sys.exit('Run python scripts/collect.py before building; no fabricated seed data is supplied.')
    data=json.loads(file.read_text(encoding='utf-8'))
    data['catalog']=json.loads((ROOT/'config/catalog.json').read_text(encoding='utf-8'))
    data['sources']=json.loads((ROOT/'config/sources.json').read_text(encoding='utf-8'))
    data['site']=json.loads((ROOT/'config/site.json').read_text(encoding='utf-8'))
    write_docs(data)
    dest=ROOT/'dist';dest.mkdir(exist_ok=True)
    for file in (ROOT/'web').iterdir():
        if file.is_file():shutil.copyfile(file,dest/file.name)
    (dest/'data').mkdir(exist_ok=True)
    (dest/'data/latest.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    shutil.copytree(ROOT/'docs',dest/'docs',dirs_exist_ok=True)
    (dest/'.nojekyll').touch();rss(data,dest/'feed.xml')
    print(f'Built dist: {len(data["items"])} sourced records, {len(data["catalog"])} catalog entries')

if __name__=='__main__':main()
