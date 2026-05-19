# build_index_html.py
# 用途：读取 listening_index.json，把数据内嵌进一个独立的 HTML 筛选页面。
# 这样 HTML 双击即可打开，无需本地服务器（避免浏览器对 file:// 下 fetch 的限制）。
#
# 用法：在本目录（ielts_index/）下运行  python3 build_index_html.py
# 每次更新 listening_index.json 后重跑一次即可刷新 listening_index.html。
import json
d = json.load(open('listening_index.json', encoding='utf-8'))
data_js = json.dumps(d, ensure_ascii=False)

html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>雅思听力分类索引 · 训练筛选器</title>
<style>
  :root {
    --bg:#f4f5f7; --card:#ffffff; --ink:#1f2330; --muted:#6b7280;
    --line:#e3e6ea; --accent:#2f5fe0; --accent-soft:#e8eefc;
    --p1:#d9534f; --p2:#e0922f; --p3:#2f8f5b; --p4:#2f5fe0;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;
    background:var(--bg); color:var(--ink); line-height:1.65; }
  .wrap { max-width:1240px; margin:0 auto; padding:28px 20px 80px; }
  header h1 { font-size:22px; font-weight:700; }
  header p { color:var(--muted); font-size:13px; margin-top:4px; }
  .layout { display:grid; grid-template-columns:260px 1fr; gap:22px; margin-top:22px; align-items:start; }
  .panel { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }
  .sidebar { position:sticky; top:16px; max-height:calc(100vh - 32px); overflow-y:auto; }
  .fgroup { margin-bottom:15px; }
  .fgroup:last-child { margin-bottom:0; }
  .fgroup h3 { font-size:12px; letter-spacing:.04em; color:var(--muted); text-transform:uppercase; margin-bottom:7px; }
  .opt { display:flex; align-items:center; gap:7px; font-size:13.5px; padding:2.5px 0; cursor:pointer; }
  .opt input { cursor:pointer; }
  .opt .cnt { color:var(--muted); font-size:12px; margin-left:auto; }
  .bookgrid { display:grid; grid-template-columns:repeat(4,1fr); gap:4px; }
  .bookgrid .opt { font-size:12.5px; gap:4px; padding:2px 0; }
  .bookgrid .cnt { display:none; }
  .search { width:100%; padding:8px 10px; border:1px solid var(--line); border-radius:8px; font-size:13.5px; }
  .reset { width:100%; margin-top:4px; padding:8px; border:1px solid var(--line); background:#fff;
    border-radius:8px; cursor:pointer; font-size:13px; color:var(--muted); }
  .reset:hover { background:var(--bg); }
  .bar { display:flex; align-items:baseline; gap:10px; margin-bottom:14px; flex-wrap:wrap; }
  .bar .count { font-size:15px; font-weight:600; }
  .bar .hint { font-size:12.5px; color:var(--muted); }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:14px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:15px 16px;
    border-left:4px solid var(--line); }
  .card.p1 { border-left-color:var(--p1); }
  .card.p2 { border-left-color:var(--p2); }
  .card.p3 { border-left-color:var(--p3); }
  .card.p4 { border-left-color:var(--p4); }
  .card .cid { font-size:11.5px; color:var(--muted); font-family:ui-monospace,Menlo,monospace; }
  .card h2 { font-size:15.5px; font-weight:700; margin:3px 0 1px; }
  .card .en { font-size:12.5px; color:var(--muted); margin-bottom:9px; }
  .tags { display:flex; flex-wrap:wrap; gap:5px; margin-bottom:9px; }
  .tag { font-size:11.5px; padding:2px 8px; border-radius:20px; background:var(--bg); color:#46506a; border:1px solid var(--line); }
  .tag.type { background:var(--accent-soft); color:var(--accent); border-color:#d4def8; }
  .tag.scn { background:#fff4e6; color:#b9701f; border-color:#f3e0c4; }
  .tag.sub { background:#eaf6ef; color:#2f7d52; border-color:#cfe9d9; }
  .tag.kw  { background:#fff; color:var(--muted); }
  .tag.warn { background:#fdeaea; color:#c0392b; border-color:#f3c9c9; }
  .summary { font-size:13px; color:#2c3242; }
  .summary.clamp { display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }
  .more { font-size:12px; color:var(--accent); cursor:pointer; margin-top:5px; display:inline-block; }
  audio { width:100%; margin-top:11px; height:34px; }
  .path { font-size:11px; color:var(--muted); font-family:ui-monospace,Menlo,monospace; margin-top:6px; word-break:break-all; }
  .path.partial { color:#b9701f; }
  .empty { padding:40px; text-align:center; color:var(--muted); }
  @media (max-width:820px){ .layout{ grid-template-columns:1fr; } .sidebar{ position:static; max-height:none; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>雅思听力分类索引 · 训练筛选器</h1>
    <p id="meta-line"></p>
  </header>
  <div class="layout">
    <aside class="panel sidebar">
      <div class="fgroup">
        <h3>关键词搜索</h3>
        <input class="search" id="q" placeholder="标题 / 摘要 / 关键词…">
      </div>
      <div class="fgroup" id="f-part"></div>
      <div class="fgroup" id="f-speech"></div>
      <div class="fgroup" id="f-context"></div>
      <div class="fgroup" id="f-scenario"></div>
      <div class="fgroup" id="f-subject"></div>
      <div class="fgroup" id="f-source"></div>
      <div class="fgroup"><h3>书目</h3><div class="bookgrid" id="f-book"></div></div>
      <button class="reset" id="reset">清除全部筛选</button>
    </aside>
    <main>
      <div class="bar">
        <span class="count" id="count"></span>
        <span class="hint">勾选多个条件为「与」关系；同一组内多选为「或」关系</span>
      </div>
      <div class="grid" id="grid"></div>
      <div class="empty" id="empty" style="display:none">没有符合条件的材料，试着放宽筛选。</div>
    </main>
  </div>
</div>
<script>
const DB = ''' + data_js + ''';
const T = DB.taxonomy;
const partFacet = T.type.facets.part_no.values;
const speechFacet = T.type.facets.speech_type.values;
const ctxFacet = T.type.facets.context.values;
const scnFacet = T.scenario.values;
const subFacet = T.subjects.values;
const sqFacet = T.source_quality.values;
document.getElementById('meta-line').textContent =
  DB.meta.scope + ' · 共 ' + DB.meta.total_items + ' 个 Part · 生成于 ' + DB.meta.generated_date;

const state = { part:new Set(), speech:new Set(), context:new Set(),
  scenario:new Set(), subject:new Set(), source:new Set(), book:new Set(), q:'' };

function counts(keyFn){
  const m={};
  DB.items.forEach(it=>{ keyFn(it).forEach(k=>m[k]=(m[k]||0)+1); });
  return m;
}
const cPart=counts(it=>[String(it.type.part_no)]);
const cSpeech=counts(it=>[it.type.speech_type]);
const cCtx=counts(it=>[it.type.context]);
const cScn=counts(it=>[it.scenario]);
const cSub=counts(it=>it.subjects);
const cSrc=counts(it=>[it.source_quality]);
const cBook=counts(it=>[String(it.book)]);

function buildGroup(elId, title, dict, cntMap, stateKey){
  const el=document.getElementById(elId);
  let h='<h3>'+title+'</h3>';
  Object.keys(dict).forEach(k=>{
    h+='<label class="opt"><input type="checkbox" data-g="'+stateKey+'" value="'+k+'">'
      +'<span>'+dict[k]+'</span><span class="cnt">'+(cntMap[k]||0)+'</span></label>';
  });
  el.innerHTML=h;
}
buildGroup('f-part','类型 · Part 序号',partFacet,cPart,'part');
buildGroup('f-speech','类型 · 话语形式',speechFacet,cSpeech,'speech');
buildGroup('f-context','类型 · 语境',ctxFacet,cCtx,'context');
buildGroup('f-scenario','场景',scnFacet,cScn,'scenario');
buildGroup('f-subject','话题 / 学科',subFacet,cSub,'subject');
buildGroup('f-source','原文完整度',sqFacet,cSrc,'source');

// book filter 1..20
(function(){
  const el=document.getElementById('f-book');
  let h='';
  for(let b=1;b<=20;b++){
    h+='<label class="opt"><input type="checkbox" data-g="book" value="'+b+'">'
      +'<span>剑'+b+'</span></label>';
  }
  el.innerHTML=h;
})();

document.querySelectorAll('input[type=checkbox]').forEach(cb=>{
  cb.addEventListener('change',e=>{
    const g=e.target.dataset.g, v=e.target.value;
    e.target.checked?state[g].add(v):state[g].delete(v);
    render();
  });
});
document.getElementById('q').addEventListener('input',e=>{ state.q=e.target.value.trim().toLowerCase(); render(); });
document.getElementById('reset').addEventListener('click',()=>{
  ['part','speech','context','scenario','subject','source','book'].forEach(k=>state[k].clear());
  state.q=''; document.getElementById('q').value='';
  document.querySelectorAll('input[type=checkbox]').forEach(cb=>cb.checked=false);
  render();
});

function match(it){
  if(state.part.size && !state.part.has(String(it.type.part_no))) return false;
  if(state.speech.size && !state.speech.has(it.type.speech_type)) return false;
  if(state.context.size && !state.context.has(it.type.context)) return false;
  if(state.scenario.size && !state.scenario.has(it.scenario)) return false;
  if(state.subject.size && !it.subjects.some(s=>state.subject.has(s))) return false;
  if(state.source.size && !state.source.has(it.source_quality)) return false;
  if(state.book.size && !state.book.has(String(it.book))) return false;
  if(state.q){
    const hay=(it.title+' '+it.title_zh+' '+it.summary_zh+' '+it.keywords.join(' ')).toLowerCase();
    if(!hay.includes(state.q)) return false;
  }
  return true;
}

function card(it){
  const partLabel='P'+it.type.part_no;
  const tags=[];
  tags.push('<span class="tag type">'+partLabel+' · '+speechFacet[it.type.speech_type]+' · '+ctxFacet[it.type.context]+'</span>');
  tags.push('<span class="tag scn">'+scnFacet[it.scenario]+'</span>');
  it.subjects.forEach(s=>tags.push('<span class="tag sub">'+subFacet[s]+'</span>'));
  it.keywords.forEach(k=>tags.push('<span class="tag kw">'+k+'</span>'));
  if(it.source_quality!=='full') tags.push('<span class="tag warn">'+sqFacet[it.source_quality]+'</span>');
  const a=it.audio;
  let audioHtml='', pathHtml='';
  if(a.part_file){
    audioHtml='<audio controls preload="none" src="../'+a.part_file+'"></audio>';
    pathHtml='<div class="path">'+a.part_file+'</div>';
  } else if(a.full_test_file){
    audioHtml='<audio controls preload="none" src="../'+a.full_test_file+'"></audio>';
    pathHtml='<div class="path partial">⚠ 该 Part 无单独切分音频，下面是整套 Test 音频：'+a.full_test_file+'</div>';
  } else {
    pathHtml='<div class="path partial">（无音频文件）</div>';
  }
  return '<div class="card p'+it.type.part_no+'">'
    +'<div class="cid">'+it.id+' &nbsp;|&nbsp; 剑'+it.book+' Test'+it.test+' Part'+it.part+'</div>'
    +'<h2>'+it.title_zh+'</h2>'
    +'<div class="en">'+it.title+'</div>'
    +'<div class="tags">'+tags.join('')+'</div>'
    +'<div class="summary clamp">'+it.summary_zh+'</div>'
    +'<span class="more">展开全文 ▾</span>'
    +audioHtml
    +pathHtml
    +'</div>';
}

function render(){
  const list=DB.items.filter(match);
  document.getElementById('count').textContent='匹配 '+list.length+' / '+DB.items.length+' 个 Part';
  const grid=document.getElementById('grid');
  const empty=document.getElementById('empty');
  grid.innerHTML=list.map(card).join('');
  empty.style.display=list.length?'none':'block';
  grid.querySelectorAll('.more').forEach(m=>{
    m.addEventListener('click',()=>{
      const s=m.previousElementSibling;
      s.classList.toggle('clamp');
      m.textContent=s.classList.contains('clamp')?'展开全文 ▾':'收起 ▴';
    });
  });
}
render();
</script>
</body>
</html>
'''
open('listening_index.html','w',encoding='utf-8').write(html)
print('HTML written:', len(html), 'bytes')
