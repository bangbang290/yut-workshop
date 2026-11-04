/* Live projector presentation. Game decisions remain on the server.
 * Parent document receives a JSON state marker (.yut-st). Local code only
 * renders it, queues short transitions, and controls local sound/fullscreen. */
(function () {
  'use strict';
  var W = window, doc = document;
  if (W.__yutScreen) return;
  W.__yutScreen = true;
  var CSS = __CSS__, KIT = __SPRITES__;
  var NM = {back:'빽도',do:'도',gae:'개',geol:'걸',yut:'윷',mo:'모'};
  var STEPS = {back:-1,do:1,gae:2,geol:3,yut:4,mo:5}, AGAIN = {yut:1,mo:1};
  var COLORS = ['var(--t0)','var(--t1)','var(--t2)','var(--t3)'];
  var HEX = ['#d88046','#8c70a8','#557aa6','#799c58'];
  var VB = ['viewBox="0 0 64 96"','viewBox="0 0 64 96"','viewBox="0 0 96 72"','viewBox="0 0 64 64"'];
  function spr(t) { return KIT.spr[t % 4] || ''; }
  function av(t) {
    if (KIT.av && KIT.av[t % 4]) return KIT.av[t % 4];
    return KIT.avb ? spr(t).replace(VB[t % 4], 'viewBox="' + KIT.avb[t % 4] + '" style="overflow:hidden"') : spr(t);
  }
  function motion(t) { return (KIT.motion && KIT.motion[t % 4]) || 'walk'; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
  var P = {END:[90,90]}, k, t3 = 40 / 3;
  for (k=1;k<=4;k++) { P['O'+k]=[90,90-16*k];P['O'+(5+k)]=[90-16*k,10];P['O'+(10+k)]=[10,10+16*k];P['O'+(15+k)]=[10+16*k,90]; }
  P.O5=[90,10];P.O10=[10,10];P.O15=[10,90];
  P.A1=[90-t3,10+t3];P.A2=[90-2*t3,10+2*t3];P.C=[50,50];P.A3=[10+2*t3,90-2*t3];P.A4=[10+t3,90-t3];
  P.B1=[10+t3,10+t3];P.B2=[10+2*t3,10+2*t3];P.B3=[90-2*t3,90-2*t3];P.B4=[90-t3,90-t3];
  var WAIT=[99,82],EXIT=[97,97];
  var ROUTES={O:['S'],M:['S'],MC:['S'],D:['S']};
  (function(){
    var i;for(i=1;i<=19;i++)ROUTES.O.push('O'+i);ROUTES.O.push('END');
    for(i=1;i<=5;i++){ROUTES.M.push('O'+i);ROUTES.MC.push('O'+i);}
    ROUTES.M.push('A1','A2','C','A3','A4');for(i=15;i<=19;i++)ROUTES.M.push('O'+i);ROUTES.M.push('END');
    ROUTES.MC.push('A1','A2','C','B3','B4','END');
    for(i=1;i<=10;i++)ROUTES.D.push('O'+i);ROUTES.D.push('B1','B2','C','B3','B4','END');
  })();
  function nodeOf(g){return ROUTES[g.route] && ROUTES[g.route][g.idx];}
  function sx(p){return p[0]-p[1];}
  function tname(s,i){return (s.cfg.names && s.cfg.names[i]) || ['흥부','놀부','제비','박씨'][i];}
  var NS='http://www.w3.org/2000/svg',root,$,curB=540,lastW=-1,lastH=-1;
  function sv(tag,attrs,parent){var e=doc.createElementNS(NS,tag);for(var a in attrs)e.setAttribute(a,attrs[a]);if(parent)parent.appendChild(e);return e;}
  function div(cls,parent,h){var e=doc.createElement('div');e.className=cls;if(h!=null)e.innerHTML=h;if(parent)parent.appendChild(e);return e;}
  function icon(which){
    var paths=which==='sound'?'<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>':which==='muted'?'<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="m16 9 5 6m0-6-5 6"/>':which==='full'?'<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>':'<path d="m5 12 4 4L19 6"/>';
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+paths+'</svg>';
  }
  function setup(){
    var style=doc.createElement('style');style.id='yut-projector-style';style.textContent=CSS+(KIT.css||'');doc.head.appendChild(style);
    if(doc.querySelector('base')){
      var here=W.location.href.split('#')[0];
      KIT.spr=KIT.spr.map(function(s){return s.replace(/url\(#/g,'url('+here+'#');});
    }
    if(KIT.defs){var d=doc.createElement('div');d.innerHTML=KIT.defs;while(d.firstChild)doc.body.appendChild(d.firstChild);}
    root=doc.createElement('div');root.id='yut-app';root.setAttribute('aria-label','윷놀이 스크린');
    root.innerHTML=
      '<svg class="landscape" viewBox="0 0 1600 280" preserveAspectRatio="none" aria-hidden="true"><path d="M0 150Q140 55 310 160T590 125T910 170T1260 85T1600 160V280H0Z" fill="#b2c09a"/><path d="M0 205Q170 100 390 205T750 200T1110 165T1600 195V280H0Z" fill="#9caf8c"/><path d="M0 244Q200 190 500 240T1000 225T1600 247V280H0Z" fill="#d6c69f"/></svg>'+
      '<svg class="festival-flags flags-left" viewBox="0 0 240 30" aria-hidden="true"><path d="M-5 1Q110 22 245 2" fill="none" stroke="#8a6b45" stroke-width="1.4"/><path d="m22 5 16 3-10 14Z" fill="#bd563c"/><path d="m65 10 16 1-9 14Z" fill="#c89c3d"/><path d="m112 12 16-1-7 15Z" fill="#53746a"/><path d="m160 11 16-2-6 15Z" fill="#b85b40"/><path d="m207 7 16-2-5 14Z" fill="#c49a44"/></svg>'+
      '<svg class="festival-flags flags-right" viewBox="0 0 240 30" aria-hidden="true"><path d="M-5 1Q110 22 245 2" fill="none" stroke="#8a6b45" stroke-width="1.4"/><path d="m22 5 16 3-10 14Z" fill="#c49a44"/><path d="m74 11 16 1-9 14Z" fill="#bd563c"/><path d="m126 12 16-1-7 15Z" fill="#53746a"/><path d="m180 9 16-2-6 15Z" fill="#c89c3d"/></svg>'+
      '<header class="banner"><div class="brand"><div class="cloth"><h1>심사2국 워크숍</h1><span class="sub">윷놀이 한마당</span><span class="festival-seal" aria-hidden="true">한<br>마당</span></div></div>'+
      '<div class="header-actions"><div class="connection"><i></i><span>연결 중</span></div><button class="tool-btn show-results" type="button">최종 순위</button><button class="tool-btn sound-btn" type="button" title="효과음 켜기 / 끄기 (M)" aria-label="효과음 켜기">'+icon('muted')+'<span class="tool-label">소리 켜기</span></button><button class="tool-btn full-btn" type="button" title="전체 화면 (F)" aria-label="전체 화면">'+icon('full')+'<span class="tool-label">전체 화면</span></button></div></header>'+
      '<aside class="hud tl"><div class="card turn"><div class="eyebrow">윷놀이</div><div class="who">준비 중</div><div class="what">진행석 연결을 기다리고 있어요.</div></div></aside>'+
      '<section class="stage" aria-label="실시간 윷놀이 말판"><div class="board-kicker">함께 웃고, 함께 즐기는 우리들의 한 판</div><div class="plane"><svg class="roads" viewBox="0 0 100 100" aria-hidden="true"><g class="rdl"></g><g class="pvl"></g></svg><div class="tiles"></div><div class="marks"></div><div class="pieces"></div></div><div class="board-foot">모 · 뒷모 · 방에 멈추면 지름길로</div><div class="call" role="status" aria-live="polite"><div class="call-box"><strong></strong><small></small></div></div></section>'+
      '<aside class="hud tr"><div class="teams-heading"><h2>우리 팀은 지금</h2><span class="pieces-label"></span></div><div class="teams"></div><div class="legend"><span><i></i>대기</span><span><i class="on"></i>이동 중</span><span><i class="out"></i>완주</span></div><div class="rule-card"><b>함께 가면 더 신나요</b>같은 팀은 업고 가요.<br>상대 말을 잡으면 한 번 더!</div></aside>'+
      '<div class="footer"><span class="live-pill"><i></i>방금 한 수</span><div class="log" role="status" aria-live="polite">첫 번째 윷을 던지면 시작합니다.</div><span class="footer-note">결과 입력은 진행석 · 말 이동은 태블릿</span></div><div class="screen-notice" role="status"></div>';
    doc.body.appendChild(root);$=function(sel){return root.querySelector(sel);};
    initBoard();sizeBoard();bindControls();updateAudioButton();
    W.addEventListener('resize',function(){clearTimeout(W.__yutRt);W.__yutRt=setTimeout(sizeBoard,80);});
    try{doc.fonts.ready.then(function(){setTimeout(sizeBoard,50);});}catch(e){}
  }
  function initBoard(){
    var rd=$('.rdl');['M90 90L90 10L10 10L10 90Z','M90 10L10 90M10 10L90 90'].forEach(function(d){sv('path',{class:'rd',d:d},rd);sv('path',{class:'rd2',d:d},rd);});
    var tiles=$('.tiles');Object.keys(P).forEach(function(k){
      var big=['END','O5','O10','O15','C'].indexOf(k)>=0;
      var e=div('tile'+(big?' big':'')+(k==='C'?' mid':''),tiles,({O1:'<span>도</span>',O2:'<span>개</span>',O3:'<span>걸</span>',O4:'<span>윷</span>'})[k]||'');
      e.style.left=P[k][0]+'%';e.style.top=P[k][1]+'%';e.setAttribute('data-node',k);
    });
    [[[81,98],'출발','red'],[[96,5],'모',''],[[5,16],'뒷모',''],[[5,96],'찌모',''],[[57,43],'방','']].forEach(function(s){var e=pt(s[0],'',tiles);div('sign'+(s[2]?' '+s[2]:''),div('up',e),s[1]);});
  }
  function sizeBoard(){
    if(!root)return;
    var st=$('.stage'),pl=$('.plane'),rs=root.style,w=st.clientWidth,h=st.clientHeight;
    var topSpace=w<450?40:50,bottomSpace=39,available=Math.max(140,h-topSpace-bottomSpace),B=Math.max(100,Math.min(w/1.47,available/1.06));
    function setB(v){B=Math.max(90,Math.floor(v));curB=B;rs.setProperty('--B',B+'px');}
    setB(B);rs.setProperty('--dy','0px');
    for(var i=0;i<5;i++){
      var r=pl.getBoundingClientRect(),f=Math.min(1.2,(w*.966)/Math.max(1,r.width),available/Math.max(1,r.height+B*.16+18));
      if(f>.995&&f<1.005)break;setB(B*f);
    }
    var br=pl.getBoundingClientRect(),sr=st.getBoundingClientRect(),center=sr.top+topSpace+available/2;
    rs.setProperty('--dy',Math.round(center-(br.top-B*.16+br.bottom+18)/2)+'px');
    lastW=w;lastH=h;
  }
  function pt(at,cls,parent){var e=div('pt'+(cls?' '+cls:''),parent);e.style.left=at[0]+'%';e.style.top=at[1]+'%';return e;}
  function pieceEl(team,n,at,o){
    o=o||{};var e=pt(at,'pc k-'+motion(team)+(o.can?' can':'')+(o.sel?' sel':'')+(o.ghost?' ghostnew':''));e.style.setProperty('--tc',COLORS[team]);
    div('shd',e);div('base',e);if(o.can||o.sel)div('ring',e);
    var lift=div('lift',div('up',e)),face=div('face'+(o.flip?' flip':''),lift),figs=div('figs',div('lean',face));
    for(var i=Math.min(n,4)-1;i>=1;i--)div('fig back'+i,figs,spr(team));div('fig front',figs,spr(team));
    if(n>1)div('cnt',lift,'×'+n);return e;
  }
  function options(s){var pv=s.preview;if(!pv)return [];if(pv.options)return pv.options;return pv.dest?[{i:s.sel,r:s.pending[s.sel],nodes:pv.nodes||[],dest:pv.dest,finished:pv.finished}]:[];}
  var facing={};
  function drawBoard(s,opt){
    opt=opt||{};var box=$('.pieces');box.innerHTML='';var pvl=$('.pvl');pvl.innerHTML='';
    Array.prototype.forEach.call(root.querySelectorAll('.marks .spot'),function(e){e.remove();});
    var live=s.phase==='move'&&!opt.plain,can={},pv=live?s.preview:null;
    if(live)(s.selectable||[]).forEach(function(k){can[k]=1;});
    var items=s.groups.filter(function(g){return g.id!==opt.hide&&P[nodeOf(g)];}).map(function(g){return {g:g,at:P[nodeOf(g)]};});
    items.sort(function(a,b){return a.at[0]+a.at[1]-b.at[0]-b.at[1];});
    items.forEach(function(it){var g=it.g;box.appendChild(pieceEl(g.team,g.n,it.at,{can:!!can[g.id],sel:pv&&String(pv.key)===String(g.id),flip:facing[g.id]}));});
    if(live&&(can.new||(pv&&pv.key==='new')))box.appendChild(pieceEl(s.turn,1,WAIT,{can:true,ghost:true,sel:pv&&pv.key==='new'}));
    if(pv){
      var gc=HEX[pv.team!=null?pv.team:s.turn],destinations={};
      options(s).forEach(function(o){
        var to=o.finished?EXIT:P[o.dest];if(!to)return;
        var pts=(o.nodes||[]).filter(function(x){return P[x];}).map(function(x){return P[x];});
        if(pv.key==='new')pts.unshift(WAIT);if(o.finished)pts.push(EXIT);
        if(pts.length>1){var line=sv('polyline',{class:'pv',points:pts.map(function(p){return p.join(',');}).join(' ')},pvl);line.style.setProperty('--gc',gc);}
        var key=o.dest+':'+!!o.finished;if(!destinations[key])destinations[key]={to:to,finished:o.finished,names:[]};
        if(destinations[key].names.indexOf(NM[o.r])<0)destinations[key].names.push(NM[o.r]);
      });
      Object.keys(destinations).forEach(function(key){
        var d=destinations[key],sp=div('spot'+(d.finished?' exit':''),$('.marks'));sp.style.left=d.to[0]+'%';sp.style.top=d.to[1]+'%';sp.style.setProperty('--gc',gc);
        var label=d.names.join(' · '),lb=pt(d.to,'optp',box);lb.style.setProperty('--gc',gc);
        div('olab'+(d.finished?' exit':''),div('up',lb),d.finished?'완주<small>'+label+'</small>':label);
      });
    }
  }
  function renderAll(s,opt){
    opt=opt||{};var over=s.phase==='over',team=over&&s.ranks.length?s.ranks[0]:s.turn,pending=s.pending||[];
    $('.cloth h1').textContent=s.cfg.title||'심사2국 워크숍';var sub=$('.cloth .sub');sub.textContent=s.cfg.sub||'';sub.style.display=s.cfg.sub?'':'none';
    root.style.setProperty('--tc',COLORS[team]);root.style.setProperty('--team-count',s.cfg.teams);root.classList.toggle('is-over',over);
    var bonus=s.phase==='throw'&&(pending.length||((s.last||{}).kind==='move'&&(s.last||{}).caught&&s.cfg.captureBonus&&(s.last||{}).team===s.turn)),what=over?'모든 말이 먼저 완주했어요.':s.phase==='throw'?(bonus?'<b>한 번 더</b> 던지세요.':'윷을 힘차게 던져 주세요.'):(s.preview?'빛나는 <b>도착 칸</b>을 선택하세요.':'태블릿에서 <b>움직일 말</b>을 골라요.');
    var badge=over?'우승':s.phase==='throw'?(bonus?'한 번 더!':'윷 던지기'):s.preview?'도착 칸 선택':'말 선택';
    var chips=pending.length?pending.map(function(r,i){return '<span class="pchip'+(AGAIN[r]?' bonus':'')+(s.phase==='move'&&i===s.sel?' sel':'')+'">'+NM[r]+'<small>'+STEPS[r]+'칸</small></span>';}).join(''):'<span class="none">윷을 던지면 여기에 표시돼요.</span>';
    var step=over?4:s.phase==='throw'?1:s.preview?3:2;
    var steps=['윷 던지고 결과 입력','움직일 말 고르기','도착할 칸 선택'];
    var guide=steps.map(function(label,i){var n=i+1;return '<div class="step'+(n===step?' active':n<step?' complete':'')+'"><span class="num">'+(n<step?'✓':'0'+n)+'</span>'+label+'</div>';}).join('');
    $('.hud.tl').innerHTML='<div class="card turn" style="--tc:'+COLORS[team]+'"><div class="turn-top"><span class="eyebrow">'+(over?'오늘의 우승':'이번 차례')+'</span><span class="turn-badge">'+badge+'</span></div><div class="turn-hero">'+spr(team)+'</div><div class="who">'+esc(tname(s,team))+(over?' 승리!':' 차례')+'</div><div class="what">'+what+'</div></div>'+
      '<div class="card pendrow"><div class="label-row"><h2 class="lbl">남은 윷 결과</h2><span class="quantity">'+(pending.length?pending.length+'개':'')+'</span></div><div class="pend">'+chips+'</div></div><div class="steps">'+guide+'</div><div class="hint">'+(over?'다음 판은 <b>진행석</b>에서 시작해요.':s.phase==='throw'?'실제 윷을 던진 뒤<br><b>진행석</b>에서 결과를 눌러 주세요.':'팀 대표가 <b>태블릿</b>에서<br>말과 도착 칸을 차례로 눌러 주세요.')+'</div>';
    var rows='';for(var i=0;i<s.cfg.teams;i++){
      var on=s.groups.filter(function(g){return g.team===i;}).reduce(function(a,g){return a+g.n;},0),dots='';
      for(var j=0;j<s.cfg.pieces;j++)dots+='<span class="dot '+(j<s.done[i]?'out':j<s.done[i]+on?'on':'')+'"></span>';
      var rank=s.ranks.indexOf(i),now=i===s.turn&&!over;
      rows+='<div class="team'+(now?' now':'')+(rank>=0?' gone':'')+'" style="--tc:'+COLORS[i]+'"><div class="av">'+av(i)+'</div><div><div class="tname">'+esc(tname(s,i))+'</div><div class="tstat">대기 '+s.home[i]+' · 이동 '+on+'</div></div><div class="finish-count">'+s.done[i]+'<small>/ '+s.cfg.pieces+'</small></div><div class="team-progress"><div class="dots">'+dots+'</div>'+(rank>=0?'<span class="tag">'+(rank+1)+'위</span>':now?'<span class="tag">현재 차례</span>':'')+'</div></div>';
    }
    $('.teams').innerHTML=rows;$('.pieces-label').textContent='완주한 말 / '+s.cfg.pieces+'개';
    $('.rule-card').innerHTML='<b>함께 가면 더 신나요</b>같은 팀은 업고 가요.<br>'+(s.cfg.captureBonus?'상대 말을 잡으면 한 번 더!':'상대 말을 잡으면 출발로 돌려보내요.');
    var latest=(s.log||[])[0];$('.log').textContent=latest||'첫 번째 윷을 던지면 시작합니다.';
    $('.log').title=(s.log||[]).slice(0,4).join('\n');
    $('.board-kicker').textContent=over?'오늘의 한마당, 모두 수고하셨습니다!':s.phase==='throw'?(bonus?(pending.length?'윷 · 모는 한 번 더!':'잡기 성공! 한 번 더 던지세요'):'함께 웃고, 함께 즐기는 우리들의 한 판'):s.preview?'선택한 말의 도착 칸이 빛나고 있어요':'태블릿에서 이동할 말을 골라 주세요';
    $('.board-foot').textContent=s.cfg.strictEnd?'참먹이를 지나면 완주 · 모 · 뒷모 · 방에 멈추면 지름길':'참먹이에 도착하면 완주 · 모 · 뒷모 · 방에 멈추면 지름길';
    if(!over){var ov=$('.overlay');if(ov)ov.remove();}
    var stage=$('.stage');if(stage.clientWidth!==lastW||stage.clientHeight!==lastH)sizeBoard();drawBoard(s,opt);
  }
  var callTimer=null,noticeTimer=null;
  function callout(text,detail){
    var box=$('.call-box');box.querySelector('strong').textContent=text;box.querySelector('small').textContent=detail||'';box.classList.remove('go');void box.offsetWidth;box.classList.add('go');
    clearTimeout(callTimer);callTimer=setTimeout(function(){box.classList.remove('go');},1600);
  }
  function notice(message){$('.screen-notice').textContent=message;clearTimeout(noticeTimer);noticeTimer=setTimeout(function(){$('.screen-notice').textContent='';},4500);}
  function poof(node){if(!P[node])return;var p=div('poof',$('.marks'));p.style.left=P[node][0]+'%';p.style.top=P[node][1]+'%';setTimeout(function(){p.remove();},800);}
  function celebrate(s,quiet){
    if(!s.ranks.length)return;
    var old=$('.overlay');if(old)old.remove();
    if(!quiet&&!reduced){
      var confetti=div('confetti',root);for(var i=0;i<65;i++){var p=doc.createElement('i');p.style.left=Math.random()*100+'%';p.style.background=['#c96d4c','#d6ac56','#7c9875','#a9b8c2','#ede2bf'][i%5];p.style.animationDuration=(2.8+Math.random()*2.5)+'s';p.style.animationDelay=Math.random()*.9+'s';confetti.appendChild(p);}setTimeout(function(){confetti.remove();},6500);
    }
    var rows=s.ranks.map(function(t,i){return '<div class="rank-row"><span class="rank-no">'+(i+1)+'위</span><span class="av" style="--tc:'+COLORS[t]+'">'+av(t)+'</span><span class="rank-team">'+esc(tname(s,t))+'</span><span class="rank-state">'+s.done[t]+' / '+s.cfg.pieces+' 완주</span></div>';}).join('');
    var overlay=div('overlay',root,'<section class="win" role="dialog" aria-label="최종 순위"><div class="winner-mark">오늘의 윷놀이 우승팀</div><div class="winner-art">'+spr(s.ranks[0])+'</div><h2>'+esc(tname(s,s.ranks[0]))+' 우승!</h2><p class="win-sub">다 함께 즐긴 한 판, 모두 수고하셨습니다.</p><div class="rank">'+rows+'</div><button class="tool-btn close-results" type="button">말판 다시 보기</button></section>');
    overlay.querySelector('.close-results').addEventListener('click',function(){overlay.remove();$('.show-results').focus();});
    if(!quiet)beep('done');
  }
  var actx=null,muted=false;
  try{muted=W.localStorage.getItem('yut-muted')==='1';}catch(e){}
  function ac(){if(!actx){try{actx=new(W.AudioContext||W.webkitAudioContext)();}catch(e){actx=null;}}return actx;}
  function updateAudioButton(){if(!root)return;var on=!muted&&actx&&actx.state==='running',button=$('.sound-btn');button.innerHTML=icon(on?'sound':'muted')+'<span class="tool-label">'+(on?'소리 켜짐':'소리 켜기')+'</span>';button.setAttribute('aria-label',on?'효과음 끄기':'효과음 켜기');button.setAttribute('aria-pressed',on?'true':'false');}
  function unlock(){if(muted)return;var c=ac();if(!c)return;try{var p=c.resume();if(p&&p.then)p.then(updateAudioButton).catch(function(){});}catch(e){}updateAudioButton();}
  function toggleSound(){
    if(!actx||actx.state!=='running'){muted=false;unlock();}else{muted=!muted;if(!muted)unlock();}
    try{W.localStorage.setItem('yut-muted',muted?'1':'0');}catch(e){}updateAudioButton();if(!muted)setTimeout(function(){beep('tok');},80);
  }
  function toggleFullscreen(){
    try{var p=doc.fullscreenElement?doc.exitFullscreen():root.requestFullscreen();if(p&&p.catch)p.catch(function(){notice('전체 화면을 열 수 없으면 F11을 눌러 주세요.');});}catch(e){notice('전체 화면을 열 수 없으면 F11을 눌러 주세요.');}
  }
  function bindControls(){
    $('.sound-btn').addEventListener('click',toggleSound);$('.full-btn').addEventListener('click',toggleFullscreen);$('.show-results').addEventListener('click',function(){if(S&&S.phase==='over')celebrate(S,true);});
    doc.addEventListener('pointerdown',function(e){if(!e.target.closest||!e.target.closest('.sound-btn'))unlock();},true);
    doc.addEventListener('keydown',function(e){if(e.altKey||e.ctrlKey||e.metaKey||/INPUT|TEXTAREA|SELECT/.test((e.target||{}).tagName||''))return;if(e.key==='m'||e.key==='M'){e.preventDefault();toggleSound();}else if(e.key==='f'||e.key==='F'){e.preventDefault();toggleFullscreen();}else if(e.key==='Escape'){var ov=$('.overlay');if(ov)ov.remove();}else unlock();});
    doc.addEventListener('fullscreenchange',function(){var label=$('.full-btn .tool-label');if(label)label.textContent=doc.fullscreenElement?'전체 화면 해제':'전체 화면';});
  }
  function beep(kind){
    if(muted)return;var c=ac();if(!c||c.state!=='running')return;var t=c.currentTime+.01;
    function tone(f,d,v,type,at,f2){var o=c.createOscillator(),g=c.createGain();o.type=type||'triangle';o.frequency.setValueAtTime(f,t+(at||0));if(f2)o.frequency.exponentialRampToValueAtTime(f2,t+(at||0)+d);g.gain.setValueAtTime(.0001,t+(at||0));g.gain.exponentialRampToValueAtTime(v,t+(at||0)+.008);g.gain.exponentialRampToValueAtTime(.0001,t+(at||0)+d);o.connect(g);g.connect(c.destination);o.start(t+(at||0));o.stop(t+(at||0)+d+.05);}
    if(kind==='tok'){tone(700,.09,.11,'triangle');tone(350,.10,.06);}
    else if(kind==='walk'){tone(460,.05,.045);tone(230,.06,.03,'sine',.01);}
    else if(kind==='fly')tone(740,.1,.04,'sine',0,1100);
    else if(kind==='roll')tone(190,.09,.07,'triangle',0,140);
    else if(kind==='big'){[523,659,784].forEach(function(f,i){tone(f,.26,.09,'triangle',i*.10);});tone(1047,.42,.07,'sine',.32);}
    else if(kind==='catch'){tone(240,.18,.09,'triangle',0,130);tone(660,.20,.08,'triangle',.16);tone(880,.25,.08,'triangle',.25);}
    else if(kind==='done')[523,659,784,1047].forEach(function(f,i){tone(f,.30,.08,'triangle',i*.10);});
  }
  var S=null,busy=false,waiting=null,seenMove=null,seenThrow=null,wasOver=false;
  var reduced=false;try{reduced=W.matchMedia('(prefers-reduced-motion: reduce)').matches;}catch(e){}
  var animationEpoch=0,animationTimers=[];
  function later(fn,delay){var epoch=animationEpoch;var timer=setTimeout(function(){if(epoch===animationEpoch)fn();},delay);animationTimers.push(timer);return timer;}
  function cancelTransitions(){
    animationEpoch++;animationTimers.forEach(clearTimeout);animationTimers=[];busy=false;waiting=null;clearTimeout(callTimer);$('.call-box').classList.remove('go');
    try{Array.prototype.forEach.call($('.pieces').getAnimations({subtree:true}),function(a){a.cancel();});}catch(e){}
    Array.prototype.forEach.call(root.querySelectorAll('.confetti'),function(e){e.remove();});
  }
  function afterMove(n,L){
    renderAll(n);
    if(L.caught){poof(L.caught);callout('잡았다!',L.caughtN+'개의 말을 출발로!'+(n.cfg.captureBonus?' 한 번 더 던져요.':''));beep('catch');}
    else if(L.finished){callout('났다!',(L.n>1?L.n+'개의 말이 함께':'말이 무사히')+' 도착했어요.');beep('done');}
    else if(L.stacked){callout('업었다!','같은 팀 말을 업었어요.');beep('tok');}
    else beep('tok');
    if(L.rank&&n.phase!=='over')later(function(){callout(tname(n,L.team)+' '+L.rank+'위!','모든 말이 완주했어요.');},1300);
    if(n.phase==='over'&&!wasOver)later(function(){if(S&&S.phase==='over')celebrate(n);},700);
    wasOver=n.phase==='over';
  }
  function animateMove(prev,n,L){
    var pts=(L.nodes||[]).filter(function(x){return P[x];}).map(function(x){return P[x];});if(L.new&&pts.length)pts.unshift(WAIT);if(L.finished&&pts.length)pts.push(EXIT);
    if(reduced||pts.length<2){afterMove(n,L);return;}
    busy=true;renderAll(prev,{hide:L.new?null:L.id,plain:true});
    var team=L.team,kind=motion(team),hops=pts.length-1,per=kind==='walk'?310:kind==='fly'?250:280,total=Math.min(2500,per*hops);per=total/hops;
    if(kind==='fly'&&total<650){total=650;per=total/hops;}
    var el=pieceEl(team,L.n,pts[0],{});el.classList.add(kind==='walk'?'walking':kind==='fly'?'flying':'rolling');el.style.setProperty('--per',per+'ms');$('.pieces').appendChild(el);
    var face=el.querySelector('.face'),lift=el.querySelector('.lift'),shd=el.querySelector('.shd'),base=el.querySelector('.base'),left=false;
    var keyframes=pts.map(function(p,i){return {left:p[0]+'%',top:p[1]+'%',offset:i/hops};});
    try{
      el.animate(keyframes,{duration:total,fill:'forwards',easing:'linear'});
      if(kind==='fly'){
        var hi=Math.round(curB*.095);lift.animate([{transform:'translateY(0)'},{transform:'translateY(-'+hi+'px)',offset:.3},{transform:'translateY(-'+hi+'px)',offset:.7},{transform:'translateY(0)'}],{duration:total,easing:'ease-in-out',fill:'forwards'});
        shd.animate([{transform:'translate(-50%,-50%) scale(1)',opacity:1},{transform:'translate(-50%,-50%) scale(.55)',opacity:.5,offset:.5},{transform:'translate(-50%,-50%) scale(1)',opacity:1}],{duration:total,fill:'forwards'});
        base.animate([{opacity:.94},{opacity:.1,offset:.2},{opacity:.1,offset:.8},{opacity:.94}],{duration:total,fill:'forwards'});
      }
      if(L.finished){var fade=[{opacity:1},{opacity:1,offset:.82},{opacity:0}];el.querySelector('.up').animate(fade,{duration:total+200,fill:'forwards'});base.animate(fade,{duration:total+200,fill:'forwards'});shd.animate(fade,{duration:total+200,fill:'forwards'});}
    }catch(e){busy=false;afterMove(n,L);return;}
    for(var h=0;h<hops;h++)(function(h){later(function(){var d=sx(pts[h+1])-sx(pts[h]);if(d<-.01)left=true;else if(d>.01)left=false;face.classList.toggle('flip',left);if(kind!=='fly'||h%2===0)beep(kind);},per*h);})(h);
    later(function(){if(!L.finished&&L.id)facing[L.id]=left;busy=false;afterMove(n,L);if(waiting){var next=waiting;waiting=null;take(next);}},total+(L.finished?220:40));
  }
  function take(n){
    if(!n||!n.cfg)return;var L=n.last||{};
    var changedGame=!!S&&S.game_id&&n.game_id&&S.game_id!==n.game_id;
    var interrupt=changedGame||['undo','reset','restore','import'].indexOf(L.kind)>=0;
    if(busy&&!interrupt){if(!waiting||n.ver>=waiting.ver)waiting=n;return;}
    if(interrupt){cancelTransitions();facing={};}
    var prev=changedGame?null:S;S=n;
    if(!prev){seenMove=seenThrow=L.at||null;wasOver=n.phase==='over';renderAll(n);if(wasOver)celebrate(n,true);return;}
    if(L.kind==='move'&&L.at!==seenMove){seenMove=L.at;animateMove(prev,n,L);return;}
    renderAll(n);
    if(L.kind==='throw'&&L.at!==seenThrow){seenThrow=L.at;callout(NM[L.r]||'',AGAIN[L.r]?'한 번 더 던지세요!':L.r==='back'?'왔던 길로 한 칸 뒤로':STEPS[L.r]+'칸 앞으로');beep(AGAIN[L.r]?'big':'tok');}
    if(n.phase==='over'&&!wasOver)celebrate(n);wasOver=n.phase==='over';
  }
  var heartbeat=null,lastHeartbeatAt=Date.now(),hasHeartbeat=false,lastMarkerVersion=null,lastMarkerGame=null;
  function read(){
    var markers=doc.querySelectorAll('.yut-st'),latest=null;
    for(var i=0;i<markers.length;i++){
      try{var v=JSON.parse(markers[i].getAttribute('title'));if(!v.cfg)continue;if(!latest||(v._server_ts||0)>=(latest._server_ts||0))latest=v;}catch(e){}
    }
    return latest;
  }
  function connection(n){
    if(n&&n._server_ts!=null){hasHeartbeat=true;if(heartbeat!==n._server_ts){heartbeat=n._server_ts;lastHeartbeatAt=Date.now();}}
    var stale=!W.__YUT_PREVIEW__&&hasHeartbeat&&Date.now()-lastHeartbeatAt>8000;
    var el=$('.connection');el.classList.toggle('stale',stale);el.querySelector('span').textContent=W.__YUT_PREVIEW__?'미리보기':stale?'연결 확인 필요':n?'실시간 연결':'연결 중';
    el.title=stale?'진행석 화면과 연결을 확인하고, 화면이 멈춰 있으면 새로고침하세요.':'진행석·태블릿과 같은 판을 보여 줍니다.';
  }
  function tick(){
    var n=read();connection(n);if(!n)return;
    if(n.ver===lastMarkerVersion&&n.game_id===lastMarkerGame)return;lastMarkerVersion=n.ver;lastMarkerGame=n.game_id;
    if(S&&n.ver===S.ver&&n.game_id===S.game_id&&!waiting)return;if(waiting&&n.ver===waiting.ver&&n.game_id===waiting.game_id)return;take(n);
  }
  setup();setInterval(tick,250);tick();
  try{new MutationObserver(function(records){if(records.some(function(r){return r.target!==root&&!root.contains(r.target);}))tick();}).observe(doc.body,{subtree:true,attributes:true,attributeFilter:['title'],childList:true});}catch(e){}
  W.__yutScreenTest={take:take,state:function(){return S;},size:sizeBoard,B:function(){return curB;},busy:function(){return busy;},cancel:cancelTransitions};
})();
