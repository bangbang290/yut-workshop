/* 스크린(프로젝터) 화면 엔진.
   Streamlit 화면에 숨겨 둔 상태(.yut-st 의 title = JSON)를 0.25초마다 읽어서 3D 윷판을 그립니다.
   판 번호(ver)가 바뀌면: 말 이동은 칸마다 콩콩 뛰어가는 장면, 결과 입력은 큰 글씨, 잡기·나기·승리는 효과.
   입력은 받지 않습니다(결과는 진행석, 말은 패드에서). */
(function () {
  'use strict';
  var W = window, doc = document;
  if (W.__yutScreen) return;
  W.__yutScreen = true;

  var CSS = __CSS__;
  var NM = { back: '빽도', do: '도', gae: '개', geol: '걸', yut: '윷', mo: '모' };
  var AGAIN = { yut: 1, mo: 1 };
  var COLORS = ['var(--t0)', 'var(--t1)', 'var(--t2)', 'var(--t3)'];
  var HEX = ['#e07b1f', '#7a3fb0', '#1f3f8f', '#2e8b45'];
  var EMB = [
    '<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="13" y="25" width="22" height="13" rx="1.5" fill="#f7e9c8" stroke="#4a3018" stroke-width="1.8"/><rect x="21" y="29" width="6.5" height="9" fill="#9a6634" stroke="#4a3018" stroke-width="1.4"/><path d="M6.5 27.5C9 13 39 13 41.5 27.5Z" fill="#e2ad48" stroke="#4a3018" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 20.5c5-3 19-3 24 0M9.5 24.5c7-3 22-3 29 0" fill="none" stroke="#a8752a" stroke-width="1.3"/><path d="M24 14v-3" stroke="#4a3018" stroke-width="1.6"/></svg>',
    '<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="11" y="25" width="26" height="13" fill="#f7e9c8" stroke="#2c2238" stroke-width="1.8"/><path d="M15 25v13M33 25v13" stroke="#a83a2c" stroke-width="2.4"/><rect x="20.5" y="29" width="7" height="9" fill="#a83a2c" stroke="#2c2238" stroke-width="1.3"/><path d="M3.5 21.5c3 2.5 6 3 9 2.2h23c3 .8 6 .3 9-2.2l-6-7.5c-6-2.5-23-2.5-29 0Z" fill="#3c3a52" stroke="#1b1726" stroke-width="1.6" stroke-linejoin="round"/><path d="M12 17.5h24M10 20.5h28" stroke="#6e6a8c" stroke-width="1.2"/><path d="M9 14.2c4-3.2 26-3.2 30 0" fill="none" stroke="#1b1726" stroke-width="2.2" stroke-linecap="round"/></svg>',
    '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M22 23C17 12 10 9 3 10.5c7 2.5 12 8 15.5 15Z" fill="#1d2a52"/><path d="M26 23c6-9 13-12 19.5-10.5-6.5 2.5-11 7.5-14.5 14Z" fill="#26356a"/><path d="M38.5 25.5c-2.5 5-9.5 7.5-17 6.8L8.5 40l4.4-7.6L5 33.5l9.5-6.2c5-5.3 15-7.2 21.4-4.6 1.4.6 2.4 1.6 2.6 2.8Z" fill="#1d2a52"/><path d="M21.5 31.6c6 .3 12.5-1.6 15.4-5-3.6 1.6-9.6 3.4-15.4 5Z" fill="#fffaf0"/><circle cx="36.6" cy="24.3" r="1.6" fill="#d23a2a"/><circle cx="34.6" cy="23.4" r=".9" fill="#fff"/><path d="M38.4 24.6l3.2-.6-2.9 1.6Z" fill="#e8b03f"/></svg>',
    '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 12.5c-7.5 0-12.5 6.5-12.5 14S16.5 41 24 41s12.5-7 12.5-14.5S31.5 12.5 24 12.5Z" fill="#f5f2dc" stroke="#4d6b26" stroke-width="1.9"/><path d="M17.5 19c-2.5 5-2.3 11 1 16" fill="none" stroke="#d6cfa6" stroke-width="2.2" stroke-linecap="round"/><path d="M24 12.5c-.5-3 .5-5 2.5-6.5" fill="none" stroke="#4d6b26" stroke-width="2.2" stroke-linecap="round"/><path d="M26.5 7.5c4.5-3.8 10.5-2.2 12 1.8-4 2.2-9 1.8-12-1.8Z" fill="#4f9a3a" stroke="#2f5d22" stroke-width="1.2"/><path d="M24 12.5c3 .5 5 2 6 4" fill="none" stroke="#4d6b26" stroke-width="1.4"/></svg>'
  ];
  // 판 모양 (서버와 같은 좌표)
  var P = { END: [90, 90] };
  for (var k = 1; k <= 4; k++) { P['O' + k] = [90, 90 - 16 * k]; P['O' + (5 + k)] = [90 - 16 * k, 10]; P['O' + (10 + k)] = [10, 10 + 16 * k]; P['O' + (15 + k)] = [10 + 16 * k, 90]; }
  P.O5 = [90, 10]; P.O10 = [10, 10]; P.O15 = [10, 90];
  var t3 = 40 / 3;
  P.A1 = [90 - t3, 10 + t3]; P.A2 = [90 - 2 * t3, 10 + 2 * t3]; P.C = [50, 50]; P.A3 = [10 + 2 * t3, 90 - 2 * t3]; P.A4 = [10 + t3, 90 - t3];
  P.B1 = [10 + t3, 10 + t3]; P.B2 = [10 + 2 * t3, 10 + 2 * t3]; P.B3 = [90 - 2 * t3, 90 - 2 * t3]; P.B4 = [90 - t3, 90 - t3];
  var ROUTES = {
    O: ['S'], M: ['S'], MC: ['S'], D: ['S']
  };
  (function () {
    var i;
    for (i = 1; i <= 19; i++) ROUTES.O.push('O' + i); ROUTES.O.push('END');
    for (i = 1; i <= 5; i++) { ROUTES.M.push('O' + i); ROUTES.MC.push('O' + i); }
    ROUTES.M.push('A1', 'A2', 'C', 'A3', 'A4'); for (i = 15; i <= 19; i++) ROUTES.M.push('O' + i); ROUTES.M.push('END');
    ROUTES.MC.push('A1', 'A2', 'C', 'B3', 'B4', 'END');
    for (i = 1; i <= 10; i++) ROUTES.D.push('O' + i); ROUTES.D.push('B1', 'B2', 'C', 'B3', 'B4', 'END');
  })();
  function nodeOf(g) { return ROUTES[g.route][g.idx]; }

  // ───────────── 화면 뼈대
  var NS = 'http://www.w3.org/2000/svg', root, $;
  function sv(tag, attrs, parent) { var e = doc.createElementNS(NS, tag); for (var a in attrs) e.setAttribute(a, attrs[a]); if (parent) parent.appendChild(e); return e; }
  function div(cls, parent, html) { var e = doc.createElement('div'); e.className = cls; if (html != null) e.innerHTML = html; if (parent) parent.appendChild(e); return e; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]; }); }
  function setup() {
    var lk = doc.createElement('link'); lk.rel = 'stylesheet';
    lk.href = 'https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Nanum+Brush+Script&family=Yeon+Sung&display=swap';
    doc.head.appendChild(lk);
    var st = doc.createElement('style'); st.textContent = CSS; doc.head.appendChild(st);
    root = doc.createElement('div'); root.id = 'yut-app';
    root.innerHTML =
      '<header class="banner"><svg class="bunting" viewBox="0 0 1000 46" preserveAspectRatio="none" aria-hidden="true"></svg>' +
      '<div class="cloth"><div class="sub"></div><h1></h1><div class="seal" aria-hidden="true">한<br>마당</div></div></header>' +
      '<div class="main"><aside class="teams"></aside>' +
      '<section class="stage"><div class="plane"><svg class="roads" viewBox="0 0 100 100" aria-hidden="true"><g class="rdl"></g><g class="pvl"></g></svg>' +
      '<div class="tiles"></div><div class="marks"></div><div class="pieces"></div></div><div class="call"><span></span></div></section>' +
      '<aside class="side"><div class="card turn"></div><div class="card hint"></div><div><h2 class="lbl">이번 결과</h2><div class="pend"></div></div><div class="card log"></div></aside></div>' +
      '<div class="soundpill">화면을 한 번 누르면 효과음이 켜집니다</div>';
    doc.body.appendChild(root);
    $ = function (sel) { return root.querySelector(sel); };
    drawBunting(); initBoard(); sizeBoard();
    W.addEventListener('resize', function () { clearTimeout(W.__yutRt); W.__yutRt = setTimeout(function () { sizeBoard(); }, 80); });
    try { doc.fonts.ready.then(function () { setTimeout(sizeBoard, 50); }); } catch (e) {}
  }
  function drawBunting() {
    var svg = $('.bunting');
    sv('path', { d: 'M0 5 Q500 40 1000 5', fill: 'none', stroke: '#2b2218', 'stroke-width': 1.6 }, svg);
    var cols = ['#cf4430', '#e8b03f', '#1f3f8f', '#2e8b45', '#fffaf0', '#7a3fb0'];
    for (var i = 0, t = .02; t < .99; t += .028, i++) {
      var x = 1000 * t, y = 5 + 70 * t * (1 - t);
      sv('path', { d: 'M' + (x - 9) + ' ' + y + ' L' + (x + 9) + ' ' + y + ' L' + x + ' ' + (y + 19) + 'Z', fill: cols[i % cols.length], stroke: '#2b2218', 'stroke-width': 1 }, svg);
    }
  }
  function initBoard() {
    var rd = $('.rdl');
    ['M90 90 L90 10 L10 10 L10 90 Z', 'M90 10 L10 90 M10 10 L90 90'].forEach(function (d) { sv('path', { class: 'rd', d: d }, rd); sv('path', { class: 'rd2', d: d }, rd); });
    var tiles = $('.tiles');
    Object.keys(P).forEach(function (k) {
      var n = +k.slice(1), cls = 'tile';
      if (k === 'END') cls += ' big start'; else if (k === 'C') cls += ' big mid';
      else if (k === 'O5' || k === 'O10' || k === 'O15') cls += ' big';
      else if (k[0] === 'O') cls += n < 5 ? ' s1' : n < 10 ? ' s2' : n < 15 ? ' s3' : ' s4';
      else cls += ' dg';
      var t = div(cls, tiles, { O1: '<span>도</span>', O2: '<span>개</span>', O3: '<span>걸</span>', O4: '<span>윷</span>' }[k] || '');
      t.style.left = P[k][0] + '%'; t.style.top = P[k][1] + '%';
    });
    [['END', '출발 · 참먹이', 'red low'], ['O5', '모', ''], ['O10', '뒷모', ''], ['O15', '찌모', ''], ['C', '방', '']].forEach(function (s) {
      var pt = div('pt', tiles); pt.style.left = P[s[0]][0] + '%'; pt.style.top = P[s[0]][1] + '%';
      div('sign' + (s[2] ? ' ' + s[2] : ''), div('up', pt), esc(s[1]));
    });
  }
  // 기울인 판이 실제로 그려진 크기를 재서 가운데 칸에 꼭 맞춤
  function sizeBoard() {
    var st = $('.stage'), pl = $('.plane'), rs = root.style;
    var w = st.clientWidth, h = st.clientHeight, B = Math.max(160, Math.min(w / 1.5, h / 1.0));
    function setB(v) { B = Math.max(140, Math.floor(v)); rs.setProperty('--B', B + 'px'); }
    setB(B); rs.setProperty('--dy', '0px');
    var EDGE = 26;   // 판 아래쪽 나무 두께와 그림자
    for (var k = 0; k < 4; k++) {
      var r = pl.getBoundingClientRect(), f = Math.min(1, (w * .97) / r.width, (h * .97 - EDGE) / (r.height + B * .17));
      if (f > .995) break;
      setB(B * f);
    }
    var r2 = pl.getBoundingClientRect(), s = st.getBoundingClientRect();
    rs.setProperty('--dy', Math.round((s.top + s.bottom) / 2 - (r2.top - B * .17 + r2.bottom + EDGE) / 2) + 'px');
  }

  // ───────────── 그리기
  function tname(S, i) { return (S.cfg.names && S.cfg.names[i]) || ['흥부', '놀부', '제비', '박씨'][i]; }
  function pieceEl(S, g, node, o) {
    o = o || {};
    var pt = div('pc pt' + (o.can ? ' can' : '') + (o.sel ? ' sel' : '') + (o.ghost ? ' ghostnew' : ''));
    pt.setAttribute('data-id', g.id);
    pt.style.left = P[node][0] + '%'; pt.style.top = P[node][1] + '%';
    pt.style.setProperty('--tc', COLORS[g.team]);
    div('shd', pt);
    if (o.can) div('ring', pt);
    var hop = div('hop', div('piece', div('up', pt)));
    div('tok', hop, EMB[g.team % 4] + (g.n > 1 ? '<span class="cnt">' + g.n + '</span>' : '') + (o.num ? '<span class="num">' + esc(o.num) + '</span>' : ''));
    div('ped', hop);
    return pt;
  }
  function drawBoard(S, opt) {
    opt = opt || {};
    var box = $('.pieces'); box.innerHTML = '';
    var pv = $('.pvl'); pv.innerHTML = '';
    Array.prototype.forEach.call(root.querySelectorAll('.marks .ghost'), function (e) { e.remove(); });
    var cands = {}, prevKey = S.preview ? S.preview.key : null;
    if (!opt.plain) (S.cands || []).forEach(function (c) { cands[c.key] = c.num; });
    var list = S.groups.filter(function (g) { return g.id !== opt.hide; }).sort(function (a, b) {
      var A = P[nodeOf(a)], B2 = P[nodeOf(b)]; return (A[0] + A[1]) - (B2[0] + B2[1]);
    });
    list.forEach(function (g) {
      var num = cands[g.id];
      box.appendChild(pieceEl(S, g, nodeOf(g), { can: num != null, num: num, sel: prevKey === g.id }));
    });
    if (cands['new'] != null) {
      box.appendChild(pieceEl(S, { id: 'new', team: S.turn, n: 1 }, 'END', { can: true, ghost: true, num: cands['new'] + ' 새 말', sel: prevKey === 'new' }));
    }
    if (S.preview && !opt.plain) {
      var nodes = S.preview.nodes || [];
      if (nodes.length > 1) sv('polyline', { class: 'pv', points: nodes.map(function (n) { return P[n].join(','); }).join(' ') }, pv);
      var d = P[S.preview.dest];
      if (d) { var gh = div('ghost', $('.marks')); gh.style.left = d[0] + '%'; gh.style.top = d[1] + '%'; gh.style.setProperty('--gc', HEX[S.preview.team || S.turn]); }
    }
  }
  function renderAll(S, opt) {
    opt = opt || {};
    var over = S.phase === 'over', team = over && S.ranks.length ? S.ranks[0] : S.turn;
    $('.cloth h1').textContent = S.cfg.title || '심사2국 워크숍';
    var sub = $('.cloth .sub'); sub.textContent = S.cfg.sub || ''; sub.style.display = S.cfg.sub ? '' : 'none';
    root.style.setProperty('--tc', COLORS[team]);
    var what = over ? '모든 말이 먼저 났습니다' : S.phase === 'throw' ? (S.pending.length ? '윷이나 모! 한 번 더 던지세요' : '윷을 던지세요') : '말을 옮길 차례';
    $('.turn').innerHTML = '<div class="emb" style="--tc:' + COLORS[team] + '">' + EMB[team % 4] + '</div><div><div class="who">' + esc(tname(S, team)) + (over ? ' 승리!' : ' 차례') + '</div><div class="what">' + what + '</div></div>';
    var hint = over ? '수고하셨습니다!' : S.phase === 'throw' ? '윷을 던지면 <b>진행석</b>에서 결과를 누릅니다.'
      : S.preview ? '패드에서 <b>움직이기</b>를 누르면 갑니다.' : '패드에서 <b>말 번호</b>를 눌러 고르세요.';
    $('.hint').innerHTML = hint;
    $('.pend').innerHTML = S.pending.length ? S.pending.map(function (r, i) { return '<span class="pchip' + (S.phase === 'move' && i === S.sel ? ' sel' : '') + '">' + NM[r] + '</span>'; }).join('') : '<span class="none">아직 없음</span>';
    var t = '';
    for (var i = 0; i < S.cfg.teams; i++) {
      var on = S.groups.filter(function (g) { return g.team === i; }).reduce(function (a, g) { return a + g.n; }, 0), dots = '';
      for (var a = 0; a < S.cfg.pieces; a++) dots += '<span class="dot ' + (a < S.done[i] ? 'out' : a < S.done[i] + on ? 'on' : '') + '"></span>';
      var rk = S.ranks.indexOf(i);
      t += '<div class="card team' + (i === S.turn && !over ? ' now' : '') + (rk >= 0 ? ' gone' : '') + '" style="--tc:' + COLORS[i] + '"><div class="emb">' + EMB[i % 4] + '</div><div style="min-width:0">' +
           '<div class="tname">' + esc(tname(S, i)) + '</div><div class="tstat">대기 ' + S.home[i] + ' · 판 ' + on + ' · 난 말 ' + S.done[i] + '</div><div class="dots">' + dots + '</div></div>' +
           (rk >= 0 ? '<div class="rankbadge">' + (rk + 1) + '등</div>' : '') + '</div>';
    }
    $('.teams').innerHTML = t;
    $('.log').innerHTML = (S.log || []).slice(0, 3).map(function (l) { return '<div>' + esc(l) + '</div>'; }).join('') || '<div>윷을 던지면 시작합니다.</div>';
    if (!over) { var ov = $('.overlay'); if (ov) ov.remove(); }
    var st = $('.stage');   // 현수막 글씨 등으로 판 자리 크기가 바뀌었으면 다시 맞춤
    if (st.clientWidth !== lastW || st.clientHeight !== lastH) { lastW = st.clientWidth; lastH = st.clientHeight; sizeBoard(); }
    drawBoard(S, opt);
  }
  var lastW = -1, lastH = -1;

  // ───────────── 효과
  function callout(text) { var c = $('.call span'); c.textContent = text; c.classList.remove('go'); void c.offsetWidth; c.classList.add('go'); }
  function poof(node) { var p = div('poof', $('.marks')); p.style.left = P[node][0] + '%'; p.style.top = P[node][1] + '%'; setTimeout(function () { p.remove(); }, 800); }
  function celebrate(S) {
    var box = div('confetti', root);
    for (var i = 0; i < 90; i++) {
      var p = doc.createElement('i');
      p.style.left = (Math.random() * 100) + '%'; p.style.background = ['#cf4430', '#e8b03f', '#1f3f8f', '#2e8b45', '#fffaf0'][i % 5];
      p.style.animationDuration = (2.4 + Math.random() * 2.4) + 's'; p.style.animationDelay = (Math.random() * 1.2) + 's';
      box.appendChild(p);
    }
    setTimeout(function () { box.remove(); }, 6500);
    var rows = S.ranks.map(function (t, i) { return '<div><span class="emb" style="--tc:' + COLORS[t] + '">' + EMB[t % 4] + '</span>' + (i + 1) + '등 · ' + esc(tname(S, t)) + '</div>'; }).join('');
    var old = $('.overlay'); if (old) old.remove();
    div('overlay', root, '<div class="card win"><h2>' + esc(tname(S, S.ranks[0])) + ' 승리!</h2><div class="rank">' + rows + '</div></div>');
    beep('done');
  }
  // 소리 (한 번 클릭해야 켜짐. 도우미가 연 창처럼 자동 재생이 허용되면 바로 켜짐)
  var actx = null, unlocked = false;
  function ac() { if (!actx) { try { actx = new (W.AudioContext || W.webkitAudioContext)(); } catch (e) { actx = null; } } return actx; }
  function unlock() { var c = ac(); if (!c) return; try { c.resume(); } catch (e) {} setTimeout(function () { if (c.state === 'running') { unlocked = true; var p = $('.soundpill'); if (p) p.style.opacity = '0'; } }, 200); }
  doc.addEventListener('pointerdown', unlock, true); doc.addEventListener('keydown', unlock, true);
  function beep(kind) {
    var c = ac(); if (!c || c.state !== 'running') return;
    var t = c.currentTime + 0.01;
    function tone(f, d, v, type, at) {
      var o = c.createOscillator(), g = c.createGain(); o.type = type || 'triangle'; o.frequency.setValueAtTime(f, t + (at || 0));
      g.gain.setValueAtTime(0.0001, t + (at || 0)); g.gain.exponentialRampToValueAtTime(v, t + (at || 0) + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, t + (at || 0) + d);
      o.connect(g); g.connect(c.destination); o.start(t + (at || 0)); o.stop(t + (at || 0) + d + 0.05);
    }
    if (kind === 'tok') { tone(820, 0.09, 0.25, 'square'); tone(410, 0.12, 0.18); }
    else if (kind === 'hop') tone(620, 0.07, 0.12, 'triangle');
    else if (kind === 'big') { [0, .09, .18].forEach(function (a, i) { tone(700 - i * 90, 0.1, 0.22, 'square', a); }); tone(523, 0.5, 0.2, 'triangle', .28); tone(784, 0.6, 0.16, 'triangle', .34); }
    else if (kind === 'catch') { tone(180, 0.25, 0.35, 'sawtooth'); tone(120, 0.35, 0.3, 'square', .06); tone(880, 0.3, 0.12, 'triangle', .2); }
    else if (kind === 'done') { [523, 659, 784, 1047].forEach(function (f, i) { tone(f, 0.35, 0.18, 'triangle', i * 0.09); }); }
  }

  // ───────────── 말 이동 장면: 이동 전 판에서 그 말만 빼고, 칸마다 콩콩 뛰어간 뒤 새 판으로
  var S = null, busy = false, waiting = null, seenMove = null, seenThrow = null, wasOver = false;
  var reduced = false; try { reduced = W.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
  function afterMove(n, L) {
    renderAll(n);
    if (L.caught) { poof(L.caught); callout('잡았다!'); beep('catch'); }
    else if (L.finished) { callout(L.n > 1 ? L.n + '동 났다!' : '났다!'); beep('done'); }
    else if (L.stacked) { callout('업었다!'); beep('tok'); }
    else beep('tok');
    if (L.rank && n.phase !== 'over') setTimeout(function () { callout(tname(n, L.team) + ' ' + L.rank + '등!'); }, 1300);
    if (n.phase === 'over' && !wasOver) setTimeout(function () { celebrate(n); }, 600);
    wasOver = n.phase === 'over';
  }
  function animateMove(prev, n, L) {
    var nodes = (L.nodes || []).filter(function (x) { return P[x]; });
    if (reduced || nodes.length < 2) { afterMove(n, L); return; }
    busy = true;
    renderAll(prev, { hide: L.new ? null : L.id, plain: true });
    var el = pieceEl(n, { id: 'run', team: L.team, n: L.n }, nodes[0], {});
    $('.pieces').appendChild(el);
    var hops = nodes.length - 1, per = 300, total = per * hops, kf = [], hk = [];
    for (var i = 0; i < hops; i++) {
      var a = P[nodes[i]], b = P[nodes[i + 1]];
      kf.push({ left: a[0] + '%', top: a[1] + '%', offset: i / hops });
      kf.push({ left: (a[0] + b[0]) / 2 + '%', top: (a[1] + b[1]) / 2 + '%', offset: (i + .5) / hops });
      hk.push({ transform: 'translateY(0)', offset: i / hops, easing: 'ease-out' });
      hk.push({ transform: 'translateY(calc(var(--B) * -.07))', offset: (i + .5) / hops, easing: 'ease-in' });
    }
    var z = P[nodes[hops]];
    kf.push({ left: z[0] + '%', top: z[1] + '%', offset: 1 }); hk.push({ transform: 'translateY(0)', offset: 1 });
    try {
      el.animate(kf, { duration: total, fill: 'forwards' });
      el.querySelector('.hop').animate(hk, { duration: total, fill: 'forwards' });
      if (L.finished) el.querySelector('.piece').animate([{ opacity: 1 }, { opacity: 1, offset: .85 }, { opacity: 0 }], { duration: total + 250, fill: 'forwards' });
    } catch (e) {}
    for (var h = 1; h <= hops; h++) (function (h) { setTimeout(function () { beep('hop'); }, per * h - 40); })(h);
    setTimeout(function () {
      busy = false; afterMove(n, L);
      if (waiting) { var w = waiting; waiting = null; take(w); }
    }, total + (L.finished ? 260 : 60));
  }
  function take(n) {
    if (busy) { waiting = n; return; }
    var prev = S; S = n;
    var L = n.last || {};
    if (!prev) { seenMove = seenThrow = L.at || null; wasOver = n.phase === 'over'; renderAll(n); if (wasOver) celebrate(n); return; }
    if (L.kind === 'move' && L.at !== seenMove) { seenMove = L.at; animateMove(prev, n, L); return; }
    renderAll(n);
    if (L.kind === 'throw' && L.at !== seenThrow) { seenThrow = L.at; callout(NM[L.r] + (AGAIN[L.r] ? '! 한 번 더' : '!')); beep(AGAIN[L.r] ? 'big' : 'tok'); }
    if (n.phase === 'over' && !wasOver) celebrate(n);
    wasOver = n.phase === 'over';
  }
  function read() {
    var el = doc.querySelector('.yut-st');
    if (!el) return null;
    try { return JSON.parse(el.getAttribute('title')); } catch (e) { return null; }
  }
  function tick() {
    var n = read();
    if (!n || !n.cfg) return;
    if (S && n.ver === S.ver && !waiting) return;
    if (waiting && n.ver === waiting.ver) return;
    take(n);
  }
  setup();
  unlock();
  setInterval(tick, 250);
  try { new MutationObserver(function () { tick(); }).observe(doc.body, { subtree: true, attributes: true, attributeFilter: ['title'], childList: true }); } catch (e) {}
  W.__yutScreenTest = { take: take, state: function () { return S; }, size: function () { sizeBoard(); } };
})();
