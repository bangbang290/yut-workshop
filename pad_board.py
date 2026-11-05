"""태블릿용 윷판: 말을 고르고, 도착 칸을 누르는 두 단계 인터페이스.

HTML iframe은 주기적으로 다시 만들지 않습니다. app.py의 fragment는 숨은
Streamlit 버튼과 marker만 갱신하고, 이 문서는 그 상태를 읽습니다.
모든 버튼에는 렌더링한 판 번호가 들어가므로 늦게 도착한 입력이 새 판에
적용되지 않습니다. 서버 함수에도 payload의 expected_ver를 전달해야 합니다.
"""
from __future__ import annotations

import html
import json
import time
import uuid
from functools import lru_cache

import sprites
import yutcore as Y

_SERVER_ID = uuid.uuid4().hex


def pad_state(S: dict) -> dict:
    keys = Y.selectable(S)
    return {
        "ver": S["ver"],
        "game_id": S.get("game_id"),
        "server": _SERVER_ID,
        "heartbeat": int(time.time() * 1000),
        "phase": S["phase"],
        "throwReason": Y.throw_reason(S),
        "turn": S["turn"],
        "teams": S["cfg"]["teams"],
        "names": [Y.tname(S, i) for i in range(4)],
        "home": S["home"],
        "done": S["done"],
        "ranks": S["ranks"],
        "pending": S["pending"],
        "captureBonus": S["cfg"]["captureBonus"],
        "groups": [
            {"id": g["id"], "team": g["team"], "n": g["n"], "node": Y.node_of(g)}
            for g in S["groups"]
        ],
        "selectable": keys,
        "opts": {
            str(key): [
                {"i": o["i"], "r": o["r"], "dest": o["dest"],
                 "finished": o["finished"], "nodes": o["nodes"]}
                for o in Y.options_for(S, key)
            ]
            for key in keys
        },
        "pv": (S.get("preview") or {}).get("key"),
        "last": S.get("last") or {},
    }


def marker(S: dict) -> str:
    value = json.dumps(pad_state(S), ensure_ascii=False)
    return f'<i class="yx-pad-st" title="{html.escape(value, quote=True)}" style="display:none" aria-hidden="true"></i>'


def hidden_keys(S: dict) -> list[tuple[str, str, dict]]:
    """(Streamlit key, action, arguments) for the version visible to the player.

    select: Y.select(arg['key'], expected_ver=arg['expected_ver'])
    move:   Y.move_option(arg['key'], arg['i'], expected_ver=arg['expected_ver'])
    """
    version = S["ver"]
    prefix = f"yx_v{version}"
    out = [(f"{prefix}_sel_none", "select", {"key": None, "expected_ver": version})]
    for key in Y.selectable(S):
        out.append((f"{prefix}_sel_{key}", "select", {"key": key, "expected_ver": version}))
        for option in Y.options_for(S, key):
            out.append((f"{prefix}_mv_{key}_{option['i']}", "move",
                        {"key": key, "i": option["i"], "expected_ver": version}))
    return out


HIDDEN_CSS = "<style>.st-key-yx_hidden{display:none!important}</style>"

_CSS = r"""
:root{color-scheme:light;--ink:#493d2b;--muted:#85755b;--paper:#fbf3df;--line:#d5bf96;--accent:#ad4d37}
*{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden;background:transparent;color:var(--ink);font-family:"Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif;-webkit-tap-highlight-color:transparent}
button{font:inherit;touch-action:manipulation;-webkit-tap-highlight-color:transparent}
button:focus-visible{outline:3px solid #d88d38!important;outline-offset:4px!important}
button:disabled{cursor:default}
#wrap{height:100%;display:flex;flex-direction:column;padding:16px 18px 10px;background:linear-gradient(155deg,#fff8e6,#f3e7cd);border:1.5px solid #ad9166;border-radius:14px;box-shadow:inset 0 0 0 4px #f9efd8,inset 0 0 0 5px #e1cda5;overflow:hidden;user-select:none;-webkit-user-select:none}
.pad-top{display:flex;justify-content:space-between;align-items:center;gap:12px;min-height:36px;margin-bottom:10px;border-bottom:1px solid #d9c59d;padding-bottom:3px}
.pad-eyebrow{display:block;font-size:10px;font-weight:750;letter-spacing:.1em;color:#937447;margin-bottom:3px}.pad-eyebrow::after{content:"한마당";display:inline-block;font-family:"YutBrush","Malgun Gothic",serif;font-size:10px;font-weight:400;line-height:1;border:1px solid #b34f39;border-radius:2px;color:#b34f39;padding:2px 3px;margin-left:8px;letter-spacing:0;transform:rotate(-5deg)}
#team{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:20px;font-weight:400;letter-spacing:-.03em;display:flex;align-items:center;gap:8px;min-width:0}
#team .team-dot{height:9px;width:9px;border-radius:50%;flex:none;background:var(--team,#b76d43);box-shadow:0 0 0 4px color-mix(in srgb,var(--team,#b76d43) 12%,transparent)}
#team .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:14em}
#connection{flex:none;display:flex;align-items:center;gap:5px;font-size:10px;font-weight:700;color:#7e8778;white-space:nowrap}
#connection i{width:6px;height:6px;border-radius:100%;background:#628665}
#connection.wait{color:#b78336}#connection.wait i{background:#b78336}#connection.off{color:#b75b47}#connection.off i{background:#b75b47}
.guide{display:flex;align-items:center;gap:5px;font-size:11px;font-weight:750;color:#9a8666;min-height:28px}
.step{display:flex;align-items:center;gap:6px;padding:5px 9px;border-radius:5px;white-space:nowrap}
.step i{width:18px;height:18px;display:grid;place-items:center;border-radius:4px;background:#e9dcc0;font-size:10px;font-style:normal}
.step.active{background:#edddbb;color:#72502c}.step.active i{background:#966039;color:#fff8e6}.step.done{color:#65704a}.step.done i{background:#dfe1c4}
.step-arrow{font-weight:400;color:#c0beae}
#stage-status{margin-left:auto;color:#837963;font-size:10px;font-weight:500;text-align:right}
.results{display:flex;align-items:center;gap:6px;min-height:42px;padding:6px 0 2px;overflow-x:auto;overflow-y:hidden;scrollbar-width:none;flex:none}
.results::-webkit-scrollbar{display:none}
.result-label{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:13px;font-weight:400;color:#917345;white-space:nowrap;margin-right:2px}
.rchip{display:inline-flex;align-items:center;justify-content:center;gap:5px;border:1.5px solid #c5ab7b;border-radius:5px;background:#fff8e5;padding:6px 10px;min-height:34px;color:#76562f;cursor:pointer;font-family:"YutHand","Malgun Gothic",sans-serif;font-size:14px;font-weight:400;white-space:nowrap;box-shadow:1px 1px 0 #ceb98f55}
.rchip small{font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;font-size:10px;font-weight:500;opacity:.7}.rchip.on{background:#7f5532;border-color:#644026;color:#fff7e3}.rchip:disabled{opacity:.6}.no-result{font-size:11px;color:#9b8866;padding:6px 0}
#play{position:relative;display:grid;place-items:center;flex:1;min-height:0}
#bd{position:relative;width:var(--S,470px);height:var(--S,470px)}
#bd svg.brd{position:absolute;inset:0;width:100%;height:100%;overflow:visible;filter:drop-shadow(0 13px 10px #80694014)}
.lay{position:absolute;inset:0;pointer-events:none}
.at{position:absolute;width:0;height:0}
.pc{position:absolute;left:0;top:0;transform:translate(-50%,-100%);display:flex;flex-direction:column;align-items:center;pointer-events:none;filter:drop-shadow(0 4px 3px #34271625)}
.pc .figs{position:relative;display:flex;align-items:flex-end}
.pc .fig{position:relative;display:block;transform-origin:50% 100%}
.piggyback .fig.front{z-index:4;transform:rotate(4deg)}
.pc .fig.b1{position:absolute;left:0;bottom:0;z-index:3;transform:translate(-27%,-46%) rotate(-6deg) scale(.65);filter:brightness(.98)}
.pc .fig.b2{position:absolute;left:0;bottom:0;z-index:2;transform:translate(32%,-65%) rotate(7deg) scale(.57);filter:brightness(.96)}
.pc .fig.b3{position:absolute;left:0;bottom:0;z-index:1;transform:translate(-12%,-86%) rotate(-4deg) scale(.49);filter:brightness(.94)}
.k-walk .fig{height:calc(var(--S)*.142)}.k-fly .fig{height:calc(var(--S)*.095)}.k-roll .fig{height:calc(var(--S)*.092)}
.k-fly .figs{margin-bottom:calc(var(--S)*.022)}
.pc .fig svg,.pc .fig img{height:100%;width:auto;display:block}
.cnt{position:absolute;right:-12px;top:0;min-width:23px;height:23px;padding:0 5px;border-radius:8px;background:var(--tc);color:#fff;border:2px solid #fffdf7;box-shadow:0 2px 4px #223e3522;display:grid;place-items:center;font-size:12px;font-weight:800;z-index:8}
.base{position:absolute;left:0;top:0;transform:translate(-50%,-50%);width:calc(var(--S)*.067);height:calc(var(--S)*.046);border-radius:50%;background:color-mix(in srgb,var(--tc) 55%,#fff8e8);border:2px solid color-mix(in srgb,var(--tc) 78%,#fff);box-shadow:0 3px 0 color-mix(in srgb,var(--tc) 55%,#665441)}
.ring{position:absolute;left:0;top:0;transform:translate(-50%,-50%);width:calc(var(--S)*.106);height:calc(var(--S)*.106);border-radius:50%;border:2px dashed var(--tc);background:color-mix(in srgb,var(--tc) 6%,transparent);animation:ring 1.8s ease-in-out infinite;pointer-events:none}
.sel .ring{border:3px solid var(--tc);box-shadow:0 0 0 3px #fffdf2;animation:none}
.can .pc{animation:bob 2.3s ease-in-out infinite}.sel .pc{animation:bob 1.5s ease-in-out infinite}
.dim .pc{opacity:.5}.ghost .pc{opacity:.92}
.tap,.tapd{position:absolute;left:0;top:0;pointer-events:auto;cursor:pointer;border:0;background:transparent;padding:0;appearance:none;touch-action:manipulation}
.tap{width:max(44px,calc(var(--S)*.105));height:max(48px,calc(var(--S)*.12));border-radius:50%;transform:translate(-50%,-78%)}
.tap:focus-visible{background:#e6b15c22}.tap:disabled{pointer-events:none}
.tapd{width:max(44px,calc(var(--S)*.106));height:max(44px,calc(var(--S)*.106));border-radius:50%;transform:translate(-50%,-50%)}
.tapd:focus-visible{background:#e6b15c33}.tapd:disabled{pointer-events:none}
.spot{position:absolute;left:0;top:0;transform:translate(-50%,-50%);width:calc(var(--S)*.103);height:calc(var(--S)*.103);border-radius:50%;border:3px solid var(--tc);background:color-mix(in srgb,var(--tc) 16%,#fffdf0);box-shadow:0 0 0 4px #fffdf3bb;pointer-events:none;animation:ring 1.7s ease-in-out infinite}
.spot::after{content:"";position:absolute;inset:24%;border-radius:50%;border:1.5px solid var(--tc);opacity:.5}
.olab{position:absolute;left:0;top:0;transform:translate(-50%,calc(-100% - var(--S)*.06));font-family:"YutHand","Malgun Gothic",sans-serif;font-size:clamp(12px,calc(var(--S)*.029),18px);font-weight:400;line-height:1.05;padding:6px 9px;border-radius:6px;background:#fff8e6;border:1.5px solid var(--tc);box-shadow:2px 2px 0 #a9865030;color:#65472a;white-space:nowrap;pointer-events:none;text-align:center}
.olab small{display:block;font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;margin-top:4px;font-size:9px;font-weight:700;color:#a56539}.olab.exit{background:#815335;border-color:#6e4127;color:#fff7e3}.olab.exit small{color:#eddcb9}
.lab{position:absolute;transform:translate(-50%,-50%);font-family:"YutHand","Malgun Gothic",sans-serif;font-size:clamp(10px,calc(var(--S)*.023),14px);font-weight:400;color:#8c704b;white-space:nowrap;pointer-events:none}
.lab.start{font-size:clamp(11px,calc(var(--S)*.026),16px);color:#a24c35;letter-spacing:.03em}
.tray{position:absolute;transform:translate(-50%,-50%);font-family:"YutHand","Malgun Gothic",sans-serif;font-size:clamp(10px,calc(var(--S)*.022),13px);font-weight:400;white-space:nowrap;text-align:center;color:#92754d;pointer-events:none}
.tray strong{font-weight:400;color:#795336}
.footer{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:34px;flex:none;border-top:1px solid #d9c69f;padding-top:7px}
#hint{font-size:10px;font-weight:500;color:#8b8573;line-height:1.5;margin:0}
#cancel,#refresh{border:1.5px solid #c8ae80;border-radius:5px;background:#fff8e6;min-height:34px;padding:6px 10px;color:#795b36;white-space:nowrap;font-size:10px;font-weight:650;cursor:pointer;flex:none;box-shadow:1px 2px 0 #d5bf9555}
#cancel:disabled,#refresh:disabled{opacity:.5}
[hidden]{display:none!important}
#toast{position:absolute;left:50%;bottom:49px;transform:translateX(-50%);z-index:50;max-width:calc(100% - 30px);width:max-content;background:#675035;color:#fff8e5;padding:10px 15px;border-radius:8px;font-size:12px;font-weight:600;box-shadow:0 4px 20px #4b362320;opacity:0;transition:opacity .2s;pointer-events:none;line-height:1.5;text-align:center}
#toast.on{opacity:1}
.pad-effects{z-index:5;pointer-events:none}
.pad-effects *{pointer-events:none!important}
.pad-impact{position:absolute;left:0;top:0;width:calc(var(--S)*.11);height:calc(var(--S)*.08);border:3px solid #b75236;border-radius:50%;box-shadow:0 0 0 3px #fff7dfaa;animation:padImpact .65s ease-out both}
.pad-impact.stack{border-color:#b79434;border-style:dashed}
.pad-star{position:absolute;left:0;top:0;width:calc(var(--S)*.022);height:calc(var(--S)*.022);background:#c89b38;clip-path:polygon(50% 0,62% 34%,98% 32%,70% 57%,80% 94%,50% 72%,20% 94%,30% 57%,2% 32%,38% 34%);animation:padSpark .65s ease-out both}
.pad-ghost .pc{filter:drop-shadow(0 3px 2px #4d342b26)}
@keyframes padImpact{0%{transform:translate(-50%,-50%) scale(.6);opacity:0}15%{opacity:.9}100%{transform:translate(-50%,-50%) scale(1.8);opacity:0}}
@keyframes padSpark{0%{transform:translate(-50%,-20px) scale(.4);opacity:0}15%{opacity:1}100%{transform:translate(var(--dx),var(--dy)) rotate(100deg) scale(.65);opacity:0}}
.chooser{position:absolute;inset:0;z-index:60;display:flex;align-items:flex-end;justify-content:center;background:#4c382924;border-radius:14px;padding:14px;backdrop-filter:blur(3px)}
.choice-card{width:100%;max-width:440px;border-radius:12px;background:#fff5df;padding:19px;box-shadow:3px 5px 0 #6e4e3533,0 12px 60px #4b362326;border:1.5px solid #bda276}
.choice-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.choice-head h2{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:22px;font-weight:400;letter-spacing:-.03em;margin:0;color:#6e492b}.choice-head p{font-size:11px;color:#8b7657;line-height:1.5;margin:6px 0 14px}
.choice-close{height:34px;width:34px;border:1px solid #cdb68b;background:#f0e1c0;border-radius:6px;font-size:19px;color:#8b6940;cursor:pointer}
.choice-buttons{display:flex;flex-direction:column;gap:7px}.choice-button{display:flex;justify-content:space-between;align-items:center;gap:10px;text-align:left;border:1.5px solid #c3a471;background:#f3e4bf;border-radius:7px;padding:13px 14px;min-height:56px;cursor:pointer;color:#6e4d2a}.choice-button b{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:18px;font-weight:400}.choice-button small{font-size:10px;color:#8d7651;text-align:right;line-height:1.5}
.sr-only{position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden;clip-path:inset(100%);white-space:nowrap}
@keyframes ring{50%{transform:translate(-50%,-50%) scale(1.08);opacity:.75}}
@keyframes bob{0%,100%{transform:translate(-50%,-100%)}50%{transform:translate(-50%,calc(-100% - var(--S)*.009))}}
@media(max-width:440px){#wrap{padding:10px 9px 8px;border-radius:10px}.pad-top{margin-bottom:5px}#team{font-size:18px}.step{font-size:10px;padding:4px 6px}#stage-status{display:none}.results{min-height:39px}.rchip{padding:5px 8px;font-size:13px}.rchip small{font-size:9px}.footer{min-height:37px}#hint{font-size:9px}.olab{padding:5px 6px;border-radius:5px}.cnt{min-width:20px;height:20px;font-size:10px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
"""

_JS = r"""
(function(){
'use strict';
var KIT=__KIT__, INITIAL=__INITIAL__, SHARED_FONTS=__SHARED_FONTS__;
var NM={back:'빽도',do:'도',gae:'개',geol:'걸',yut:'윷',mo:'모'};
var STEPS={back:'−1',do:'1',gae:'2',geol:'3',yut:'4',mo:'5'};
var AGAIN={yut:1,mo:1};
var HEX=['#d88046','#8c70a8','#557aa6','#799c58'];
var NODE={END:'출발',O5:'모',O10:'뒷모',O15:'찌모',C:'방',A1:'모 지름길 1',A2:'모 지름길 2',A3:'방 아래 1',A4:'방 아래 2',B1:'뒷모 지름길 1',B2:'뒷모 지름길 2',B3:'나가는 길 1',B4:'나가는 길 2'};
['도','개','걸','윷','모'].forEach(function(n,i){NODE['O'+(i+1)]=n;NODE['O'+(i+6)]='뒷'+n;NODE['O'+(i+11)]='찌'+n;if(i<4)NODE['O'+(i+16)]='날'+n;});
var Pn={END:[90,90]};for(var k=1;k<=4;k++){Pn['O'+k]=[90,90-16*k];Pn['O'+(5+k)]=[90-16*k,10];Pn['O'+(10+k)]=[10,10+16*k];Pn['O'+(15+k)]=[10+16*k,90];}
Pn.O5=[90,10];Pn.O10=[10,10];Pn.O15=[10,90];var third=40/3;
Pn.A1=[90-third,10+third];Pn.A2=[90-2*third,10+2*third];Pn.C=[50,50];Pn.A3=[10+2*third,90-2*third];Pn.A4=[10+third,90-third];
Pn.B1=[10+third,10+third];Pn.B2=[10+2*third,10+2*third];Pn.B3=[90-2*third,90-2*third];Pn.B4=[90-third,90-third];
function q(p){return [50+(p[0]-p[1])*.46,50+(p[0]+p[1]-100)*.46];}
var WAIT=[74,85],EXIT=[26,85];
var doc=document,PD=null;try{if(window.parent!==window)PD=window.parent.document;}catch(e){}
var wrap,bd,layT,layP,layO,layFx,svgB,S=null,sel=null,resultFilter='all',pending=null,choice=null;
var latestHeartbeat=0,lastSeen=0,connection='waiting',toastTimer=0,keyboard=false,fitTimer=0;
var markerCache=new WeakMap(),tickQueued=false,fontsAdopted=false,connectionPainted=false;
var feedbackKey=null,feedbackTimer=0,feedbackAnimations=[],reduced=false;
try{var motionPreference=window.matchMedia('(prefers-reduced-motion: reduce)');reduced=motionPreference.matches;var motionChanged=function(event){reduced=event.matches;if(reduced)clearFeedback(false);};if(motionPreference.addEventListener)motionPreference.addEventListener('change',motionChanged);else if(motionPreference.addListener)motionPreference.addListener(motionChanged);}catch(e){}
function compactSprites(){
  // Reuse one local image URL per character instead of inserting the complete
  // encoded picture into every piece, stack, and subsequent redraw.
  if(!window.URL||!window.URL.createObjectURL||!window.Blob||!window.atob)return;
  var urls=Object.create(null),fallbacks=Object.create(null);
  function compact(markup){return markup.replace(/href="(data:image\/[\w.+-]+;base64,[^"]+)"/g,function(original,uri){
    if(!urls[uri]){try{var comma=uri.indexOf(','),binary=window.atob(uri.slice(comma+1)),bytes=new Uint8Array(binary.length);for(var i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);urls[uri]=window.URL.createObjectURL(new window.Blob([bytes],{type:uri.slice(5,uri.indexOf(';'))}));fallbacks[urls[uri]]=uri;}catch(e){return original;}}
    return 'href="'+urls[uri]+'"';
  });}
  KIT.spr=KIT.spr.map(compact);
  doc.addEventListener('error',function(event){var e=event.target,uri=e&&e.getAttribute&&e.getAttribute('href');if(uri&&fallbacks[uri])e.setAttribute('href',fallbacks[uri]);},true);
}
function adoptFonts(){
  // Live mode already sent these font bytes in the parent Streamlit page.
  // Copy once locally when available; standalone previews embed their fonts.
  if(!SHARED_FONTS||fontsAdopted||!PD)return;
  var source=PD.getElementById('yut-fonts');
  if(source&&source.textContent){var style=doc.createElement('style');style.id='yut-pad-fonts';style.textContent=source.textContent;doc.head.appendChild(style);fontsAdopted=true;}
}
function el(tag,cls,parent,markup){var e=doc.createElement(tag);if(cls)e.className=cls;if(markup!=null)e.innerHTML=markup;if(parent)parent.appendChild(e);return e;}
function sv(tag,attrs,parent){var e=doc.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs).forEach(function(key){e.setAttribute(key,attrs[key]);});if(parent)parent.appendChild(e);return e;}
function at(p,cls,parent){var e=el('div','at'+(cls?' '+cls:''),parent);e.style.left=p[0]+'%';e.style.top=p[1]+'%';return e;}
function esc(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function same(a,b){return a==null?b==null:String(a)===String(b);}
function announce(text){doc.getElementById('announcement').textContent=text;}
function toast(text){var e=doc.getElementById('toast');e.textContent=text;e.classList.add('on');announce(text);clearTimeout(toastTimer);toastTimer=setTimeout(function(){e.classList.remove('on');},3200);}
function button(parent,cls,label,fn){var e=el('button',cls,parent);e.type='button';e.setAttribute('aria-label',label);if(fn)e.addEventListener('click',function(event){event.stopPropagation();fn();});return e;}
function currentTeam(){return S&&S.phase==='over'&&S.ranks&&S.ranks.length?S.ranks[0]:(S?S.turn:0);}
function isReady(){return !!S&&!pending&&connection==='ok'&&!INITIAL;}
function actionKey(kind,key,i){return 'yx_v'+S.ver+'_'+(kind==='move'?'mv_'+key+'_'+i:'sel_'+(key==null?'none':key));}
function send(kind,key,i){
  if(!isReady())return false;
  var id=actionKey(kind,key,i),target=PD&&PD.querySelector('.st-key-'+id+' button');
  if(!target||!target.isConnected||target.disabled){tick();toast('화면을 맞추고 있어요. 잠깐 뒤 다시 눌러 주세요.');return false;}
  pending={kind:kind,key:key,i:i,version:S.ver,at:Date.now()};
  if(kind==='select')sel=key;
  target.click();draw();return true;
}
function fit(){if(!bd)return;var play=doc.getElementById('play');var size=Math.max(160,Math.floor(Math.min(play.clientWidth,play.clientHeight)));bd.style.setProperty('--S',size+'px');}
function setup(){
  compactSprites();adoptFonts();
  if(KIT.defs){var definitions=el('div');definitions.innerHTML=KIT.defs;while(definitions.firstChild)doc.body.appendChild(definitions.firstChild);}
  wrap=el('main','',doc.body);wrap.id='wrap';wrap.setAttribute('aria-label','말 옮기기 윷판');
  wrap.innerHTML='<div class="pad-top"><div><span class="pad-eyebrow">우리 팀의 한 수</span><div id="team"><i class="team-dot" aria-hidden="true"></i><span class="name">윷판을 불러오는 중</span></div></div><span id="connection" class="wait"><i aria-hidden="true"></i><span>연결 중</span></span></div>'+ 
    '<div class="guide"><span class="step" id="step-one"><i>1</i>말 고르기</span><span class="step-arrow" aria-hidden="true">›</span><span class="step" id="step-two"><i>2</i>도착 칸 누르기</span><span id="stage-status">진행석과 연결 중</span></div>'+ 
    '<div class="results" id="results" aria-label="남은 윷 결과"></div><div id="play"><div id="bd"></div></div>'+ 
    '<div class="footer"><p id="hint">잠시만 기다려 주세요.</p><button type="button" id="cancel" hidden>선택 취소</button><button type="button" id="refresh" hidden>상태 다시 확인</button></div>'+ 
    '<div id="toast" role="status"></div><div id="announcement" class="sr-only" role="status" aria-live="polite"></div>';
  bd=doc.getElementById('bd');
  svgB=sv('svg',{class:'brd',viewBox:'0 0 100 100','aria-hidden':'true'},bd);
  var defs=sv('defs',{},svgB),gradient=sv('linearGradient',{id:'pad-board-fill',x1:'0',y1:'0',x2:'0',y2:'1'},defs);
  sv('stop',{offset:'0%','stop-color':'#f4ebd5'},gradient);sv('stop',{offset:'100%','stop-color':'#eaddbc'},gradient);
  sv('polygon',{points:'50,5.8 96,51.8 50,97.8 4,51.8',fill:'#b5a37c',stroke:'#a49168','stroke-width':'.4','stroke-linejoin':'round'},svgB);
  sv('polygon',{points:'50,4 96,50 50,96 4,50',fill:'url(#pad-board-fill)',stroke:'#c3b18b','stroke-width':'.55','stroke-linejoin':'round'},svgB);
  sv('polygon',{points:'50,6.5 93.5,50 50,93.5 6.5,50',fill:'none',stroke:'#d3c19a','stroke-width':'.4'},svgB);
  function line(a,b){var A=q(Pn[a]),B=q(Pn[b]);sv('line',{x1:A[0],y1:A[1],x2:B[0],y2:B[1],stroke:'#b6a47e','stroke-width':'1.45','stroke-linecap':'round'},svgB);sv('line',{x1:A[0],y1:A[1],x2:B[0],y2:B[1],stroke:'#f7efda','stroke-width':'.42','stroke-linecap':'round'},svgB);}
  [['END','O5'],['O5','O10'],['O10','O15'],['O15','END'],['O5','O15'],['O10','END']].forEach(function(pair){line(pair[0],pair[1]);});
  Object.keys(Pn).forEach(function(key){var p=q(Pn[key]),big=['END','O5','O10','O15','C'].indexOf(key)>=0;
    sv('circle',{cx:p[0],cy:p[1]+.45,r:big?4.1:2.65,fill:'#c2b08a'},svgB);
    sv('circle',{cx:p[0],cy:p[1],r:big?4.1:2.65,fill:big?'#ede0bd':'#fffbef',stroke:'#cab994','stroke-width':'.38'},svgB);
    if(big)sv('circle',{cx:p[0],cy:p[1],r:2.9,fill:'none',stroke:'#c8b68f','stroke-width':'.24'},svgB);
  });
  [['O1','도'],['O2','개'],['O3','걸'],['O4','윷']].forEach(function(pair){var p=q(Pn[pair[0]]);var label=sv('text',{x:p[0],y:p[1]+.8,'font-size':'1.75','font-weight':'700','text-anchor':'middle',fill:'#aa9c7d'},svgB);label.textContent=pair[1];});
  sv('g',{class:'pv'},svgB);
  layT=el('div','lay',bd);layP=el('div','lay',bd);layO=el('div','lay',bd);layFx=el('div','lay pad-effects',bd);layFx.setAttribute('aria-hidden','true');layP.style.zIndex='2';layO.style.zIndex='3';
  [[q(Pn.O5),[7,-4],'모'],[q(Pn.O10),[7,-1.5],'뒷모'],[q(Pn.O15),[-7,-4],'찌모'],[q(Pn.C),[5.7,-3.5],'방'],[q(Pn.END),[0,7],'출발','start']].forEach(function(item){var e=el('div','lab'+(item[3]?' '+item[3]:''),layT);e.textContent=item[2];e.style.left=(item[0][0]+item[1][0])+'%';e.style.top=(item[0][1]+item[1][1])+'%';});
  doc.getElementById('cancel').addEventListener('click',function(){if(isReady())send('select',null);});
  doc.getElementById('refresh').addEventListener('click',function(){tick();if(pending&&Date.now()-pending.at>8000&&Date.now()-lastSeen<4000){pending=null;sel=S.pv;draw();toast('입력이 아직 반영되지 않았어요. 판을 확인하고 다시 눌러 주세요.');}else if(connection!=='ok')toast('연결을 기다리고 있어요. 태블릿의 와이파이를 확인해 주세요.');});
  doc.addEventListener('keydown',function(event){keyboard=true;if(event.key==='Escape'){if(choice)closeChoices();else if(sel!=null&&isReady())send('select',null);}});
  doc.addEventListener('pointerdown',function(){keyboard=false;},true);
  addEventListener('resize',function(){clearTimeout(fitTimer);fitTimer=setTimeout(fit,40);});
  if(window.ResizeObserver)new ResizeObserver(fit).observe(doc.getElementById('play'));
  fit();
}
function avatar(team,n){var markup='<div class="figs'+(n>1?' piggyback':'')+'" aria-hidden="true">';for(var i=Math.min(n,4)-1;i>=1;i--)markup+='<div class="fig b'+i+'">'+KIT.spr[team%4]+'</div>';markup+='<div class="fig front">'+KIT.spr[team%4]+'</div>';return markup+(n>1?'<span class="cnt">'+n+'</span>':'')+'</div>';}
function piece(team,n,p,options){
  var e=at(p,'k-'+KIT.motion[team%4]+(options.can?' can':'')+(options.selected?' sel':'')+(options.dim?' dim':'')+(options.ghost?' ghost':''),layP);e.style.setProperty('--tc',HEX[team]);
  if(options.groupId!=null)e.dataset.group=String(options.groupId);
  el('div','base',e);if(options.can||options.selected)el('div','ring',e);el('div','pc',e,avatar(team,n));
  if(options.key!=null){var control=button(e,'tap',options.label,function(){tapPiece(options.key);});control.disabled=!isReady();control.dataset.focus='piece-'+options.key;control.dataset.piece=String(options.key);control.setAttribute('aria-pressed',options.selected?'true':'false');}
}
function selectedOptions(){return sel!=null&&S&&S.opts?(S.opts[String(sel)]||[]).filter(function(option){return resultFilter==='all'||option.r===resultFilter;}):[];}
function effect(option){if(option.finished)return '완주';var enemy=S.groups.some(function(g){return g.node===option.dest&&g.team!==S.turn;});if(enemy)return S.captureBonus&&!AGAIN[option.r]?'잡기 · 한 번 더':'잡기';var friend=S.groups.some(function(g){return g.node===option.dest&&g.team===S.turn&&!same(g.id,sel);});return friend?'우리 말 업기':'';}
function updateResults(){
  var res=doc.getElementById('results');res.innerHTML='<span class="result-label">쓸 결과</span>';
  if(!S||!S.pending.length){el('span','no-result',res).textContent='윷 결과를 기다리고 있어요';return;}
  var names=[],counts={};S.pending.forEach(function(result){if(!counts[result])names.push(result);counts[result]=(counts[result]||0)+1;});
  if(names.indexOf(resultFilter)<0)resultFilter='all';
  function add(result){var all=result==='all',active=resultFilter===result||names.length===1,label=all?'전체 경로':NM[result]+' '+STEPS[result]+'칸'+(counts[result]>1?' '+counts[result]+'개':'');var chip=button(res,'rchip'+(active?' on':''),label,function(){resultFilter=result;closeChoices(false);draw();});chip.innerHTML=all?'전체':esc(NM[result])+'<small>'+STEPS[result]+'칸'+(counts[result]>1?' · ×'+counts[result]:'')+'</small>';chip.setAttribute('aria-pressed',active?'true':'false');chip.dataset.focus='result-'+result;chip.disabled=!!pending||S.phase!=='move'||INITIAL!=null;}
  if(names.length>1)add('all');names.forEach(add);
}
function draw(){
  var focused=doc.activeElement&&doc.activeElement.dataset?doc.activeElement.dataset.focus:null;
  layP.innerHTML='';layO.innerHTML='';svgB.querySelector('.pv').innerHTML='';
  var name=doc.querySelector('#team .name'),step1=doc.getElementById('step-one'),step2=doc.getElementById('step-two'),stage=doc.getElementById('stage-status'),hint=doc.getElementById('hint');
  step1.className='step';step2.className='step';updateResults();
  if(!S){name.textContent='윷판을 불러오는 중';hint.textContent='진행석과 연결하고 있어요.';return;}
  var team=currentTeam(),moving=S.phase==='move',can={};(S.selectable||[]).forEach(function(key){can[String(key)]=1;});
  wrap.style.setProperty('--team',HEX[team]);name.textContent=S.names[team]+(S.phase==='over'?' · 승리!':' 차례');
  if(S.phase==='over'){stage.textContent='게임 종료';hint.textContent='모두 수고하셨습니다. 새 게임은 진행석에서 시작해요.';}
  else if(!moving){stage.textContent=S.throwReason==='capture'?'잡기! 한 번 더 던지세요':AGAIN[S.throwReason]?'한 번 더 던지세요':'윷을 던져 주세요';hint.textContent='진행석에서 윷 결과를 입력하면 말을 고를 수 있어요.';}
  else if(pending){stage.textContent=pending.kind==='move'?'이동을 반영하는 중':'선택을 맞추는 중';hint.textContent='잠시만 기다려 주세요. 스크린에도 함께 반영됩니다.';}
  else if(sel==null){step1.classList.add('active');stage.textContent='우리 팀 말을 골라요';hint.textContent='새 말 또는 판 위에서 테두리가 빛나는 말을 누르세요.';}
  else{step1.classList.add('done');step2.classList.add('active');stage.textContent='갈 곳을 골라요';hint.textContent='테두리가 표시된 도착 칸을 누르면 이동합니다.';}
  var cancel=doc.getElementById('cancel');cancel.hidden=sel==null||!moving;cancel.disabled=!isReady();
  if(connection==='offline')hint.textContent='연결이 늦어지고 있어요. 와이파이 연결을 확인해 주세요.';
  var pieces=S.groups.slice().filter(function(g){return Pn[g.node];}).sort(function(a,b){return q(Pn[a.node])[1]-q(Pn[b.node])[1];});
  pieces.forEach(function(g){var available=moving&&!!can[String(g.id)];piece(g.team,g.n,q(Pn[g.node]),{can:available&&sel==null&&!pending,selected:same(sel,g.id),dim:moving&&g.team===S.turn&&!available,key:available?g.id:null,groupId:g.id,label:S.names[g.team]+' 말 '+g.n+'개, '+(NODE[g.node]||g.node)+(same(sel,g.id)?', 선택됨':' 선택')});});
  Array.prototype.forEach.call(layT.querySelectorAll('.tray'),function(e){e.remove();});
  if(S.phase!=='over'&&S.home[S.turn]>0){var canNew=moving&&!!can.new;piece(S.turn,1,WAIT,{can:canNew&&sel==null&&!pending,selected:same(sel,'new'),dim:!canNew,ghost:true,key:canNew?'new':null,label:S.names[S.turn]+' 새 말 선택, 대기 '+S.home[S.turn]+'개'});var tray=el('div','tray',layT);tray.style.left=WAIT[0]+'%';tray.style.top=(WAIT[1]+8)+'%';tray.innerHTML='<strong>새 말</strong> · 대기 '+S.home[S.turn];}
  if(moving&&sel!=null){
    var grouped={};selectedOptions().forEach(function(option){var id=option.dest+'|'+!!option.finished;if(!grouped[id])grouped[id]=[];grouped[id].push(option);});
    Object.keys(grouped).forEach(function(id){var options=grouped[id],first=options[0],to=first.finished?EXIT:q(Pn[first.dest]);if(!to)return;
      var pts=(first.nodes||[]).filter(function(n){return Pn[n];}).map(function(n){return q(Pn[n]);});if(same(sel,'new'))pts.unshift(WAIT);if(first.finished)pts.push(EXIT);
      if(pts.length>1)sv('polyline',{points:pts.map(function(p){return p.join(',');}).join(' '),fill:'none',stroke:HEX[S.turn],'stroke-width':'.6','stroke-dasharray':'1.1 1.1','stroke-linecap':'round','stroke-linejoin':'round',opacity:'.82'},svgB.querySelector('.pv'));
      var target=at(to,'',layO);target.style.setProperty('--tc',HEX[S.turn]);el('div','spot',target);
      var names=options.map(function(option){return NM[option.r];}).join(' · '),note=effect(first),label=el('div','olab'+(first.finished?' exit':''),target);
      label.innerHTML=esc(names)+(note?'<small>'+esc(note)+'</small>':'');
      var key=sel,version=S.ver,control=button(target,'tapd',names+' → '+(first.finished?'완주':NODE[first.dest]||first.dest)+(note?', '+note:''),function(){if(!S||S.ver!==version)return;if(options.length===1)tapDest(key,first.i);else openChoices(key,options);});
      control.disabled=!isReady();control.dataset.focus='dest-'+id;control.dataset.dest=first.finished?'finish':first.dest;
    });
    if(!selectedOptions().length&&!pending)hint.textContent='이 말로 쓸 수 없는 결과예요. 다른 결과나 말을 고르세요.';
  }
  updateConnection();
  if(keyboard&&focused){var candidate=Array.prototype.find.call(doc.querySelectorAll('[data-focus]'),function(e){return e.dataset.focus===focused&&!e.disabled;});if(candidate)candidate.focus({preventScroll:true});}
}
function openChoices(key,options){
  if(!isReady())return;closeChoices(false);choice={key:key,version:S.ver,options:options};
  var backdrop=el('section','chooser',wrap);backdrop.id='chooser';backdrop.setAttribute('role','dialog');backdrop.setAttribute('aria-modal','true');backdrop.setAttribute('aria-labelledby','choice-title');
  var card=el('div','choice-card',backdrop),head=el('div','choice-head',card);
  el('div','',head,'<h2 id="choice-title">어떤 결과를 쓸까요?</h2><p>같은 칸에 도착해요. 남겨 둘 결과를 생각해 보세요.</p>');
  var close=button(head,'choice-close','결과 선택 닫기',function(){closeChoices();});close.textContent='×';
  var choices=el('div','choice-buttons',card);
  options.forEach(function(option){var rest=S.pending.filter(function(_,index){return index!==option.i;}).map(function(result){return NM[result];}).join(' · ')||'없음';var b=button(choices,'choice-button',NM[option.r]+' 사용, 남는 결과 '+rest,function(){var version=choice&&choice.version;closeChoices(false);if(S.ver===version)tapDest(key,option.i);});b.innerHTML='<b>'+esc(NM[option.r])+'로 '+(option.finished?'완주하기':'이동하기')+'</b><small>남는 결과<br>'+esc(rest)+'</small>';});
  backdrop.addEventListener('click',function(event){if(event.target===backdrop)closeChoices();});
  backdrop.addEventListener('keydown',function(event){if(event.key!=='Tab')return;var buttons=backdrop.querySelectorAll('button'),first=buttons[0],last=buttons[buttons.length-1];if(event.shiftKey&&doc.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&doc.activeElement===last){event.preventDefault();first.focus();}});
  choices.querySelector('button').focus({preventScroll:true});
}
function closeChoices(restoreFocus){var e=doc.getElementById('chooser');if(e)e.remove();choice=null;if(restoreFocus!==false&&keyboard){var first=doc.querySelector('.tapd:not(:disabled)');if(first)first.focus({preventScroll:true});}}
function tapPiece(key){if(!isReady()||S.phase!=='move')return;closeChoices(false);send('select',same(sel,key)?null:key);}
function tapDest(key,index){if(!isReady()||S.phase!=='move'||!same(sel,key))return;var options=S.opts[String(key)]||[];if(!options.some(function(option){return option.i===index;}))return;closeChoices(false);send('move',key,index);}
function read(){
  if(INITIAL)return INITIAL;if(!PD)return null;var markers=PD.querySelectorAll('.yx-pad-st'),best=null;
  for(var i=0;i<markers.length;i++){
    var marker=markers[i],raw=marker.getAttribute('title'),cached=markerCache.get(marker);
    if(!cached||cached.raw!==raw){cached={raw:raw,value:null};try{cached.value=JSON.parse(raw);}catch(e){}markerCache.set(marker,cached);}
    var item=cached.value;if(item&&(!best||item.heartbeat>best.heartbeat))best=item;
  }
  return best;
}
function clearFeedback(clearToast){
  clearTimeout(feedbackTimer);feedbackTimer=0;
  feedbackAnimations.forEach(function(a){try{a.cancel();}catch(e){}});feedbackAnimations=[];
  if(layFx)layFx.innerHTML='';if(wrap)wrap.removeAttribute('data-feedback');
  if(clearToast){clearTimeout(toastTimer);var message=doc.getElementById('toast');if(message)message.classList.remove('on');}
}
function feedbackAnimate(node,frames,options){
  if(!node||!node.animate||reduced)return;
  try{feedbackAnimations.push(node.animate(frames,options));}catch(e){}
}
function eventKey(state){var last=state.last||{};return last.at==null?null:[state.game_id||state.server||'',last.kind,last.at,last.id==null?last.team:last.id].join('|');}
function feedback(next,old,restarted){
  var key=eventKey(next),last=next.last||{},reset=['undo','reset','restore','import'].indexOf(last.kind)>=0;
  if(key===feedbackKey&&!restarted)return;
  feedbackKey=key;clearFeedback(true);
  // The first snapshot, reconnect, and history changes are already canonical.
  // Selection versions retain the same event key and never replay this layer.
  if(!old||restarted||reset||!key)return;
  if(last.kind==='nak'){toast('낙! 이번 차례를 마칩니다.');return;}
  if(last.kind!=='move'||(!last.caught&&!last.stacked))return;
  var merged=next.groups.find(function(g){return same(g.id,last.id);}),total=Number(last.resultN)||(merged&&merged.n)||Number(last.n)||1;
  var captured=Number(last.caughtN)||1,kind=last.caught?'catch':'stack';
  toast(last.caught?'잡았다! '+captured+'개의 말을 출발로!'+(last.bonusAwarded===true?' 한 번 더 던져요.':''):'업었다! '+(Number(last.n)||1)+'개 + '+(Number(last.stackedN)||Math.max(1,total-(Number(last.n)||1)))+'개, 함께 '+total+'개!');
  if(reduced)return;
  var node=last.caught||(merged&&merged.node)||(last.nodes||[]).slice(-1)[0];if(!Pn[node])return;
  var p=q(Pn[node]),size=bd.clientWidth,zone=at(p,'pad-burst',layFx);wrap.dataset.feedback=kind;
  el('div','pad-impact '+kind,zone);
  for(var i=0;i<4;i++){var star=el('i','pad-star',zone);star.style.setProperty('--dx',((i-1.5)*size*.027)+'px');star.style.setProperty('--dy',(-size*(.09+(i%2)*.025))+'px');}
  var current=Array.prototype.find.call(layP.querySelectorAll('[data-group]'),function(e){return same(e.dataset.group,last.id);});
  if(current)feedbackAnimate(current.querySelector('.figs'),[{transform:'translateY(0) rotate(0) scale(1)'},{transform:'translateY('+size*.01+'px) rotate(-5deg) scale(1.06,.88)',offset:.22},{transform:'translateY(-'+size*.025+'px) rotate(4deg) scale(.98,1.03)',offset:.55},{transform:'translateY(0) rotate(0) scale(1)'}],{duration:520,easing:'ease-out'});
  if(last.caught){
    var groups=Array.isArray(last.caughtPieces)&&last.caughtPieces.length?last.caughtPieces:old.groups.filter(function(g){return g.node===node&&g.team!==last.team;}),figures=[];
    for(var round=0;round<2&&figures.length<2;round++)groups.forEach(function(g){if(g.n>round&&figures.length<2)figures.push(g);});
    figures.forEach(function(g,index){
      var start=[p[0]+index*1.8,p[1]-index],ghost=at(start,'pad-ghost k-'+KIT.motion[g.team%4],layFx);ghost.style.setProperty('--tc',HEX[g.team]);el('div','pc',ghost,avatar(g.team,1));
      feedbackAnimate(ghost,[{left:start[0]+'%',top:start[1]+'%',opacity:1},{left:(start[0]*.7+WAIT[0]*.3)+'%',top:(start[1]*.7+WAIT[1]*.3-9)+'%',opacity:1,offset:.4},{left:WAIT[0]+'%',top:WAIT[1]+'%',opacity:0}],{duration:700+index*90,delay:index*55,fill:'both',easing:'ease-out'});
      feedbackAnimate(ghost.querySelector('.figs'),[{transform:'rotate(0) scale(1)'},{transform:'rotate('+(index?175:-160)+'deg) scale(.35)'}],{duration:700+index*90,delay:index*55,fill:'both',easing:'ease-in'});
    });
  }
  feedbackTimer=setTimeout(function(){clearFeedback(false);},1050);
}
function updateConnection(){
  var old=connection,age=Date.now()-lastSeen;
  connection=INITIAL?'preview':!lastSeen?'waiting':age>12000?'offline':age>5000?'waiting':'ok';
  var pill=doc.getElementById('connection'),state=pill.querySelector('span');
  if(!connectionPainted||old!==connection){connectionPainted=true;pill.className=connection==='ok'||connection==='preview'?'':connection==='offline'?'off':'wait';state.textContent=connection==='ok'?'연결됨':connection==='preview'?'화면 미리보기':connection==='offline'?'연결 확인':'동기화 중';}
  var slow=!!pending&&Date.now()-pending.at>8000,refresh=doc.getElementById('refresh'),hideRefresh=!slow&&connection!=='offline';if(refresh.hidden!==hideRefresh)refresh.hidden=hideRefresh;
  if(slow){var stage=doc.getElementById('stage-status'),hint=doc.getElementById('hint');if(stage.textContent!=='입력 확인이 늦어지고 있어요')stage.textContent='입력 확인이 늦어지고 있어요';if(hint.textContent!=='상태를 다시 확인한 뒤 다음 동작을 진행해 주세요.')hint.textContent='상태를 다시 확인한 뒤 다음 동작을 진행해 주세요.';}
  if(old!==connection&&S){Array.prototype.forEach.call(doc.querySelectorAll('.tap,.tapd,#cancel'),function(b){b.disabled=!isReady();});}
}
function receive(next){
  if(!next||typeof next.ver!=='number'||!Array.isArray(next.groups)||!Array.isArray(next.pending))return;
  var restarted=!!S&&(next.server!==S.server||!!(S.game_id&&next.game_id&&S.game_id!==next.game_id));
  if(restarted||next.heartbeat>latestHeartbeat){latestHeartbeat=next.heartbeat;lastSeen=Date.now();}
  updateConnection();
  if(S&&!restarted&&next.ver<=S.ver)return;
  var old=S,action=pending;
  if(restarted){pending=null;action=null;closeChoices(false);}
  else if(action&&next.ver>action.version){pending=null;}
  S=next;sel=next.pv==null?null:next.pv;
  if(sel!=null&&(S.selectable||[]).map(String).indexOf(String(sel))<0)sel=null;
  if(!old||old.phase!==S.phase||old.pending.join(',')!==S.pending.join(','))resultFilter='all';
  if(choice&&choice.version!==S.ver)closeChoices(false);
  draw();
  if(action&&action.kind==='select'&&same(sel,action.key)&&sel!=null){announce('말을 골랐습니다. 도착 칸을 누르세요.');if(keyboard){var first=doc.querySelector('.tapd:not(:disabled)');if(first)first.focus({preventScroll:true});}}
  else if(action&&action.kind==='move'&&S.last&&S.last.kind==='move'){announce(S.last.finished?'완주했습니다.':'말을 옮겼습니다.');}
  feedback(S,old,restarted);
  if(restarted)toast('진행석과 다시 연결했어요. 현재 판을 확인해 주세요.');
}
function tick(){adoptFonts();var n=read();if(n)receive(n);else updateConnection();}
function hasMarker(node){return node&&node.nodeType===1&&(node.matches('.yx-pad-st')||node.querySelector('.yx-pad-st'));}
function markerChanged(record){return record.type==='attributes'?hasMarker(record.target):Array.prototype.some.call(record.addedNodes,hasMarker)||Array.prototype.some.call(record.removedNodes,hasMarker);}
function queueTick(){if(tickQueued)return;tickQueued=true;window.requestAnimationFrame(function(){tickQueued=false;tick();});}
setup();draw();tick();setInterval(tick,1000);
// Follow only the shared state marker, rather than every Streamlit DOM change.
// The interval remains as a heartbeat/slow-response fallback.
if(PD)try{new MutationObserver(function(records){if(records.some(markerChanged))queueTick();}).observe(PD.body,{subtree:true,attributes:true,attributeFilter:['title'],childList:true});}catch(e){}
window.__pad={state:function(){return S;},sel:function(){return sel;},pending:function(){return pending;},tapPiece:tapPiece,tapDest:tapDest,receive:receive};
})();
"""


@lru_cache(maxsize=2)
def _pad_html(kit: str, initial: str, sprite_css: str, shared_fonts: bool) -> str:
    code = (_JS.replace("__KIT__", kit).replace("__INITIAL__", initial)
            .replace("__SHARED_FONTS__", "true" if shared_fonts else "false"))
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<style>{_CSS}{sprite_css}</style></head><body><script>{code}</script></body></html>')


def pad_html(preview_state: dict | None = None, *, shared_fonts: bool = False) -> str:
    """Cached iframe shell; optional state makes a self-contained visual preview.

    Live Streamlit can share its ``style#yut-fonts`` instead of sending the same
    font data again inside the iframe. The default remains fully standalone.
    """
    kit = sprites.js_bundle(include_css=False).replace("</", "<\\/")
    initial = json.dumps(pad_state(preview_state) if preview_state is not None else None,
                         ensure_ascii=False).replace("</", "<\\/")
    sprite_css = sprites.SPRITE_BASE_CSS if shared_fonts else sprites.SPRITE_CSS
    return _pad_html(kit, initial, sprite_css, shared_fonts)
