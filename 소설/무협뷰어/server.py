#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
무협지 웹 뷰어 + TTS 리더
포트: 8906
데이터: E:\일반 소설\무협지\정리됨\목록.json
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os, re, json
from flask import Flask, jsonify, request, Response

BASE_DIR   = r"E:\일반 소설\무협지\정리됨"
JSON_PATH  = os.path.join(BASE_DIR, "목록.json")
PORT       = 8906

app = Flask(__name__)

# ─── 소설 목록 로드 ───
def load_novels():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    novels = data.get('무협지', [])
    for i, n in enumerate(novels):
        n['id'] = i + 1
    return novels

_novels_cache = None
def get_novels():
    global _novels_cache
    if _novels_cache is None:
        _novels_cache = load_novels()
    return _novels_cache

@app.route('/api/refresh')
def api_refresh():
    global _novels_cache
    _novels_cache = None
    novels = get_novels()
    return jsonify({"ok": True, "total": len(novels)})

# ─── 파일 읽기 ───
def read_file(fpath):
    try:
        with open(fpath, 'rb') as f:
            raw = f.read()
    except Exception:
        return ""
    if raw[:3] == b'\xef\xbb\xbf':
        return raw[3:].decode('utf-8', errors='replace')
    try:
        return raw.decode('utf-8')
    except:
        pass
    high = sum(1 for b in raw[:4096] if b >= 0x80) / max(len(raw[:4096]), 1)
    if high > 0.05:
        for enc in ('cp949', 'euc-kr'):
            try:
                return raw.decode(enc)
            except:
                continue
    # 한글 비율로 최적 인코딩 선택
    best, best_score = None, -1
    for enc in ('cp949', 'utf-8', 'euc-kr', 'utf-8-sig'):
        try:
            t = raw.decode(enc, errors='replace')
            k = sum(1 for c in t[:1000] if '\uAC00' <= c <= '\uD7A3')
            b = t[:1000].count('\uFFFD')
            s = k - b * 3
            if s > best_score:
                best_score, best = s, t
        except:
            continue
    return best or raw.decode('utf-8', errors='replace')

def split_paragraphs(text):
    paras = [p.strip() for p in re.split(r'\n{2,}|\r\n\r\n', text) if p.strip()]
    if len(paras) < 10:
        paras = [l.strip() for l in text.splitlines() if l.strip()]
    return paras

# ─── API ───
@app.route('/api/novels')
def api_novels():
    q      = request.args.get('q', '').strip()
    author = request.args.get('author', '').strip()
    sort   = request.args.get('sort', 'title')
    page   = max(1, int(request.args.get('page', 1)))
    limit  = min(200, int(request.args.get('limit', 50)))

    novels = get_novels()
    result = novels

    if q:
        ql = q.lower()
        result = [n for n in result if ql in n['제목'].lower() or ql in n['작가'].lower()]
    if author:
        result = [n for n in result if author in n['작가']]

    if sort == 'title':
        result = sorted(result, key=lambda n: n['제목'])
    elif sort == 'author':
        result = sorted(result, key=lambda n: (n['작가'], n['제목']))
    elif sort == 'size':
        result = sorted(result, key=lambda n: n.get('파일크기_MB', 0), reverse=True)

    total  = len(result)
    start  = (page - 1) * limit
    paged  = result[start:start+limit]

    return jsonify({
        "novels": paged,
        "total": total,
        "page": page
    })

@app.route('/api/authors')
def api_authors():
    novels = get_novels()
    from collections import Counter
    cnt = Counter(n['작가'] for n in novels if n['작가'] != '미상')
    return jsonify([{"작가": k, "cnt": v} for k, v in cnt.most_common(30)])

@app.route('/api/novel/<int:nid>/content')
def api_content(nid):
    novels = get_novels()
    novel  = next((n for n in novels if n['id'] == nid), None)
    if not novel:
        return jsonify({"error": "not found"}), 404

    page  = int(request.args.get('page', 1))
    psize = int(request.args.get('psize', 150))

    text  = read_file(novel['파일경로'])
    paras = split_paragraphs(text)
    total = len(paras)
    start = (page - 1) * psize
    end   = min(start + psize, total)

    return jsonify({
        "title":       novel['제목'],
        "author":      novel['작가'],
        "paragraphs":  paras[start:end],
        "page":        page,
        "total_para":  total,
        "total_pages": (total + psize - 1) // psize,
        "start_idx":   start
    })

@app.route('/api/bookmark', methods=['POST'])
def save_bookmark():
    data = request.json or {}
    nid  = data.get('novel_id')
    para = data.get('paragraph_idx', 0)
    pg   = data.get('page', 1)
    bm_file = os.path.join(BASE_DIR, 'bookmarks.json')
    bm = {}
    if os.path.exists(bm_file):
        try:
            with open(bm_file, 'r', encoding='utf-8') as f:
                bm = json.load(f)
        except:
            pass
    bm[str(nid)] = {"paragraph_idx": para, "page": pg}
    with open(bm_file, 'w', encoding='utf-8') as f:
        json.dump(bm, f, ensure_ascii=False)
    return jsonify({"ok": True})

@app.route('/api/bookmark/<int:nid>')
def get_bookmark(nid):
    bm_file = os.path.join(BASE_DIR, 'bookmarks.json')
    if not os.path.exists(bm_file):
        return jsonify({"paragraph_idx": 0, "page": 1})
    try:
        with open(bm_file, 'r', encoding='utf-8') as f:
            bm = json.load(f)
        d = bm.get(str(nid), {})
        return jsonify({"paragraph_idx": d.get('paragraph_idx', 0), "page": d.get('page', 1)})
    except:
        return jsonify({"paragraph_idx": 0, "page": 1})

# ─── 페이지 ───
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>⚔️ 무협지 도서관</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--acc:#c9a227;--bg:#0a0a0f;--surface:#150f05;--card:#1e1808;--border:#2a2010;--text:#e0d5c5;--sub:#887755}
[data-skin="sakura"]{--acc:#ff6baf;--bg:#18080f;--surface:#2d1220;--card:#3e1a2e;--border:#5a2545;--text:#fff3f8;--sub:#c090a8}
[data-skin="rainbow"]{--acc:#9d50ff;--bg:#080812;--surface:#10102a;--card:#16164a;--border:#28286a;--text:#f0f0ff;--sub:#8888cc}
[data-skin="ocean"]{--acc:#00c8e8;--bg:#010a14;--surface:#041824;--card:#062032;--border:#0a304e;--text:#d8f0ff;--sub:#5090b0}
[data-skin="library"]{--acc:#d4a030;--bg:#180e06;--surface:#281a0c;--card:#382414;--border:#503a20;--text:#f4e8d0;--sub:#907858}
[data-skin="forest"]{--acc:#50c850;--bg:#020c04;--surface:#081a0c;--card:#0c2410;--border:#183818;--text:#dcf0e0;--sub:#609060}
#skinCanvas{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:1;opacity:0;transition:opacity .6s}
#skinCanvas.on{opacity:1}
body{font-family:'Malgun Gothic',sans-serif;background:var(--bg);color:var(--text);
  min-height:100vh;overflow-x:hidden;padding-bottom:env(safe-area-inset-bottom)}
.header{
  background:var(--surface);
  padding:12px 16px;padding-top:calc(12px + env(safe-area-inset-top));
  position:sticky;top:0;z-index:100;
  box-shadow:0 2px 20px rgba(0,0,0,.7);
  border-bottom:1px solid var(--border)}
.header-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.header h1{font-size:clamp(18px,5vw,22px);color:var(--acc);
  text-shadow:0 0 20px rgba(201,162,39,.4)}
.skin-btn{background:none;border:1px solid var(--border);color:var(--acc);
  padding:4px 10px;border-radius:14px;font-size:12px;cursor:pointer;white-space:nowrap}
.header .stats{font-size:12px;color:var(--sub);margin-bottom:8px}
.search-bar{display:flex;gap:8px}
.search-bar input{
  flex:1;padding:10px 14px;border-radius:25px;
  border:1px solid var(--border);background:var(--card);color:var(--text);
  font-size:clamp(14px,4vw,16px);-webkit-appearance:none}
.search-bar input::placeholder{color:var(--sub)}
.filter-row{
  display:flex;gap:8px;padding:10px 14px;
  overflow-x:auto;scrollbar-width:none;
  background:var(--bg);border-bottom:1px solid var(--border)}
.filter-row::-webkit-scrollbar{display:none}
.chip{
  padding:7px 14px;border-radius:20px;
  border:1px solid var(--border);background:var(--card);color:var(--sub);
  font-size:clamp(12px,3.5vw,14px);cursor:pointer;white-space:nowrap;
  transition:.15s;-webkit-tap-highlight-color:transparent}
.chip.active{background:var(--acc);color:#000;border-color:var(--acc);font-weight:700}
.chip:active{opacity:.7}
.sort-row{
  display:flex;gap:6px;padding:8px 14px;
  background:var(--bg);border-bottom:1px solid var(--border);
  overflow-x:auto;scrollbar-width:none}
.sort-row::-webkit-scrollbar{display:none}
.sort-btn{
  padding:6px 12px;border-radius:12px;
  border:1px solid var(--border);background:transparent;
  color:var(--sub);font-size:clamp(11px,3vw,13px);cursor:pointer;white-space:nowrap}
.sort-btn.active{color:var(--acc);border-color:var(--acc)}
.novel-list{padding:10px 12px;position:relative;z-index:2}
.novel-card{
  background:var(--card);border-radius:14px;
  padding:13px;margin-bottom:10px;
  display:flex;align-items:flex-start;gap:10px;
  cursor:pointer;transition:.15s;
  border:1px solid var(--border);
  -webkit-tap-highlight-color:transparent}
.novel-card:active{transform:scale(.98)}
.rank{font-size:clamp(15px,4vw,18px);font-weight:900;color:var(--acc);
  width:28px;text-align:center;flex-shrink:0;padding-top:3px}
.novel-info{flex:1;min-width:0}
.novel-title{font-size:clamp(14px,4vw,16px);font-weight:600;
  color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.novel-author{font-size:clamp(11px,3vw,13px);color:var(--acc);margin-top:3px}
.novel-meta{display:flex;gap:6px;margin-top:4px;align-items:center;flex-wrap:wrap}
.origin-badge{padding:2px 8px;border-radius:10px;font-size:11px;
  background:var(--surface);color:var(--acc);border:1px solid var(--border)}
.size-badge{font-size:11px;color:var(--sub)}
.loading{text-align:center;padding:40px;color:var(--sub)}
.fab{position:fixed;bottom:calc(24px + env(safe-area-inset-bottom));right:20px;
  background:var(--acc);color:#000;border:none;border-radius:50%;
  width:52px;height:52px;font-size:22px;cursor:pointer;
  box-shadow:0 4px 20px rgba(0,0,0,.4);z-index:50}
.fab:active{transform:scale(.92)}
</style>
</head>
<body>
<canvas id="skinCanvas"></canvas>
<div class="header">
  <div class="header-top">
    <h1>⚔️ 무협지 도서관</h1>
    <button class="skin-btn" id="skinBtn" onclick="cycleSkin()">🌙 다크</button>
  </div>
  <div class="stats" id="stats">로딩 중...</div>
  <div class="search-bar">
    <input type="search" id="searchInput" placeholder="제목, 작가 검색..." oninput="onSearch()">
  </div>
</div>
<div class="filter-row" id="authorFilter">
  <div class="chip active" onclick="setAuthor('',this)">전체</div>
</div>
<div class="sort-row">
  <button class="sort-btn active" onclick="setSort('title',this)">가나다순</button>
  <button class="sort-btn" onclick="setSort('author',this)">작가순</button>
  <button class="sort-btn" onclick="setSort('size',this)">분량순</button>
</div>
<div class="novel-list" id="novelList"><div class="loading">목록 로딩 중...</div></div>
<button class="fab" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>

<script>
let curAuthor='', curSort='title', curQ='', page=1, loading=false, hasMore=true, searchTimer;

async function loadNovels(reset=false){
  if(loading||(!reset&&!hasMore)) return;
  if(reset){page=1;hasMore=true;document.getElementById('novelList').innerHTML='<div class="loading">로딩 중...</div>';}
  loading=true;
  const res=await fetch(`/api/novels?author=${encodeURIComponent(curAuthor)}&sort=${curSort}&q=${encodeURIComponent(curQ)}&page=${page}&limit=50`);
  const data=await res.json();
  if(reset) document.getElementById('novelList').innerHTML='';
  if(data.novels.length===0&&page===1){
    document.getElementById('novelList').innerHTML='<div class="loading">검색 결과 없음</div>';
  }
  data.novels.forEach((n,i)=>renderCard(n,(page-1)*50+i+1));
  document.getElementById('stats').textContent=`총 ${data.total.toLocaleString()}편`;
  hasMore=data.novels.length===50;
  page++; loading=false;
}

function renderCard(n, rank){
  const el=document.createElement('div');
  el.className='novel-card';
  el.innerHTML=`
    <div class="rank">${rank}</div>
    <div class="novel-info">
      <div class="novel-title">${n.제목}</div>
      <div class="novel-author">✍ ${n.작가}</div>
      <div class="novel-meta">
        <span class="origin-badge">${n.출신||'한국'}</span>
        <span class="size-badge">${(n.파일크기_MB||0).toFixed(1)}MB</span>
      </div>
    </div>`;
  el.onclick=()=>location.href=`/read/${n.id}`;
  document.getElementById('novelList').appendChild(el);
}

async function loadAuthors(){
  const res=await fetch('/api/authors');
  const authors=await res.json();
  const row=document.getElementById('authorFilter');
  authors.slice(0,20).forEach(a=>{
    const d=document.createElement('div');
    d.className='chip';
    d.textContent=`${a.작가} ${a.cnt}`;
    d.onclick=()=>setAuthor(a.작가,d);
    row.appendChild(d);
  });
}

function setAuthor(a,el){
  curAuthor=a;
  document.querySelectorAll('.filter-row .chip').forEach(c=>c.classList.remove('active'));
  if(el)el.classList.add('active');
  else document.querySelector('.filter-row .chip').classList.add('active');
  loadNovels(true);
}

function setSort(s,el){
  curSort=s;
  document.querySelectorAll('.sort-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  loadNovels(true);
}

function onSearch(){
  clearTimeout(searchTimer);
  searchTimer=setTimeout(()=>{curQ=document.getElementById('searchInput').value;loadNovels(true);},400);
}

window.addEventListener('scroll',()=>{
  if(window.innerHeight+window.scrollY>=document.body.offsetHeight-300) loadNovels();
});

// ── 6-테마 스킨 (canvas 애니메이션) ──
const SKINS=[
  {id:'dark',label:'🌙 다크'},{id:'sakura',label:'🌸 벚꽃'},
  {id:'rainbow',label:'🌈 오색찬란'},{id:'ocean',label:'🌊 밤바다'},
  {id:'library',label:'📚 서재'},{id:'forest',label:'🌿 숲속'},
];
let _si=0,_raf=null;
const _cv=document.getElementById('skinCanvas');
const _cx=_cv.getContext('2d');
function _rsz(){_cv.width=innerWidth;_cv.height=innerHeight;}
window.addEventListener('resize',_rsz);_rsz();

function applySkin(i){
  const sk=SKINS[i];
  document.documentElement.setAttribute('data-skin',sk.id==='dark'?'':sk.id);
  document.getElementById('skinBtn').textContent=sk.label;
  localStorage.setItem('wh_list_skin',i);
  if(_raf){cancelAnimationFrame(_raf);_raf=null;}
  _cv.classList.remove('on');_cx.clearRect(0,0,_cv.width,_cv.height);
  if(sk.id==='dark')_sDark();
  else if(sk.id==='sakura')_sSakura();
  else if(sk.id==='rainbow')_sRainbow();
  else if(sk.id==='ocean')_sOcean();
  else if(sk.id==='library')_sLibrary();
  else if(sk.id==='forest')_sForest();
}
function cycleSkin(){_si=(_si+1)%SKINS.length;applySkin(_si);}
(function(){const s=parseInt(localStorage.getItem('wh_list_skin')||'0');_si=(isNaN(s)?0:s)%6;applySkin(_si);})();

function _sDark(){
  _cv.classList.add('on');
  const S=[];for(let i=0;i<90;i++)S.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,r:Math.random()*1.4+.4,ph:Math.random()*Math.PI*2,sp:Math.random()*.022+.006,w:Math.random()>.7});
  let m=null,nm=Date.now()+2500+Math.random()*4000;
  function f(){_cx.clearRect(0,0,_cv.width,_cv.height);const t=Date.now()*.001;
    for(const s of S){const a=(Math.sin(t*s.sp*15+s.ph)+1)/2*.55+.1;const g=_cx.createRadialGradient(s.x,s.y,0,s.x,s.y,s.r*5.5);const c=s.w?'255,230,180':'200,215,255';g.addColorStop(0,'rgba(255,255,255,'+a+')');g.addColorStop(.25,'rgba('+c+','+a*.6+')');g.addColorStop(1,'rgba('+c+',0)');_cx.beginPath();_cx.arc(s.x,s.y,s.r*5.5,0,Math.PI*2);_cx.fillStyle=g;_cx.fill();}
    if(!m&&Date.now()>=nm)m={x:_cv.width*(.05+Math.random()*.25),y:_cv.height*(.2+Math.random()*.35),vx:2.8+Math.random()*2,vy:1.8+Math.random()*1.5,life:1};
    if(m){m.x+=m.vx;m.y+=m.vy;m.life-=.013;if(m.life<=0||m.y>_cv.height){m=null;nm=Date.now()+3500+Math.random()*5000;}else{const l=22,tl=_cx.createLinearGradient(m.x,m.y,m.x-m.vx*l,m.y-m.vy*l);tl.addColorStop(0,'rgba(255,255,255,'+m.life*.9+')');tl.addColorStop(1,'rgba(200,220,255,0)');_cx.beginPath();_cx.moveTo(m.x,m.y);_cx.lineTo(m.x-m.vx*l,m.y-m.vy*l);_cx.strokeStyle=tl;_cx.lineWidth=2;_cx.lineCap='round';_cx.stroke();}}
    _raf=requestAnimationFrame(f);}f();
}
function _sSakura(){
  _cv.classList.add('on');
  const P=[];for(let i=0;i<38;i++)P.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight-innerHeight,s:Math.random()*5+3,sp:Math.random()*.8+.25,dr:Math.random()*1.2-.6,rot:Math.random()*Math.PI*2,rs:(Math.random()-.5)*.035,op:Math.random()*.45+.2});
  function f(){_cx.clearRect(0,0,_cv.width,_cv.height);
    for(const p of P){_cx.save();_cx.translate(p.x,p.y);_cx.rotate(p.rot);_cx.globalAlpha=p.op;for(let i=0;i<5;i++){_cx.save();_cx.rotate(i*Math.PI*2/5);_cx.beginPath();_cx.ellipse(0,-p.s*.78,p.s*.3,p.s*.54,0,0,Math.PI*2);_cx.fillStyle='#ffb7d5';_cx.fill();_cx.restore();}_cx.beginPath();_cx.arc(0,0,p.s*.2,0,Math.PI*2);_cx.fillStyle='rgba(255,220,80,.9)';_cx.fill();_cx.restore();
      p.y+=p.sp;p.x+=p.dr+Math.sin(p.y*.015)*.5;p.rot+=p.rs;if(p.y>_cv.height+20){p.y=-20;p.x=Math.random()*_cv.width;}}
    _raf=requestAnimationFrame(f);}f();
}
function _sRainbow(){
  _cv.classList.add('on');
  const cols=[[255,107,157],[255,179,71],[255,225,86],[107,255,184],[86,207,255],[196,107,255]];
  const P=[];for(let i=0;i<75;i++){const c=cols[i%cols.length];P.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,r:Math.random()*2.5+.8,cr:c[0],cg:c[1],cb:c[2],ph:Math.random()*Math.PI*2,sp:Math.random()*.025+.008,dx:(Math.random()-.5)*.5,dy:(Math.random()-.5)*.5});}
  function f(){_cx.clearRect(0,0,_cv.width,_cv.height);const t=Date.now()*.001;
    for(const p of P){const a=(Math.sin(t*p.sp*30+p.ph)+1)/2*.32+.05;const g=_cx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r*3.5);g.addColorStop(0,'rgba('+p.cr+','+p.cg+','+p.cb+','+a+')');g.addColorStop(1,'rgba('+p.cr+','+p.cg+','+p.cb+',0)');_cx.beginPath();_cx.arc(p.x,p.y,p.r*3.5,0,Math.PI*2);_cx.fillStyle=g;_cx.fill();p.x+=p.dx;p.y+=p.dy;if(p.x<0||p.x>_cv.width)p.dx*=-1;if(p.y<0||p.y>_cv.height)p.dy*=-1;}
    _raf=requestAnimationFrame(f);}f();
}
function _sOcean(){
  _cv.classList.add('on');
  const P=[];for(let i=0;i<28;i++)P.push({x:Math.random()*innerWidth,y:innerHeight+Math.random()*innerHeight,r:Math.random()*4+2.5,sp:Math.random()*.6+.2,wb:Math.random()*Math.PI*2,op:Math.random()*.28+.12});
  function f(){_cx.clearRect(0,0,_cv.width,_cv.height);const t=Date.now()*.001;
    for(const p of P){p.y-=p.sp;p.x+=Math.sin(t*.7+p.wb)*.4;const fade=Math.min(1,(innerHeight-p.y)/innerHeight*4);const a=p.op*Math.max(0,fade);const g=_cx.createRadialGradient(p.x-p.r*.35,p.y-p.r*.35,0,p.x,p.y,p.r);g.addColorStop(0,'rgba(230,248,255,'+(a+.15)+')');g.addColorStop(.55,'rgba(140,210,255,'+a+')');g.addColorStop(1,'rgba(70,160,220,'+(a*.35)+')');_cx.beginPath();_cx.arc(p.x,p.y,p.r,0,Math.PI*2);_cx.fillStyle=g;_cx.fill();if(p.y<-10){p.y=innerHeight+Math.random()*60;p.x=Math.random()*innerWidth;}}
    _raf=requestAnimationFrame(f);}f();
}
function _sLibrary(){
  _cv.classList.add('on');
  const P=[];for(let i=0;i<55;i++)P.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,r:Math.random()*1.8+.5,ph:Math.random()*Math.PI*2,sp:Math.random()*.015+.005,dx:(Math.random()-.5)*.3,dy:-(Math.random()*.4+.1)});
  function f(){_cx.clearRect(0,0,_cv.width,_cv.height);const t=Date.now()*.001;
    for(const p of P){const a=(Math.sin(t*p.sp*20+p.ph)+1)/2*.4+.1;const g=_cx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r*4);g.addColorStop(0,'rgba(255,210,80,'+a+')');g.addColorStop(1,'rgba(200,140,30,0)');_cx.beginPath();_cx.arc(p.x,p.y,p.r*4,0,Math.PI*2);_cx.fillStyle=g;_cx.fill();p.x+=p.dx+Math.sin(t*.5+p.ph)*.2;p.y+=p.dy;if(p.y<-10){p.y=innerHeight+10;p.x=Math.random()*innerWidth;}if(p.x<0)p.x=innerWidth;else if(p.x>innerWidth)p.x=0;}
    _raf=requestAnimationFrame(f);}f();
}
function _sForest(){
  _cv.classList.add('on');
  const P=[];for(let i=0;i<30;i++)P.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,r:Math.random()*3+1.5,ph:Math.random()*Math.PI*2,sp:Math.random()*.02+.008,dx:(Math.random()-.5)*.7,dy:(Math.random()-.5)*.7});
  function f(){_cx.clearRect(0,0,_cv.width,_cv.height);const t=Date.now()*.001;
    for(const p of P){const a=(Math.sin(t*p.sp*20+p.ph)+1)/2*.48+.05;const g=_cx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r*5);g.addColorStop(0,'rgba(160,255,120,'+a+')');g.addColorStop(1,'rgba(80,200,60,0)');_cx.beginPath();_cx.arc(p.x,p.y,p.r*5,0,Math.PI*2);_cx.fillStyle=g;_cx.fill();p.x+=p.dx;p.y+=p.dy;if(p.x<-20)p.x=_cv.width+20;else if(p.x>_cv.width+20)p.x=-20;if(p.y<-20)p.y=_cv.height+20;else if(p.y>_cv.height+20)p.y=-20;}
    _raf=requestAnimationFrame(f);}f();
}

loadAuthors(); loadNovels(true);
</script>
</body></html>"""

READER_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>⚔️ 무협지 읽기</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{--bg:#0a0a0f;--surface:#150f05;--card:#1e1808;--accent:#c9a227;
  --text:#e8dcc8;--sub:#887755;--border:#2a2010;--read:#f0e8d8;--read-bg:#12100a}
#skinCanvas{position:fixed;top:0;left:0;width:100%;height:100%;
  pointer-events:none;z-index:5;opacity:0;transition:opacity .6s}
#skinCanvas.on{opacity:1}
[data-skin="sakura"]{--bg:#18080f;--surface:#2d1220;--card:#3e1a2e;--accent:#ff6baf;
  --text:#fff3f8;--sub:#c090a8;--border:#5a2545;--read:#fff8fc;--read-bg:#23101c}
[data-skin="rainbow"]{--bg:#080812;--surface:#10102a;--card:#16164a;--accent:#9d50ff;
  --text:#f0f0ff;--sub:#8888cc;--border:#28286a;--read:#f8f8ff;--read-bg:#0c0c28}
[data-skin="ocean"]{--bg:#010a14;--surface:#041824;--card:#062032;--accent:#00c8e8;
  --text:#d8f0ff;--sub:#5090b0;--border:#0a304e;--read:#e8f8ff;--read-bg:#030e1c}
[data-skin="library"]{--bg:#180e06;--surface:#281a0c;--card:#382414;--accent:#d4a030;
  --text:#f4e8d0;--sub:#907858;--border:#503a20;--read:#fef9f0;--read-bg:#1e1408}
[data-skin="forest"]{--bg:#020c04;--surface:#081a0c;--card:#0c2410;--accent:#50c850;
  --text:#dcf0e0;--sub:#609060;--border:#183818;--read:#f0f8f0;--read-bg:#050e07}
html{overflow-x:hidden;scroll-padding-top:56px;scroll-padding-bottom:200px}
body{min-height:100%;overflow-x:hidden;background:var(--bg);color:var(--text);
  font-family:'Malgun Gothic',serif;
  padding-top:calc(56px + env(safe-area-inset-top,0px));
  padding-bottom:calc(200px + env(safe-area-inset-bottom,0px))}
#topBar{position:fixed;top:env(safe-area-inset-top,0px);left:0;right:0;z-index:200;
  background:var(--surface);border-bottom:1px solid var(--border);
  height:56px;display:flex;align-items:center;gap:8px;padding:0 12px}
.back-btn{background:none;border:1px solid var(--border);color:var(--accent);
  padding:5px 12px;border-radius:14px;font-size:13px;cursor:pointer;flex-shrink:0}
.novel-title{font-size:13px;font-weight:bold;flex:1;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--accent)}
.bm-save{background:var(--accent);color:#000;border:none;
  border-radius:14px;padding:5px 12px;font-size:13px;font-weight:700;cursor:pointer;flex-shrink:0}

#ttsPanel{position:fixed;bottom:env(safe-area-inset-bottom,0px);left:0;right:0;z-index:200;
  background:var(--surface);border-top:2px solid var(--accent);padding:10px 12px}
.tts-row1{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.play-btn{width:52px;height:52px;border-radius:50%;background:var(--accent);color:#000;
  border:none;font-size:24px;cursor:pointer;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;font-weight:bold}
.play-btn:disabled{background:#555;color:#888}
.progress-wrap{flex:1}
.progress-bar{width:100%;height:5px;background:var(--border);border-radius:3px;overflow:hidden;cursor:pointer}
.progress-fill{height:100%;background:var(--accent);width:0%;transition:width .3s}
.time-info{font-size:11px;color:var(--sub);margin-top:3px;text-align:center}
.tts-row2{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.ctrl-btn{padding:6px 11px;border-radius:14px;border:1px solid var(--border);
  background:var(--card);color:var(--text);font-size:12px;cursor:pointer}
.ctrl-btn.on{border-color:var(--accent);color:var(--accent)}
.bm-btn{padding:6px 11px;border-radius:14px;font-size:12px;cursor:pointer;
  border:1px solid #555;background:var(--card);color:var(--sub)}
.bm-btn.on{border-color:#f4c542;color:#f4c542}
.range-wrap{display:flex;align-items:center;gap:4px;font-size:11px;color:var(--sub)}
.range-wrap input{width:70px;accent-color:var(--accent)}
.range-val{color:var(--accent);min-width:26px;font-size:12px}
#novelText{font-size:17px;line-height:2.1;color:var(--read);background:var(--read-bg);
  padding:16px 14px;border-radius:10px;white-space:pre-wrap;word-break:break-all;
  overflow-wrap:break-word;min-height:80px}
.para-el{transition:background .2s;border-radius:6px;padding:4px 8px;margin:-4px -8px;cursor:pointer}
.para-el.hl{background:rgba(201,162,39,.18);border-left:3px solid var(--accent);
  padding-left:10px;margin-left:-8px}
.para-el.done{color:var(--sub)}
#loading{text-align:center;padding:60px;color:var(--sub)}
.spinner{width:36px;height:36px;border-radius:50%;margin:0 auto 14px;
  border:3px solid var(--border);border-top-color:var(--accent);animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#toast{position:fixed;bottom:calc(210px + env(safe-area-inset-bottom,0px));left:50%;
  transform:translateX(-50%);background:rgba(40,30,10,.95);color:#e8d58a;
  padding:7px 16px;border-radius:18px;font-size:13px;
  opacity:0;transition:opacity .3s;pointer-events:none;z-index:300;white-space:nowrap}
/* 잠금 오버레이 */
#lockOverlay{display:none;position:fixed;inset:0;z-index:9999;
  background:rgba(5,4,2,.96);touch-action:none;user-select:none;
  flex-direction:column;align-items:center;justify-content:center;gap:20px}
#lockOverlay.active{display:flex}
.lock-icon{font-size:70px}.lock-hint{font-size:15px;color:#887755;text-align:center;line-height:1.8}
#unlockRing{width:90px;height:90px;border-radius:50%;position:relative;
  display:flex;align-items:center;justify-content:center}
#unlockRingSvg{position:absolute;top:0;left:0;width:100%;height:100%;transform:rotate(-90deg)}
#unlockRingCircle{fill:none;stroke:var(--accent);stroke-width:5;
  stroke-dasharray:254;stroke-dashoffset:254;stroke-linecap:round;transition:stroke-dashoffset .1s}
#unlockRingBg{fill:none;stroke:rgba(255,255,255,.08);stroke-width:5}
#unlockPct{font-size:16px;font-weight:bold;color:var(--accent)}
</style>
</head>
<body>
<canvas id="skinCanvas"></canvas>
<div id="topBar">
  <button class="back-btn" onclick="history.back()">◀ 목록</button>
  <div class="novel-title" id="topTitle">무협지 읽기</div>
  <button class="bm-save" onclick="saveBookmark()">🔖</button>
</div>

<div style="padding:12px" id="contentWrap">
  <div id="loading"><div class="spinner"></div>불러오는 중...</div>
  <div id="novelText" style="display:none"></div>
</div>

<div id="ttsPanel">
  <div class="tts-row1">
    <button class="play-btn" id="playBtn" onclick="togglePlay()" disabled>▶</button>
    <div class="progress-wrap">
      <div class="progress-bar" onclick="seekBar(event)">
        <div class="progress-fill" id="progressFill"></div>
      </div>
      <div class="time-info" id="timeInfo">불러오는 중...</div>
    </div>
  </div>
  <div class="tts-row2">
    <button class="bm-btn" id="bmBtn" onclick="toggleBookmark()">🔖 북마크</button>
    <button class="bm-btn" id="bmGoBtn" onclick="goBookmark()">📍 이동</button>
    <button class="ctrl-btn" id="skinBtn" onclick="cycleSkin()">🌙 테마</button>
    <button class="ctrl-btn" id="lockBtn" onclick="engageLock()">🔒 잠금</button>
    <select id="voiceSel" style="font-size:11px;padding:3px 6px;border-radius:10px;
      background:var(--card);color:var(--text);border:1px solid var(--border);
      max-width:140px;outline:none" onchange="onVoiceChange()"></select>
    <div class="range-wrap">
      속도<input type="range" id="rateSlider" min="0.5" max="2.0" step="0.1" value="1.3" oninput="onRateChange()">
      <span class="range-val" id="rateVal">1.3</span>
    </div>
    <div class="range-wrap">
      크기<input type="range" id="fontSlider" min="13" max="26" step="1" value="17" oninput="onFontChange()">
      <span class="range-val" id="fontVal">17</span>
    </div>
  </div>
</div>

<div id="toast"></div>
<div id="lockOverlay" oncontextmenu="return false">
  <div class="lock-icon">🔒</div>
  <div class="lock-hint">화면이 잠겼습니다<br>아무 곳이나 <b>2초</b> 꾹 누르면 해제</div>
  <div id="unlockRing">
    <svg id="unlockRingSvg" viewBox="0 0 90 90">
      <circle id="unlockRingBg" cx="45" cy="45" r="40"/>
      <circle id="unlockRingCircle" cx="45" cy="45" r="40"/>
    </svg>
    <span id="unlockPct"></span>
  </div>
</div>

<script>
const NID   = parseInt(location.pathname.split('/').pop());
const BM_KEY= 'wh_bm__' + NID;

let paragraphs=[], curPara=0, isPlaying=false, autoOn=false;
let totalPara=0, totalPages=1, curPage=1, pageStartIdx=0;
let _curUtt=null, silentAudio=null;

// ── Toast ──
function toast(msg,ms=2200){
  const t=document.getElementById('toast');
  t.textContent=msg;t.style.opacity='1';
  clearTimeout(t._t);t._t=setTimeout(()=>t.style.opacity='0',ms);
}

// ── 6-테마 스킨 시스템 (canvas 애니메이션) ──
const SKINS=[
  {id:'dark',   label:'🌙 다크'},
  {id:'sakura', label:'🌸 벚꽃'},
  {id:'rainbow',label:'🌈 오색찬란'},
  {id:'ocean',  label:'🌊 밤바다'},
  {id:'library',label:'📚 서재'},
  {id:'forest', label:'🌿 숲속'},
];
let _skinIdx=0, _skinRaf=null;
const _cv=document.getElementById('skinCanvas');
const _cx=_cv.getContext('2d');
function _cvResize(){_cv.width=innerWidth;_cv.height=innerHeight;}
window.addEventListener('resize',_cvResize);_cvResize();

function applySkin(idx){
  const sk=SKINS[idx];
  document.documentElement.setAttribute('data-skin',sk.id==='dark'?'':sk.id);
  document.getElementById('skinBtn').textContent=sk.label;
  localStorage.setItem('wh_skin',idx);
  if(_skinRaf){cancelAnimationFrame(_skinRaf);_skinRaf=null;}
  _cv.classList.remove('on');
  _cx.clearRect(0,0,_cv.width,_cv.height);
  if(sk.id==='dark')         _startDark();
  else if(sk.id==='sakura')  _startSakura();
  else if(sk.id==='rainbow') _startRainbow();
  else if(sk.id==='ocean')   _startOcean();
  else if(sk.id==='library') _startLibrary();
  else if(sk.id==='forest')  _startForest();
}
function cycleSkin(){
  _skinIdx=(_skinIdx+1)%SKINS.length;
  applySkin(_skinIdx);
  toast(SKINS[_skinIdx].label);
}
(function(){
  const saved=parseInt(localStorage.getItem('wh_skin')||'0');
  _skinIdx=(isNaN(saved)?0:saved)%SKINS.length;
  applySkin(_skinIdx);
})();

// 🌙 다크 — 발광 별빛 + 별똥별
function _startDark(){
  _cv.classList.add('on');
  const stars=[];
  for(let i=0;i<90;i++) stars.push({
    x:Math.random()*innerWidth,y:Math.random()*innerHeight,
    r:Math.random()*1.4+.4,ph:Math.random()*Math.PI*2,
    sp:Math.random()*.022+.006,warm:Math.random()>.7
  });
  let meteor=null,nextM=Date.now()+2500+Math.random()*4000;
  function frame(){
    _cx.clearRect(0,0,_cv.width,_cv.height);
    const t=Date.now()*.001;
    for(const s of stars){
      const a=(Math.sin(t*s.sp*15+s.ph)+1)/2*.55+.1;
      const glowR=s.r*5.5;
      const gr=_cx.createRadialGradient(s.x,s.y,0,s.x,s.y,glowR);
      const col=s.warm?'255,230,180':'200,215,255';
      gr.addColorStop(0,'rgba(255,255,255,'+a+')');
      gr.addColorStop(.25,'rgba('+col+','+a*.6+')');
      gr.addColorStop(1,'rgba('+col+',0)');
      _cx.beginPath();_cx.arc(s.x,s.y,glowR,0,Math.PI*2);
      _cx.fillStyle=gr;_cx.fill();
    }
    if(!meteor&&Date.now()>=nextM){
      meteor={x:_cv.width*(.05+Math.random()*.25),y:_cv.height*(.2+Math.random()*.35),
        vx:2.8+Math.random()*2,vy:1.8+Math.random()*1.5,life:1};
    }
    if(meteor){
      meteor.x+=meteor.vx;meteor.y+=meteor.vy;meteor.life-=.013;
      if(meteor.life<=0||meteor.y>_cv.height){
        meteor=null;nextM=Date.now()+3500+Math.random()*5000;
      } else {
        const len=22;
        const tl=_cx.createLinearGradient(meteor.x,meteor.y,meteor.x-meteor.vx*len,meteor.y-meteor.vy*len);
        tl.addColorStop(0,'rgba(255,255,255,'+meteor.life*.9+')');
        tl.addColorStop(.5,'rgba(200,220,255,'+meteor.life*.4+')');
        tl.addColorStop(1,'rgba(200,220,255,0)');
        _cx.beginPath();_cx.moveTo(meteor.x,meteor.y);
        _cx.lineTo(meteor.x-meteor.vx*len,meteor.y-meteor.vy*len);
        _cx.strokeStyle=tl;_cx.lineWidth=2;_cx.lineCap='round';_cx.stroke();
        _cx.beginPath();_cx.arc(meteor.x,meteor.y,2.2,0,Math.PI*2);
        _cx.fillStyle='rgba(255,255,255,'+meteor.life+')';_cx.fill();
      }
    }
    _skinRaf=requestAnimationFrame(frame);
  }
  frame();
}

// 🌸 벚꽃 — 5장 꽃잎
function _startSakura(){
  _cv.classList.add('on');
  const P=[];
  for(let i=0;i<38;i++) P.push({
    x:Math.random()*innerWidth,y:Math.random()*innerHeight-innerHeight,
    s:Math.random()*5+3,sp:Math.random()*.8+0.25,
    dr:Math.random()*1.2-0.6,rot:Math.random()*Math.PI*2,
    rs:(Math.random()-.5)*0.035,op:Math.random()*.45+.2
  });
  function drawFlower(p){
    _cx.save();_cx.translate(p.x,p.y);_cx.rotate(p.rot);_cx.globalAlpha=p.op;
    for(let i=0;i<5;i++){
      _cx.save();_cx.rotate(i*Math.PI*2/5);
      _cx.beginPath();_cx.ellipse(0,-p.s*.78,p.s*.3,p.s*.54,0,0,Math.PI*2);
      _cx.fillStyle='#ffb7d5';_cx.fill();_cx.restore();
    }
    _cx.beginPath();_cx.arc(0,0,p.s*.2,0,Math.PI*2);
    _cx.fillStyle='rgba(255,220,80,.9)';_cx.fill();_cx.restore();
  }
  function frame(){
    _cx.clearRect(0,0,_cv.width,_cv.height);
    for(const p of P){
      drawFlower(p);
      p.y+=p.sp;p.x+=p.dr+Math.sin(p.y*.015)*.5;p.rot+=p.rs;
      if(p.y>_cv.height+20){p.y=-20;p.x=Math.random()*_cv.width;}
    }
    _skinRaf=requestAnimationFrame(frame);
  }
  frame();
}

// 🌈 오색찬란 반짝이
function _startRainbow(){
  _cv.classList.add('on');
  const cols=[[255,107,157],[255,179,71],[255,225,86],[107,255,184],[86,207,255],[196,107,255],[255,107,107]];
  const P=[];
  for(let i=0;i<75;i++){
    const c=cols[i%cols.length];
    P.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,
      r:Math.random()*2.5+.8,cr:c[0],cg:c[1],cb:c[2],
      ph:Math.random()*Math.PI*2,sp:Math.random()*.025+.008,
      dx:(Math.random()-.5)*.5,dy:(Math.random()-.5)*.5});
  }
  function frame(){
    _cx.clearRect(0,0,_cv.width,_cv.height);
    const t=Date.now()*.001;
    for(const p of P){
      const a=(Math.sin(t*p.sp*30+p.ph)+1)/2*.32+.05;
      const gr=_cx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r*3.5);
      gr.addColorStop(0,'rgba('+p.cr+','+p.cg+','+p.cb+','+a+')');
      gr.addColorStop(1,'rgba('+p.cr+','+p.cg+','+p.cb+',0)');
      _cx.beginPath();_cx.arc(p.x,p.y,p.r*3.5,0,Math.PI*2);
      _cx.fillStyle=gr;_cx.fill();
      p.x+=p.dx;p.y+=p.dy;
      if(p.x<0||p.x>_cv.width)p.dx*=-1;
      if(p.y<0||p.y>_cv.height)p.dy*=-1;
    }
    _skinRaf=requestAnimationFrame(frame);
  }
  frame();
}

// 🌊 밤바다 — 물방울 아래→위
function _startOcean(){
  _cv.classList.add('on');
  const P=[];
  for(let i=0;i<28;i++) P.push({
    x:Math.random()*innerWidth,y:innerHeight+Math.random()*innerHeight,
    r:Math.random()*4+2.5,sp:Math.random()*.6+0.2,
    wb:Math.random()*Math.PI*2,op:Math.random()*.28+.12
  });
  function frame(){
    _cx.clearRect(0,0,_cv.width,_cv.height);
    const t=Date.now()*.001;
    for(const p of P){
      p.y-=p.sp;p.x+=Math.sin(t*.7+p.wb)*.4;
      const fade=Math.min(1,(innerHeight-p.y)/innerHeight*4);
      const a=p.op*Math.max(0,fade);
      const gr=_cx.createRadialGradient(p.x-p.r*.35,p.y-p.r*.35,0,p.x,p.y,p.r);
      gr.addColorStop(0,'rgba(230,248,255,'+(a+.15)+')');
      gr.addColorStop(.55,'rgba(140,210,255,'+a+')');
      gr.addColorStop(1,'rgba(70,160,220,'+(a*.35)+')');
      _cx.beginPath();_cx.arc(p.x,p.y,p.r,0,Math.PI*2);
      _cx.fillStyle=gr;_cx.fill();
      if(p.y<-10){p.y=innerHeight+Math.random()*60;p.x=Math.random()*innerWidth;}
    }
    _skinRaf=requestAnimationFrame(frame);
  }
  frame();
}

// 📚 서재 — 금빛 먼지
function _startLibrary(){
  _cv.classList.add('on');
  const P=[];
  for(let i=0;i<55;i++) P.push({
    x:Math.random()*innerWidth,y:Math.random()*innerHeight,
    r:Math.random()*1.8+.5,ph:Math.random()*Math.PI*2,
    sp:Math.random()*.015+.005,
    dx:(Math.random()-.5)*.3,dy:-(Math.random()*.4+.1)
  });
  function frame(){
    _cx.clearRect(0,0,_cv.width,_cv.height);
    const t=Date.now()*.001;
    for(const p of P){
      const a=(Math.sin(t*p.sp*20+p.ph)+1)/2*.4+.1;
      const gr=_cx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r*4);
      gr.addColorStop(0,'rgba(255,210,80,'+a+')');
      gr.addColorStop(1,'rgba(200,140,30,0)');
      _cx.beginPath();_cx.arc(p.x,p.y,p.r*4,0,Math.PI*2);
      _cx.fillStyle=gr;_cx.fill();
      p.x+=p.dx+Math.sin(t*.5+p.ph)*.2;p.y+=p.dy;
      if(p.y<-10){p.y=innerHeight+10;p.x=Math.random()*innerWidth;}
      if(p.x<0)p.x=innerWidth;else if(p.x>innerWidth)p.x=0;
    }
    _skinRaf=requestAnimationFrame(frame);
  }
  frame();
}

// 🌿 숲속 반딧불
function _startForest(){
  _cv.classList.add('on');
  const P=[];
  for(let i=0;i<30;i++) P.push({
    x:Math.random()*innerWidth,y:Math.random()*innerHeight,
    r:Math.random()*3+1.5,ph:Math.random()*Math.PI*2,
    sp:Math.random()*.02+.008,
    dx:(Math.random()-.5)*.7,dy:(Math.random()-.5)*.7
  });
  function frame(){
    _cx.clearRect(0,0,_cv.width,_cv.height);
    const t=Date.now()*.001;
    for(const p of P){
      const a=(Math.sin(t*p.sp*20+p.ph)+1)/2*.48+.05;
      const gr=_cx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r*5);
      gr.addColorStop(0,'rgba(160,255,120,'+a+')');
      gr.addColorStop(1,'rgba(80,200,60,0)');
      _cx.beginPath();_cx.arc(p.x,p.y,p.r*5,0,Math.PI*2);
      _cx.fillStyle=gr;_cx.fill();
      p.x+=p.dx;p.y+=p.dy;
      if(p.x<-20)p.x=_cv.width+20;else if(p.x>_cv.width+20)p.x=-20;
      if(p.y<-20)p.y=_cv.height+20;else if(p.y>_cv.height+20)p.y=-20;
    }
    _skinRaf=requestAnimationFrame(frame);
  }
  frame();
}

// ── 폰트 크기 ──
function onFontChange(){
  const v=document.getElementById('fontSlider').value;
  document.getElementById('fontVal').textContent=v;
  document.getElementById('novelText').style.fontSize=v+'px';
  localStorage.setItem('wh_font',v);
}
(()=>{
  const v=localStorage.getItem('wh_font');
  if(v){document.getElementById('fontSlider').value=v;
    document.getElementById('fontVal').textContent=v;
    if(document.getElementById('novelText'))
      document.getElementById('novelText').style.fontSize=v+'px';}
})();

// ── 속도 ──
function onRateChange(){
  const v=document.getElementById('rateSlider').value;
  document.getElementById('rateVal').textContent=v;
  localStorage.setItem('wh_rate',v);
}
function getRate(){return parseFloat(document.getElementById('rateSlider').value);}
(()=>{const v=localStorage.getItem('wh_rate');if(v){document.getElementById('rateSlider').value=v;document.getElementById('rateVal').textContent=v;}})();

// ── 북마크 ──
function bmRefresh(){
  const v=localStorage.getItem(BM_KEY);
  const btn=document.getElementById('bmBtn');
  if(v!==null){btn.textContent='🔖 '+(parseInt(v)+1)+'문단';btn.classList.add('on');}
  else{btn.textContent='🔖 북마크';btn.classList.remove('on');}
  return v!==null?parseInt(v):-1;
}
function toggleBookmark(){
  const v=localStorage.getItem(BM_KEY);
  if(v!==null&&parseInt(v)===curPara){localStorage.removeItem(BM_KEY);toast('북마크 해제');}
  else{localStorage.setItem(BM_KEY,curPara);toast((curPara+1)+'번째 문단 북마크');}
  bmRefresh();
}
function goBookmark(){
  const v=localStorage.getItem(BM_KEY);
  if(v===null){toast('북마크 없음');return;}
  stopAll();curPara=parseInt(v);updateProgress();jumpToPara(curPara);
  toast((curPara+1)+'번째 문단으로 이동');
  setTimeout(()=>{autoOn=true;playPara(curPara);},400);
}
function saveBookmark(){
  localStorage.setItem(BM_KEY, curPara);
  fetch('/api/bookmark',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({novel_id:NID,paragraph_idx:pageStartIdx+curPara,page:curPage})});
  toast('북마크 저장 🔖');bmRefresh();
}

// ══ TTS: 한자 제거 cleanTTS ══
function cleanTTS(text){
  return text
    // ★ 한자 완전 제거 (고전 무협지 한자 TTS 불가)
    .replace(/[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF\u2E80-\u2EFF\u31C0-\u31EF]/g,'')
    .replace(/\\[[^\\]]{0,40}\\]/g,'').replace(/【[^】]*】/g,'').replace(/〔[^〕]*〕/g,'')
    .replace(/[★☆◆◇■□▲▶◀▽△※◎●○♠♣♥♦*~`^@#%&_|]/g,'')
    .replace(/[『』「」《》〈〉]/g,'')
    .replace(/[-=_─━═—–·•]{2,}/g,' ')
    .replace(/[\\u2500-\\u257F\\u2580-\\u259F\\u25A0-\\u25FF\\u2600-\\u26FF]+/g,' ')
    .replace(/[\\n\\r]/g,' ').replace(/\\s+/g,' ').trim();
}
function hasReadable(t){return /[\\uAC00-\\uD7A3a-zA-Z0-9]/.test(t);}

// ── 무음 루프 ──
function startSilentLoop(){
  if(silentAudio)return;
  try{
    silentAudio=new Audio('data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=');
    silentAudio.loop=true;silentAudio.volume=0.001;
    silentAudio.play().catch(()=>{});
  }catch(e){}
}
function stopSilentLoop(){
  if(silentAudio){try{silentAudio.pause();silentAudio.src='';}catch(e){}silentAudio=null;}
}

// ── 청크 분할 ──
function chunkText(text,maxLen=140){
  if(text.length<=maxLen)return[text];
  const chunks=[];
  for(let i=0;i<text.length;i+=maxLen) chunks.push(text.slice(i,i+maxLen));
  return chunks;
}

// ── Web Speech 재생 ──
const synth=window.speechSynthesis;
let voices=[], curVoice=null;

function loadVoices(){
  const all=synth.getVoices();
  voices=all.filter(v=>{const l=(v.lang||'').replace('_','-').toLowerCase();return l==='ko-kr'||l==='ko';});
  if(!voices.length) voices=all.filter(v=>/korea|한국/i.test(v.name));
  const sel=document.getElementById('voiceSel');
  if(!sel)return;
  sel.innerHTML='';
  if(!voices.length){sel.innerHTML='<option>(한국어 음성 없음)</option>';return;}
  voices.forEach((v,i)=>{
    const isFem=/female|여|woman|yuna|seoyeon|sora|heami|f0[0-9]|smtf/i.test(v.name);
    const isMal=/male|남|man|minsu|dohwan|m0[0-9]|smtm/i.test(v.name);
    const label=isFem?'👩 여자':isMal?'👨 남자':'🗣 한국어('+(i+1)+')';
    const o=document.createElement('option');
    o.value=i;o.textContent=label;sel.appendChild(o);
  });
  const saved=parseInt(localStorage.getItem('wh_voice')||'0');
  if(voices[saved]){sel.value=saved;curVoice=voices[saved];}
  else curVoice=voices[0];
}
loadVoices();
if(speechSynthesis.onvoiceschanged!==undefined) speechSynthesis.onvoiceschanged=loadVoices;

function onVoiceChange(){
  const idx=parseInt(document.getElementById('voiceSel').value);
  if(voices[idx]){curVoice=voices[idx];localStorage.setItem('wh_voice',idx);}
  if(isPlaying){const wa=autoOn;stopAll();autoOn=wa;if(wa)playPara(curPara);}
}

function playWebSpeech(startIdx){
  let idx=startIdx, text='';
  while(idx<paragraphs.length){
    text=cleanTTS(paragraphs[idx]);
    if(text&&hasReadable(text))break;
    idx++;
  }
  if(idx>=paragraphs.length){
    if(curPage<totalPages){loadNextPage();return;}
    stopSilentLoop();onPlayEnd();return;
  }
  curPara=idx;highlightPara(idx);updateProgress();
  synth.cancel();
  _curUtt=new SpeechSynthesisUtterance(text);
  _curUtt.lang='ko-KR';_curUtt.rate=getRate();_curUtt.pitch=1.0;
  if(curVoice)_curUtt.voice=curVoice;
  const ci=idx;
  _curUtt.onend=()=>{if(!isPlaying)return;if(autoOn)setTimeout(()=>{if(isPlaying)playWebSpeech(ci+1);},50);else{stopSilentLoop();onPlayEnd();}};
  _curUtt.onerror=(e)=>{if(e.error==='interrupted'||e.error==='canceled')return;if(isPlaying&&autoOn)setTimeout(()=>{if(isPlaying)playWebSpeech(ci+1);},100);else{stopSilentLoop();onPlayEnd();}};
  synth.speak(_curUtt);
}

function playPara(i){
  isPlaying=true;document.getElementById('playBtn').textContent='⏸';
  startSilentLoop();playWebSpeech(i);
}

function stopAll(){
  if(_curUtt){_curUtt.onend=null;_curUtt.onerror=null;_curUtt=null;}
  synth.cancel();stopSilentLoop();
  isPlaying=false;autoOn=false;
  document.getElementById('playBtn').textContent='▶';
}

function onPlayEnd(){
  isPlaying=false;document.getElementById('playBtn').textContent='▶';
}

function togglePlay(){
  if(isPlaying)stopAll();
  else{autoOn=true;playPara(curPara);}
}

// ── 진행 ──
function updateProgress(){
  const global=pageStartIdx+curPara;
  const pct=totalPara>0?Math.round(global/totalPara*100):0;
  document.getElementById('progressFill').style.width=pct+'%';
  document.getElementById('timeInfo').textContent=(curPara+1+pageStartIdx)+' / '+totalPara+' 문단 ('+pct+'%)';
}

function seekBar(e){
  if(!totalPara)return;
  const pct=e.offsetX/e.currentTarget.offsetWidth;
  const target=Math.floor(pct*totalPara);
  const targetPage=Math.floor(target/150)+1;
  if(targetPage!==curPage){loadPage(targetPage,()=>{curPara=Math.max(0,target-pageStartIdx);jumpToPara(curPara);});}
  else{curPara=Math.max(0,Math.min(target-pageStartIdx,paragraphs.length-1));jumpToPara(curPara);}
}

function highlightPara(idx){
  document.querySelectorAll('.para-el').forEach((el,i)=>{
    el.classList.remove('hl','done');
    if(i===idx)el.classList.add('hl');
    else if(i<idx)el.classList.add('done');
  });
  const el=document.getElementById('para_'+idx);
  if(el){
    // offsetTop===0이면 최대 40회 재시도 (DOM 렌더 대기)
    let tries=0;
    const tryScroll=()=>{
      if(el.offsetTop>0||tries>40){el.scrollIntoView({behavior:'smooth',block:'nearest'});}
      else{tries++;setTimeout(tryScroll,50);}
    };
    tryScroll();
  }
}

function jumpToPara(idx){
  curPara=idx;highlightPara(idx);updateProgress();
}

function loadNextPage(){
  if(curPage<totalPages){loadPage(curPage+1,()=>{curPara=0;if(autoOn){playPara(0);}});}
  else{stopSilentLoop();onPlayEnd();}
}

// ── 페이지 로드 ──
async function loadPage(pg, cb){
  const res=await fetch(`/api/novel/${NID}/content?page=${pg}&psize=150`);
  const data=await res.json();
  paragraphs=data.paragraphs;
  totalPages=data.total_pages;
  totalPara=data.total_para;
  pageStartIdx=data.start_idx;
  curPage=pg;
  renderText();
  document.getElementById('topTitle').textContent=data.title;
  document.title='⚔️ '+data.title;
  document.getElementById('playBtn').disabled=false;
  bmRefresh();
  if(cb)cb();
}

function renderText(){
  const wrap=document.getElementById('novelText');
  wrap.innerHTML='';wrap.style.display='';
  document.getElementById('loading').style.display='none';
  paragraphs.forEach((p,i)=>{
    const el=document.createElement('p');
    el.className='para-el';el.id='para_'+i;
    el.textContent=p;
    el.onclick=()=>{stopAll();curPara=i;autoOn=true;playPara(i);}
    wrap.appendChild(el);
  });
  if(curPage<totalPages){
    const more=document.createElement('p');
    more.style.cssText='text-align:center;padding:20px;color:var(--sub);cursor:pointer';
    more.textContent='▼ 다음 페이지';
    more.onclick=()=>loadPage(curPage+1);
    wrap.appendChild(more);
  }
}

// ── 잠금 ──
function engageLock(){
  document.getElementById('lockOverlay').classList.add('active');
  initUnlockRing();
}
function initUnlockRing(){
  const circle=document.getElementById('unlockRingCircle');
  const pct=document.getElementById('unlockPct');
  let holdTimer=null, prog=0, animFrame=null, startTime=0;
  const overlay=document.getElementById('lockOverlay');
  function onStart(e){e.preventDefault();startTime=Date.now();holdTimer=setInterval(()=>{prog=Math.min(100,Math.round((Date.now()-startTime)/2000*100));circle.style.strokeDashoffset=254*(1-prog/100);pct.textContent=prog+'%';if(prog>=100){clearInterval(holdTimer);overlay.classList.remove('active');}},50);}
  function onEnd(e){e.preventDefault();clearInterval(holdTimer);prog=0;circle.style.strokeDashoffset=254;pct.textContent='';}
  overlay.addEventListener('touchstart',onStart,{passive:false});
  overlay.addEventListener('touchend',onEnd,{passive:false});
  overlay.addEventListener('mousedown',onStart);
  overlay.addEventListener('mouseup',onEnd);
}

// ── 초기화 ──
(async()=>{
  await loadPage(1);
  // 이어읽기 복원
  const bkRes=await fetch(`/api/bookmark/${NID}`);
  const bk=await bkRes.json();
  if(bk.paragraph_idx>0){
    const pg=bk.page||1;
    if(pg!==1)await loadPage(pg);
    curPara=Math.max(0,bk.paragraph_idx-pageStartIdx);
    jumpToPara(curPara);
    toast('📍 이어읽기: '+(bk.paragraph_idx+1)+'번째 문단');
  }
})();
</script>
</body></html>"""

@app.route('/')
def index():
    return Response(DASHBOARD_HTML, mimetype='text/html; charset=utf-8')

@app.route('/read/<int:nid>')
def reader(nid):
    return Response(READER_HTML, mimetype='text/html; charset=utf-8')

@app.route('/read_raw')
def read_raw():
    """소설읽기.html 호환 - 파일 원본 바이트 반환"""
    fpath = request.args.get('f', '').strip()
    if not fpath:
        return Response('path required', status=400)
    try:
        with open(fpath, 'rb') as f:
            raw = f.read()
        return Response(raw, mimetype='application/octet-stream',
                        headers={'Content-Disposition': 'inline'})
    except FileNotFoundError:
        return Response('not found', status=404)
    except Exception as e:
        return Response(str(e), status=500)

if __name__ == '__main__':
    print(f"무협지 뷰어 시작: http://localhost:{PORT}")
    print(f"데이터: {BASE_DIR}")
    novels = get_novels()
    print(f"작품 수: {len(novels)}편")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
