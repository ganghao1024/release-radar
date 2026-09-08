"""Build configured source inventory from the full catalog and audited adapters."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def make_sources(catalog):
    sources=[]
    def add(id,name,url,kind,vendors,categories,pattern=None,note='',terms=None):
        ids=[x['id'] for x in catalog if x['vendor'] in vendors and x['category'] in categories]
        sources.append(dict(id=id,name=name,url=url,kind=kind,enabled=True,catalog_ids=ids,
                            categories=categories,pattern=pattern,note=note,terms=terms or []))
    add('apple-cn','Apple 中国 Newsroom','https://www.apple.com/cn/newsroom/rss-feed.rss','rss',['Apple'],['phone'],note='中国地区发布；仅筛选 iPhone。',terms=['iPhone'])
    add('apple-global','Apple 全球 Newsroom','https://www.apple.com/newsroom/rss-feed.rss','rss',['Apple'],['phone'],note='全球发布，与中国地区公告分别保留。',terms=['iPhone'])
    add('samsung','Samsung Global Newsroom','https://news.samsung.com/global/feed/rss','rss',['Samsung'],['phone'],note='全站新闻，需要筛选手机；部分网络可能超时。',terms=['Galaxy S','Galaxy Z','Galaxy A','Galaxy M','Galaxy F','smartphone'])
    add('google','Google 官方博客','https://blog.google/rss/','rss',['Google','Google DeepMind'],['phone','ai'],note='全站 RSS，分别识别 Pixel 手机和 AI 模型。',terms=['Pixel','Gemini','Gemma','Imagen','Veo','Lyria'])
    add('pixel','Google Pixel 专栏','https://blog.google/products-and-platforms/devices/pixel/rss/','rss',['Google'],['phone'],note='Pixel 专栏 RSS；排除耳机、手表和使用教程。',terms=['Pixel'])
    add('deepmind','Google DeepMind','https://deepmind.google/blog/rss.xml','rss',['Google DeepMind'],['ai'],note='模型、研究与科学动态，过滤普通研究文章。')
    add('openai','OpenAI News','https://openai.com/news/rss.xml','rss',['OpenAI'],['ai'])
    add('qwen','Qwen 官方技术博客','https://qwenlm.github.io/blog/index.xml','rss',['阿里巴巴'],['ai'],note='官方博客存量订阅；若停止更新，页面会显示最近文章时间。')
    add('nothing','Nothing 官方新闻','https://nothing.tech/blogs/news.atom','rss',['Nothing'],['phone'],terms=['Phone','CMF'])
    add('redmagic','REDMAGIC 官方新闻','https://global.redmagic.gg/blogs/news.atom','rss',['努比亚'],['phone'],terms=['REDMAGIC','Red Magic','phone'])
    add('honor','HONOR 全球新闻','https://www.honor.com/global/news/','html',['荣耀'],['phone'],r'/global/news/(?!archive)[^/?#]+/?$',note='全球官网公告；国内与全球上市时间可能不同。',terms=['HONOR','Magic','phone'])
    add('apple-ml','Apple Machine Learning','https://machinelearning.apple.com/rss.xml','rss',['Apple'],['ai'],note='研究文章较多；仅保留明确的模型发布线索。')
    add('anthropic','Anthropic News','https://www.anthropic.com/news','html',['Anthropic'],['ai'],r'/(?:news/[^/?#]+|claude-[^/?#]+)$',note='解析官方公告和文章元数据；不是原生 RSS。')
    add('deepseek','DeepSeek 更新公告','https://api-docs.deepseek.com/updates','html',['DeepSeek'],['ai'],r'/news/[^/?#]+/?$',note='从文档更新索引发现官方发布公告。')
    add('mistral','Mistral AI News','https://mistral.ai/news','html',['Mistral AI'],['ai'],r'/news/[^/?#]+/?$')
    add('xai','xAI News','https://x.ai/news','html',['xAI'],['ai'],r'/news/[^/?#]+/?$')
    add('minimax','MiniMax News','https://www.minimax.io/news','html',['MiniMax'],['ai'],r'/news/[^/?#]+/?$')
    add('nvidia','NVIDIA 官方博客','https://blogs.nvidia.com/feed/','rss',['NVIDIA'],['ai'],terms=['Nemotron','Cosmos'],note='只匹配模型家族，不收录普通 GPU 发布。')
    add('aws','AWS 官方博客','https://aws.amazon.com/blogs/aws/feed/','rss',['Amazon / AWS'],['ai'],terms=['Amazon Nova','Amazon Titan'],note='只匹配 Amazon 自有模型，排除普通云服务新闻。')
    add('microsoft','Microsoft Research','https://www.microsoft.com/en-us/research/feed/','rss',['Microsoft'],['ai'],terms=['Phi-','Phi ','MAI-'])
    add('midjourney','Midjourney Updates','https://updates.midjourney.com/rss/','rss',['Midjourney'],['ai'])
    add('stability','Stability AI News','https://stability.ai/news-updates?format=rss','rss',['Stability AI'],['ai'])
    add('bfl','Black Forest Labs 公告','https://bfl.ai/announcements','html',['Black Forest Labs'],['ai'],r'/announcements/[^/?#]+/?$')
    covered={i for s in sources for i in s['catalog_ids']}
    for entry in catalog:
        if entry['id'] in covered: continue
        # Group exactly shared official entry URLs; do not invent RSS endpoints.
        existing=next((s for s in sources if s['url']==entry['official_url'] and not s['enabled']),None)
        if existing:
            existing['catalog_ids'].append(entry['id']); continue
        sources.append(dict(id='candidate-'+hashlib.sha1(entry['official_url'].encode()).hexdigest()[:10],
          name=entry['vendor']+' · '+entry['family'],url=entry['official_url'],kind='candidate',enabled=False,
          catalog_ids=[entry['id']],categories=[entry['category']],pattern=None,terms=[],
          note='官方入口候选；尚未完成入口有效性、自动采集适配和更新覆盖验证，不计入运行中数据源。'))
    return sources

if __name__=='__main__':
    catalog=json.loads((ROOT/'config/catalog.json').read_text(encoding='utf-8'))
    sources=make_sources(catalog)
    (ROOT/'config/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(sources)} sources, {sum(s["enabled"] for s in sources)} enabled')
