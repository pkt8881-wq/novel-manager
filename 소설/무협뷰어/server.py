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
body{font-family:'Malgun Gothic',sans-serif;background:#0a0a0f;color:#e0d5c5;
  min-height:100vh;overflow-x:hidden;
  padding-bottom:env(safe-area-inset-bottom)}
.header{
  background:linear-gradient(135deg,#1a1208,#2a1e0e);
  padding:12px 16px;padding-top:calc(12px + env(safe-area-inset-top));
  position:sticky;top:0;z-index:100;
  box-shadow:0 2px 20px rgba(0,0,0,.7);
  border-bottom:1px solid #c9a22740}
.header h1{font-size:clamp(18px,5vw,22px);color:#c9a227;margin-bottom:6px;
  text-shadow:0 0 20px #c9a22760}
.header .stats{font-size:12px;color:#888;margin-bottom:8px}
.search-bar{display:flex;gap:8px}
.search-bar input{
  flex:1;padding:10px 14px;border-radius:25px;
  border:1px solid #c9a22740;background:#1a1208;color:#e0d5c5;
  font-size:clamp(14px,4vw,16px);-webkit-appearance:none}
.search-bar input::placeholder{color:#664}
.filter-row{
  display:flex;gap:8px;padding:10px 14px;
  overflow-x:auto;scrollbar-width:none;
  background:#0d0d08;border-bottom:1px solid #1a1a10}
.filter-row::-webkit-scrollbar{display:none}
.chip{
  padding:7px 14px;border-radius:20px;
  border:1px solid #333;background:#1a1208;color:#998;
  font-size:clamp(12px,3.5vw,14px);cursor:pointer;white-space:nowrap;
  transition:.15s;-webkit-tap-highlight-color:transparent}
.chip.active{background:#c9a227;color:#000;border-color:#c9a227;font-weight:700}
.chip:active{opacity:.7}
.sort-row{
  display:flex;gap:6px;padding:8px 14px;
  background:#0a0a0f;border-bottom:1px solid #1a1a10;
  overflow-x:auto;scrollbar-width:none}
.sort-row::-webkit-scrollbar{display:none}
.sort-btn{
  padding:6px 12px;border-radius:12px;
  border:1px solid #333;background:transparent;
  color:#777;font-size:clamp(11px,3vw,13px);cursor:pointer;white-space:nowrap}
.sort-btn.active{color:#c9a227;border-color:#c9a227}
.novel-list{padding:10px 12px}
.novel-card{
  background:#150f05;border-radius:14px;
  padding:13px;margin-bottom:10px;
  display:flex;align-items:flex-start;gap:10px;
  cursor:pointer;transition:.15s;
  border:1px solid #2a2010;
  -webkit-tap-highlight-color:transparent}
.novel-card:active{transform:scale(.98);background:#1e1808}
.rank{font-size:clamp(15px,4vw,18px);font-weight:900;color:#c9a227;
  width:28px;text-align:center;flex-shrink:0;padding-top:3px}
.novel-info{flex:1;min-width:0}
.novel-title{font-size:clamp(14px,4vw,16px);font-weight:600;
  color:#e8dcc8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.novel-author{font-size:clamp(11px,3vw,13px);color:#c9a227;margin-top:3px}
.novel-meta{display:flex;gap:6px;margin-top:4px;align-items:center;flex-wrap:wrap}
.origin-badge{padding:2px 8px;border-radius:10px;font-size:11px;
  background:#2a1a00;color:#c9a227;border:1px solid #c9a22740}
.size-badge{font-size:11px;color:#666}
.loading{text-align:center;padding:40px;color:#444}
.fab{position:fixed;bottom:calc(24px + env(safe-area-inset-bottom));right:20px;
  background:#c9a227;color:#000;border:none;border-radius:50%;
  width:52px;height:52px;font-size:22px;cursor:pointer;
  box-shadow:0 4px 20px rgba(201,162,39,.4);z-index:50}
.fab:active{transform:scale(.92)}
</style>
</head>
<body>
<div class="header">
  <h1>⚔️ 무협지 도서관</h1>
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
[data-skin="light"]{--bg:#f5f0e8;--surface:#fff8ee;--card:#fffaf3;--accent:#8b4513;
  --text:#2a1a0a;--sub:#887766;--border:#d4c4a0;--read:#2a1a0a;--read-bg:#fffdf8}
[data-skin="night"]{--bg:#000005;--surface:#05050f;--card:#080818;--accent:#4488ff;
  --text:#c0d0ff;--sub:#446688;--border:#101030;--read:#d0e0ff;--read-bg:#030310}
[data-skin="green"]{--bg:#020c04;--surface:#081a0a;--card:#0c2410;--accent:#50c850;
  --text:#d8f0dc;--sub:#508050;--border:#183818;--read:#e8f8e8;--read-bg:#050e07}
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
const SKINS = ['dark','light','night','green'];
let skinIdx = 0;

let paragraphs=[], curPara=0, isPlaying=false, autoOn=false;
let totalPara=0, totalPages=1, curPage=1, pageStartIdx=0;
let _curUtt=null, silentAudio=null;

// ── Toast ──
function toast(msg,ms=2200){
  const t=document.getElementById('toast');
  t.textContent=msg;t.style.opacity='1';
  clearTimeout(t._t);t._t=setTimeout(()=>t.style.opacity='0',ms);
}

// ── 테마 ──
function cycleSkin(){
  skinIdx=(skinIdx+1)%SKINS.length;
  const s=SKINS[skinIdx];
  document.body.setAttribute('data-skin', s==='dark'?'':s);
  localStorage.setItem('wh_skin', skinIdx);
  const labels=['🌙 다크','☀️ 라이트','🌃 나이트','🌿 그린'];
  document.getElementById('skinBtn').textContent=labels[skinIdx];
}
(()=>{
  skinIdx=parseInt(localStorage.getItem('wh_skin')||'0');
  const s=SKINS[skinIdx];
  if(s!=='dark') document.body.setAttribute('data-skin',s);
})();

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

if __name__ == '__main__':
    print(f"무협지 뷰어 시작: http://localhost:{PORT}")
    print(f"데이터: {BASE_DIR}")
    novels = get_novels()
    print(f"작품 수: {len(novels)}편")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
