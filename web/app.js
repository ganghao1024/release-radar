'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl = value => {try {const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:'#';}catch{return '#';}};
const labels={release:'正式发布',preview:'预览 / 预告',available:'上线 / 开售',signal:'待核实线索'};
const state={data:null,view:'news',category:'all',vendor:'all',event:'all',range:'30',query:'',limit:20};
const date = value => value ? new Date(value).toLocaleDateString('zh-CN',{month:'2-digit',day:'2-digit'}) : '日期未提供';
const dateLong = value => value ? new Date(value).toLocaleString('zh-CN',{hour12:false}) : '未知';
const glyph = name => String(name).replace(/[^\p{L}\p{N}]/gu,'').slice(0,2).toUpperCase();
function metric(icon,title,count,unit){return `<div class="metric"><span class="metric-icon" aria-hidden="true">${icon}</span><div><div class="metric-label">${title}</div><div class="metric-value">${count}<small>${unit}</small></div></div></div>`;}
function within(item,days){return item.published_at && Date.now()-new Date(item.published_at).getTime()<=days*86400000 && new Date(item.published_at).getTime()<=Date.now()+86400000;}
function matches(item){return (state.category==='all'||item.category===state.category)&&(state.vendor==='all'||item.vendor===state.vendor)&&(state.event==='all'||item.event_type===state.event)&&(state.range==='all'||within(item,Number(state.range)))&&(!state.query||[item.title,item.summary,item.vendor,item.family].join(' ').toLocaleLowerCase().includes(state.query.toLocaleLowerCase()));}
function external(url,content,attrs=''){return `<a href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer" ${attrs}>${content}</a>`;}
function card(item){return `<article class="news-card"><div class="card-meta"><span class="vendor-glyph" aria-hidden="true">${esc(glyph(item.vendor))}</span><span>${esc(item.vendor)}</span><span class="card-category ${item.category}">${item.category==='phone'?'手机':'AI'}</span><time ${item.published_at?`datetime="${esc(item.published_at)}"`:''} title="${esc(dateLong(item.published_at))}">${esc(date(item.published_at))}</time></div><h3>${external(item.url,esc(item.title))}</h3><p>${esc(item.summary||'官方公告已收录，详情请查看原文。')}</p><div class="card-bottom"><span class="pill ${item.event_type}" title="${esc(item.evidence)}">${labels[item.event_type]||'发布线索'}</span>${external(item.url,`${esc(item.source_name)} ↗`,'aria-label="查看官方原文"')}</div></article>`;}
function renderNews(){
  const items=state.data.items.filter(matches);
  $('result-count').textContent=`${items.length} 条动态`;
  $('news-grid').innerHTML=items.length?items.slice(0,state.limit).map(card).join(''):'<div class="empty"><strong>这个范围内还没有发布信号</strong><p>试试其他厂商或“全部归档”。未知发布日期的记录只在全部归档中显示。</p><button class="secondary-button" id="empty-reset">重置筛选</button></div>';
  $('empty-reset')?.addEventListener('click',reset);
  $('load-more').hidden=items.length<=state.limit;
  for(const button of document.querySelectorAll('[data-category]'))button.classList.toggle('selected',button.dataset.category===state.category);
  for(const button of document.querySelectorAll('[data-vendor]'))button.classList.toggle('selected',button.dataset.vendor===state.vendor);
  for(const category of ['all','phone','ai'])$('count-'+category).textContent=state.data.items.filter(i=>(category==='all'||i.category===category)&&(state.range==='all'||within(i,Number(state.range)))).length;
}
function reset(){Object.assign(state,{category:'all',vendor:'all',event:'all',range:'30',query:'',limit:20});$('search').value='';$('vendor').value='all';$('event').value='all';$('range').value='30';renderNews();}
function setView(view){
  if(!['news','sources','catalog'].includes(view))view='news';
  state.view=view;history.replaceState(null,'','#'+view);
  for(const name of ['news','sources','catalog'])$(name+'-view').hidden=name!==view;
  for(const button of document.querySelectorAll('[data-view]'))button.classList.toggle('active',button.dataset.view===view);
  const names={news:'发布动态',sources:'官方来源',catalog:'厂商目录'};
  $('breadcrumb-current').textContent=names[view];$('page-title').innerHTML=names[view]+'<span class="title-dot">.</span>';
  $('page-description').textContent={news:'新手机，新模型。从官方公告开始。',sources:'看得见来源，也看得见每一次采集的状态。',catalog:'从厂商到别名，建立完整的关注地图。'}[view];
}
function renderSpotlights(){
  $('spotlights').innerHTML=['phone','ai'].map(category=>{
    const item=state.data.items.find(i=>i.category===category&&i.published_at&&i.event_type!=='signal');
    const label=category==='phone'?'MOBILE · 手机新品':'MODELS · AI 模型';
    if(!item)return `<article class="spotlight ${category}"><div class="channel-label">${label}</div><h3>等待下一次官方发布</h3><p>来源接入状态可在“官方来源”查看。</p></article>`;
    return `<article class="spotlight ${category}"><div class="spot-top"><span class="channel-label">${label}</span><time datetime="${esc(item.published_at)}">${esc(date(item.published_at))}</time></div><h3>${external(item.url,esc(item.title))}</h3><p>${esc(item.summary)}</p><div class="spot-bottom"><span>${esc(item.vendor)} · ${labels[item.event_type]}</span><span class="arrow" aria-hidden="true">↗</span></div></article>`;
  }).join('');
}
function renderSources(){
  const data=state.data,enabled=data.sources.filter(s=>s.enabled),health=new Map(data.source_status.map(s=>[s.id,s]));
  const readable=enabled.filter(s=>['ok','partial'].includes(health.get(s.id)?.status)).length;
  $('source-metrics').innerHTML=metric('◉','本次可读取',readable,`/ ${enabled.length} 个自动采集源`)+metric('◷','需要检查',enabled.length-readable,'失败或尚未验证')+metric('▦','候选官方入口',data.sources.length-enabled.length,'未计入自动采集');
  const header='<div class="source-row header"><span>来源 / 方式</span><span>运行状态</span><span>读取 / 匹配</span><span>最近文章 / 说明</span></div>';
  function row(s){const h=health.get(s.id),status=s.enabled?(h?.status||'pending'):'candidate';const name={ok:'读取成功',partial:'部分成功',error:'读取失败',pending:'尚未验证',candidate:'候选入口'}[status];
    return `<div class="source-row"><div>${external(s.url,esc(s.name)+' ↗')}<small>${s.kind==='rss'?'官方 RSS / Atom':s.kind==='html'?'官方网页解析':'待核实、待适配'}</small></div><div><span class="health ${status}">${name}</span><small>${h?'检查 '+date(h.checked_at):'未启用'}</small></div><div>${h?`${h.raw_count} / ${h.matched_count}`:'—'}<small>${h?.newest_article_at?'最近 '+date(h.newest_article_at):'日期未知'}</small></div><div class="note">${esc(s.note||'官方发布内容，按规则筛选。')}${h?.error?`<details><summary>查看诊断</summary>${esc(h.error)}</details>`:''}</div></div>`;
  }
  $('source-list').innerHTML=`<section class="source-section"><h2>自动采集 · ${enabled.length}</h2><div class="source-table">${header}${enabled.map(row).join('')}</div></section><section class="source-section"><h2>候选入口 · ${data.sources.length-enabled.length}</h2><div class="source-table">${data.sources.filter(s=>!s.enabled).map(row).join('')}</div></section>`;
}
function renderCatalog(){
  const query=$('catalog-search').value.trim().toLocaleLowerCase();
  const entries=state.data.catalog.filter(e=>[e.vendor,e.family,...e.aliases].join(' ').toLocaleLowerCase().includes(query));
  $('catalog-list').innerHTML=['phone','ai'].map(category=>{
    const list=entries.filter(e=>e.category===category);
    return `<section class="catalog-group"><h2>${category==='phone'?'手机品牌':'AI 模型厂商与研究机构'} · ${list.length}</h2>${list.map(e=>{
      const sources=state.data.sources.filter(s=>s.enabled&&s.catalog_ids.includes(e.id));
      return `<details class="catalog-entry"><summary>${esc(e.vendor)}<span class="family">${esc(e.family)}</span></summary><div class="catalog-detail"><div>${e.aliases.map(a=>`<span class="alias">${esc(a)}</span>`).join('')}</div><p>${external(e.official_url,'官方入口 ↗')}</p><div>自动采集：${sources.length?sources.map(s=>external(s.url,esc(s.name))).join(' · '):'尚未接入，保留在候选目录'}</div></div></details>`;
    }).join('')}</section>`;
  }).join('');
}
function init(){
  const d=state.data,enabled=d.sources.filter(s=>s.enabled).length,ok=d.source_status.filter(s=>['ok','partial'].includes(s.status)).length;
  const recent=d.items.filter(i=>within(i,30));
  $('metrics').innerHTML=metric('▯','手机新品',recent.filter(i=>i.category==='phone').length,'条 · 近 30 天')+metric('✳','AI 模型动态',recent.filter(i=>i.category==='ai').length,'条 · 近 30 天')+metric('◉','官方采集源',ok,`/ ${enabled} 个本次可读`);
  $('nav-count').textContent=d.items.length;$('today').textContent=new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'long',day:'numeric'});
  $('updated').textContent='最近检查 '+dateLong(d.generated_at);
  const ageHours=(Date.now()-new Date(d.generated_at).getTime())/3600000;
  $('freshness').textContent=`每小时检查 · ${d.collection_status==='ok'?'本次采集正常':'部分来源需要检查'}`;
  if(ageHours>3||d.collection_status==='error'){
    $('stale-banner').hidden=false;$('stale-banner').textContent=ageHours>3?`数据已超过 ${Math.floor(ageHours)} 小时未更新。当前显示上次采集结果，请检查 GitHub Actions 运行状态。`:'本次来源不可读，正在显示此前采集记录。';
  }
  const vendorCounts=new Map();for(const i of d.items)vendorCounts.set(i.vendor,(vendorCounts.get(i.vendor)||0)+1);
  $('quick-brands').innerHTML=[...vendorCounts].sort((a,b)=>b[1]-a[1]).slice(0,8).map(([v,n])=>`<button class="quick-brand" data-vendor="${esc(v)}"><span class="vendor-glyph">${esc(glyph(v))}</span>${esc(v)}<span class="number">${n}</span></button>`).join('');
  $('vendor').innerHTML='<option value="all">全部厂商</option>'+[...vendorCounts.keys()].sort((a,b)=>a.localeCompare(b,'zh-CN')).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
  for(const button of document.querySelectorAll('[data-vendor]'))button.addEventListener('click',()=>{state.vendor=button.dataset.vendor;state.category='all';state.range='all';state.limit=20;$('vendor').value=state.vendor;$('range').value='all';setView('news');renderNews();});
  $('footer-count').textContent=`${d.catalog.length} 条品牌关系`;
  if(d.site.repository){$('repo-link').href=safeUrl(d.site.repository);$('repo-link').hidden=false;}
  renderSpotlights();renderNews();renderSources();renderCatalog();setView(location.hash.slice(1)||'news');
  $('loading').hidden=true;$('workspace').hidden=false;
}
async function load(){
  $('loading').hidden=false;$('error').hidden=true;$('workspace').hidden=true;
  try {const response=await fetch('./data/latest.json',{cache:'no-cache'});if(!response.ok)throw new Error(`HTTP ${response.status}`);const data=await response.json();if(!Array.isArray(data.items)||!Array.isArray(data.sources)||!Array.isArray(data.catalog))throw new Error('数据格式不完整');state.data=data;init();}
  catch(error){$('loading').hidden=true;$('error').hidden=false;$('error-message').textContent=`${error.message}。请稍后重试，或通过来源清单直接访问官方公告。`;}
}
for(const button of document.querySelectorAll('[data-view]'))button.addEventListener('click',()=>state.data&&setView(button.dataset.view));
for(const button of document.querySelectorAll('[data-category]'))button.addEventListener('click',()=>{state.category=button.dataset.category;state.limit=20;renderNews();});
for(const id of ['vendor','event','range'])$(id).addEventListener('change',()=>{state[id]=$(id).value;state.limit=20;renderNews();});
$('search').addEventListener('input',()=>{state.query=$('search').value.trim();state.limit=20;renderNews();});
$('catalog-search').addEventListener('input',renderCatalog);$('reset').addEventListener('click',reset);$('load-more').addEventListener('click',()=>{state.limit+=20;renderNews();});$('retry').addEventListener('click',load);
window.addEventListener('hashchange',()=>state.data&&setView(location.hash.slice(1)));
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)&&state.view==='news'){e.preventDefault();$('search').focus();}});
load();
