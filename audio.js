/* 윷놀이 한마당: original retro folk music and synthesized game sounds.
 * No recorded samples, external libraries, network requests, or borrowed tunes.
 *
 * Browser: const a = YutAudio.create({music:true,effects:true,volume:.35,
 *              track:'folk',onChange: status => { ... }});
 *          await a.unlock(); // call from an explicit click / tap
 *          a.play('catch'); a.setMusic(false); a.setEffects(true);
 *          a.setVolume(.4); a.setMuted(true); a.setTrack('trot');
 *          a.setState(game); a.status(); a.dispose();
 *
 * Offline/Node: require('./audio.js').renderWav({track:'folk',volume:.65});
 * The offline exporter and live Web Audio player use the SAME score and PCM
 * instrument synthesis. BufferSource voices keep live CPU and node counts low.
 */
(function (root) {
  'use strict';

  var VERSION = '1.0.0';
  var TAU = Math.PI * 2;
  var LIVE_RATE = 22050;
  var MIX_GAIN = 2.5;
  var VOICE_LIMIT = 64;
  var LOOKAHEAD = .22;
  var TICK_MS = 50;
  var EPS = .00001;
  var ECHOES = [[.091, .105], [.173, .074], [.281, .038]];
  var DUCK = {catch:[.45,.62],stack:[.48,.62],finish:[.43,.80],winner:[.30,2.60],bonus:[.58,.48]};
  var TRACKS = [
    {id:'folk', name:'장터 풍류', bars:32, meter:'6/8', bpm:88,
      description:'가야금·거문고를 떠올리는 뜯는 소리, 대금풍 숨결, 장구와 북의 여섯 박자'},
    {id:'trot', name:'잔칫날 트로트', bars:32, meter:'4/4', bpm:116,
      description:'복고풍 리드와 오르간, 둥근 베이스, 쿵짝 장단의 잔치 음악'}
  ];
  var GAINS = {gayageum:.30, geomungo:.33, daegeum:.36, accordion:.30,
    organ:.17, bass:.34, bell:.21, buk:.40, jangguLow:.31, jangguHigh:.27,
    metal:.17, shaker:.13, wood:.30, kick:.40, snare:.23, hat:.14,
    whoosh:.27, rolling:.29, boing:.30};

  function clamp(x,a,b) { return Math.min(b,Math.max(a,x)); }
  function finite(x,fallback) { return typeof x==='number' && isFinite(x) ? x : fallback; }
  function midi(n) { return 440*Math.pow(2,(n-69)/12); }
  function mod(x,n) { return ((x%n)+n)%n; }
  function hash(s) {
    var h=2166136261;
    for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}
    return h>>>0;
  }
  function random(seed) {
    var s=(seed>>>0)||1;
    return function(){s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};
  }
  function soft(x) { x=clamp(x,-1,1); return x/(1+.16*Math.abs(x)); }
  function degree(scale,k) {
    var oct=Math.floor(k/scale.length);
    return scale[mod(k,scale.length)]+oct*12;
  }
  function trackInfo(id) { return TRACKS[id==='trot'?1:0]; }
  function add(events,t,d,instrument,note,velocity,pan,extra) {
    var e={t:Math.max(0,t),d:Math.max(.015,d),instrument:instrument,
      note:finite(note,60),v:clamp(finite(velocity,.7),0,1.3),pan:clamp(finite(pan,0),-1,1),bus:'music'};
    if(extra)Object.keys(extra).forEach(function(k){e[k]=extra[k];});
    events.push(e);return e;
  }

  // Each row is one complete bar: [pentatonic degree, eighth-note units].
  // Four eight-bar phrases develop the tune; the last phrase leads home.
  var FOLK_MELODY = [
    [[5,1],[6,.5],[7,.5],[8,1],[7,1],[6,1],[5,1]],
    [[3,1],[5,2],[6,1],[7,1],[6,1]],
    [[5,1.5],[7,.5],[8,1],[9,1],[8,1],[7,1]],
    [[6,1],[5,2],[3,2],[null,1]],
    [[5,1],[6,1],[7,1],[8,1],[10,1],[9,1]],
    [[8,1.5],[7,.5],[6,1],[7,1],[6,1],[5,1]],
    [[3,1],[5,1],[6,1],[7,1.5],[6,.5],[5,1]],
    [[6,1],[5,3],[null,2]],
    [[5,.5],[6,.5],[7,2],[8,1],[7,1],[5,1]],
    [[6,1],[7,1],[8,1],[6,2],[3,1]],
    [[5,1],[7,1],[9,1],[8,1.5],[7,.5],[6,1]],
    [[7,1],[6,1],[5,2],[3,1],[null,1]],
    [[3,1],[5,.5],[6,.5],[7,1],[8,2],[7,1]],
    [[9,1],[8,1],[7,1],[6,1],[5,1],[6,1]],
    [[7,1.5],[8,.5],[9,1],[8,1],[6,1],[3,1]],
    [[6,1],[5,2],[null,1],[7,1],[8,1]],
    [[10,2],[9,1],[8,1],[7,1],[8,1]],
    [[9,1],[10,.5],[11,.5],[10,1],[8,2],[7,1]],
    [[8,1],[9,1],[10,1],[12,1],[11,1],[10,1]],
    [[9,1.5],[8,.5],[7,2],[null,2]],
    [[7,1],[8,1],[9,1],[10,1.5],[9,.5],[8,1]],
    [[10,1],[8,1],[7,1],[6,1],[7,1],[8,1]],
    [[9,1.5],[10,.5],[8,1],[7,1],[6,1],[5,1]],
    [[6,1],[7,1],[8,2],[null,1],[6,1]],
    [[5,1],[6,.5],[7,.5],[8,2],[7,1],[5,1]],
    [[3,1],[5,1],[6,1],[7,1],[6,1],[3,1]],
    [[5,1.5],[7,.5],[8,1],[9,1],[7,1],[6,1]],
    [[5,2],[3,1],[5,1],[null,2]],
    [[7,1],[8,1],[10,1],[9,1],[8,1],[7,1]],
    [[6,1],[7,.5],[8,.5],[7,1],[6,1],[5,1],[3,1]],
    [[5,1],[6,1],[7,1],[6,1],[3,1],[6,1]],
    [[5,4],[null,2]]
  ];
  var TROT_MELODY = [
    [[5,1],[5,.5],[6,.5],[7,1],[8,1],[7,1],[6,1],[5,2]],
    [[3,1],[5,1],[6,2],[7,1],[6,1],[5,1],[3,1]],
    [[5,1],[7,1],[8,1],[10,1],[9,1],[8,1],[7,2]],
    [[6,1.5],[5,.5],[3,2],[null,1],[3,1],[5,2]],
    [[6,1],[7,.5],[8,.5],[9,2],[8,1],[7,1],[6,2]],
    [[8,1],[7,1],[5,1],[6,1],[7,1.5],[6,.5],[5,2]],
    [[3,1],[5,1],[6,1],[7,1],[8,1],[7,1],[6,1],[3,1]],
    [[6,1],[5,3],[null,2],[3,1],[4,1]],
    [[5,1],[7,1],[8,1.5],[7,.5],[6,1],[5,1],[3,2]],
    [[6,.5],[7,.5],[8,1],[7,1],[6,1],[5,2],[3,2]],
    [[5,1],[6,1],[7,1],[9,1],[10,2],[8,2]],
    [[7,1.5],[6,.5],[5,2],[null,1],[6,1],[7,2]],
    [[8,1],[9,.5],[10,.5],[9,1],[8,1],[7,1],[5,1],[6,2]],
    [[7,1],[6,1],[5,1],[3,1],[5,2],[6,2]],
    [[7,1],[8,1],[9,1],[8,1],[7,1],[6,1],[5,1],[3,1]],
    [[6,1],[5,3],[null,1],[7,1],[8,1],[9,1]],
    [[10,2],[10,1],[9,1],[8,1],[7,1],[8,2]],
    [[9,1],[10,.5],[11,.5],[10,1],[8,1],[9,2],[8,2]],
    [[7,1],[8,1],[10,1],[12,1],[11,1],[10,1],[9,2]],
    [[8,1.5],[7,.5],[6,2],[null,1],[6,1],[7,2]],
    [[8,1],[9,1],[10,2],[9,1],[8,1],[7,2]],
    [[9,1],[8,.5],[7,.5],[6,1],[7,1],[8,2],[6,2]],
    [[7,1],[8,1],[9,1],[10,1],[8,1],[7,1],[6,1],[3,1]],
    [[6,1],[5,3],[null,2],[6,1],[7,1]],
    [[8,1],[7,.5],[6,.5],[5,2],[7,1],[8,1],[10,2]],
    [[9,1],[8,1],[7,1],[6,1],[5,2],[3,2]],
    [[5,1],[6,1],[7,1.5],[8,.5],[9,1],[8,1],[7,2]],
    [[6,1.5],[5,.5],[3,2],[null,1],[5,1],[6,2]],
    [[7,1],[8,1],[10,2],[9,1],[8,1],[7,2]],
    [[6,1],[7,.5],[8,.5],[7,1],[6,1],[5,1],[3,1],[5,2]],
    [[3,1],[5,1],[6,1],[7,1],[6,1],[3,1],[6,1],[5,1]],
    [[5,5],[null,3]]
  ];
  var scoreCache={};
  function compose(id) {
    id=id==='trot'?'trot':'folk';
    if(scoreCache[id])return scoreCache[id];
    var isFolk=id==='folk',meta=trackInfo(id),unit=isFolk?60/(meta.bpm*3):60/(meta.bpm*2);
    var units=isFolk?6:8,bar=unit*units,events=[],rnd=random(isFolk?231109:572041);
    var scale=isFolk?[55,57,59,62,64]:[57,59,61,64,66];
    var chords=isFolk?{
      G:[43,50,55,59],C:[48,55,60,64],D:[38,45,50,57],Em:[40,47,52,55],Am:[45,52,57,60]
    }:{A:[45,52,57,61],D:[38,45,50,54],E:[40,47,52,56],Fm:[42,49,54,57],Bm:[47,54,59,62]};
    var progression=isFolk?
      ['G','G','C','D','G','Em','Am','D','G','Em','C','D','C','G','Am','D','Em','C','G','D','Em','C','Am','D','G','G','C','D','Em','C','D','G']:
      ['A','A','D','E','D','A','E','A','A','Fm','D','E','D','A','Bm','E','Fm','D','A','E','D','Fm','Bm','E','A','Fm','D','E','D','A','E','A'];
    var melody=isFolk?FOLK_MELODY:TROT_MELODY;
    for(var b=0;b<32;b++) {
      var chord=chords[progression[b]],at=b*bar,phrase=Math.floor(b/8),lead=isFolk?(b<4||b===24||b===25?'gayageum':'daegeum'):'accordion';
      var cursor=0;
      melody[b].forEach(function(pair,j){
        var n=pair[0],len=pair[1];
        if(n!==null) {
          var swing=!isFolk&&cursor%1===.5?.025:0;
          var human=j===0?0:(rnd()-.5)*.009;
          var v=(isFolk?.76:.78)+(rnd()-.5)*.10;
          var note=degree(scale,n);
          add(events,at+cursor*unit+swing+human,len*unit*(lead==='gayageum'?.88:.94),lead,note,v,isFolk?.16:.10,{bend:lead==='daegeum'&&len>=1.5?-.12:0});
          if(isFolk && phrase===2 && j===0 && b%2===0)
            add(events,at+cursor*unit+.012,.30,'bell',note+12,.22,.42);
        }
        cursor+=len;
      });
      if(Math.abs(cursor-units)>.00001)throw new Error('Invalid music bar '+id+':'+b);
      if(isFolk) {
        // Five plucks leave a pocket for the main melody and the drum response.
        var arp=[0,1.5,3,4,5],order=b%2?[0,2,1,3,2]:[0,1,2,3,1];
        arp.forEach(function(step,j){
          var nn=chord[order[j]]+(j===3?12:0);
          add(events,at+step*unit+(j%2?.007:0),unit*.90,'gayageum',nn,.37+(j===0?.13:0),-.34+(j%2)*.06);
        });
        add(events,at,unit*2.3,'geomungo',chord[0]-12,.68,-.10);
        add(events,at+3*unit,unit*1.8,'geomungo',chord[1]-12,.46,-.10);
        if(b%4===3 && b!==31)add(events,at+5.5*unit,unit*.40,'gayageum',chord[2]+12,.41,-.22);
        add(events,at,.22,'jangguLow',50,.61,-.18);
        add(events,at+3*unit,.20,'jangguLow',52,.48,-.18);
        [2,4.5,5.5].forEach(function(step,j){
          if(b%4===3||j<2)add(events,at+step*unit,.12,'jangguHigh',66+j,.40+(j===1?.12:0),.23);
        });
        for(var h=0;h<6;h++)add(events,at+(h+.04)*unit,.07,'shaker',72,(h%3===0?.34:.19),.43);
        if(b%4===0)add(events,at,.35,'buk',40,.66,-.02);
        if(b===0||b===16||b===24)add(events,at,.75,'metal',79,.33,.34);
        if(b%8===7) {
          [4.5,5,5.5].forEach(function(step,j){add(events,at+step*unit,.10,'wood',72+j*2,.30+j*.06,.12);});
        }
      } else {
        for(var q=0;q<4;q++) {
          var bt=at+q*2*unit;
          add(events,bt,unit*1.20,'bass',q%2?chord[1]-12:chord[0],q%2?.69:.81,-.08);
          add(events,bt,.24,'kick',36,q%2?.45:.64,0);
          if(q%2===1) {
            chord.slice(1).forEach(function(n,j){add(events,bt+.013,unit*1.10,'organ',n,.62-j*.08,-.22+j*.17);});
            add(events,bt,.15,'snare',62,.55,.12);
          }
          add(events,bt+unit,.07,'hat',78,.36,.35);
          add(events,bt,.06,'hat',78,.22,.35);
        }
        if(b%2===0) {
          add(events,at+3*unit,unit*.68,'gayageum',chord[2]+12,.32,-.42);
          add(events,at+7*unit,unit*.68,'gayageum',chord[3]+12,.29,-.42);
        }
        if(b===0||b===16||b===24)add(events,at,.70,'metal',82,.27,.35);
        if(b%8===7 && b!==31) {
          [6.5,7,7.5].forEach(function(step,j){add(events,at+step*unit,.11,'snare',65+j,.30+j*.06,.16);});
        }
      }
    }
    events.sort(function(a,b){return a.t-b.t;});
    var score={id:id,name:meta.name,bars:32,meter:meta.meter,bpm:meta.bpm,
      unit:unit,barDuration:bar,duration:bar*32,events:events};
    scoreCache[id]=score;return score;
  }

  function tailFor(inst) {
    return {gayageum:.70,geomungo:.65,daegeum:.20,accordion:.15,organ:.12,
      bass:.13,bell:.85,metal:.50,whoosh:.10,rolling:.12,boing:.18}[inst]||.10;
  }
  function smoothEnv(t,d,a,r) {
    if(t<0||t>=d+r)return 0;
    if(t<a){var z=t/a;return z*z*(3-2*z);}
    if(t<=d)return 1;
    var v=(d+r-t)/r;return v*v;
  }
  function makeOscillators(f,ratios,weights,rate,seed) {
    var rnd=random(seed),out=[];
    for(var i=0;i<ratios.length;i++) {
      var freq=f*ratios[i];if(freq>rate*.43)continue;
      var step=TAU*freq/rate,phase=rnd()*TAU;
      out.push({s:Math.sin(phase),c:Math.cos(phase),ss:Math.sin(step),cc:Math.cos(step),w:weights[i],decay:1});
    }
    return out;
  }
  function sumOsc(osc) {
    var y=0;
    for(var k=0;k<osc.length;k++){
      var o=osc[k],s=o.s*o.cc+o.c*o.ss;o.c=o.c*o.cc-o.s*o.ss;o.s=s;y+=s*o.w;o.w*=o.decay;
    }
    return y;
  }
  function voicePCM(e,rate) {
    var inst=e.instrument,d=e.d,release=tailFor(inst),len=Math.max(8,Math.ceil((d+release)*rate));
    var out=new Float32Array(len),f=midi(e.note),seed=hash(inst+':'+e.note+':'+d.toFixed(3)),rnd=random(seed);
    var osc,noise=0,lp=0,prev=0,phase=0,phase2=0,vib=0,y=0,t,env,i;
    if(inst==='gayageum'||inst==='geomungo'||inst==='bell') {
      var pluck=inst!=='bell',low=inst==='geomungo';
      var ratios=pluck?[1,2,3.006,4.012,5.025,6.04]:[1,2.755,5.404,8.933];
      var weights=pluck?(low?[.76,.25,.11,.07,.035,.02]:[.63,.32,.19,.12,.067,.035]):[.66,.24,.11,.04];
      osc=makeOscillators(f,ratios,weights,rate,seed);
      osc.forEach(function(o,k){var decay=(low?.80:pluck?.59:.66)/(1+k*.58);o.decay=Math.exp(-1/(rate*decay));});
      for(i=0;i<len;i++){
        t=i/rate;noise=rnd()*2-1;lp+=.22*(noise-lp);
        env=smoothEnv(t,d,pluck?.003:.005,release);
        y=sumOsc(osc)+(pluck?(noise-lp)*.11*Math.exp(-t*125):0);
        out[i]=y*env*.80;
      }
    } else if(inst==='daegeum') {
      var breathLP=0,airLP=0,pulse=0,bend=finite(e.bend,0);
      for(i=0;i<len;i++) {
        t=i/rate;noise=rnd()*2-1;breathLP+=.34*(noise-breathLP);airLP+=.075*(noise-airLP);
        vib=Math.sin(TAU*5.15*t)*.0035*clamp((t-.12)*4,0,1);
        var fq=f*Math.pow(2,bend*Math.exp(-t*20)/12)*(1+vib);
        phase+=TAU*fq/rate;
        env=smoothEnv(t,d,.045,release);
        pulse=.68*Math.sin(phase)+.19*Math.sin(2*phase+.3)+.065*Math.sin(3*phase+.6);
        out[i]=(pulse+(breathLP-airLP)*.26+noise*.025*Math.exp(-t*40))*env*.73;
      }
    } else if(inst==='accordion'||inst==='organ'||inst==='bass') {
      var bass=inst==='bass',organ=inst==='organ';
      osc=makeOscillators(f,bass?[1,2,3,5]:organ?[1,2,3,4,6]:[1,2,3,4,5,6,8],
        bass?[.84,.17,.12,.025]:organ?[.50,.34,.17,.10,.045]:[.53,.34,.22,.13,.075,.04,.022],rate,seed);
      var drift=TAU*f*1.003/rate,step=TAU*f/rate;
      for(i=0;i<len;i++) {
        t=i/rate;phase2+=drift;phase+=step;
        env=smoothEnv(t,d,bass?.008:.018,release);
        var trem=organ?(.97+.03*Math.sin(TAU*5.5*t)):(.96+.04*Math.sin(TAU*4.4*t));
        y=sumOsc(osc)+(bass?0:.08*Math.sin(phase2));
        if(bass)y*=Math.exp(-t*2.2);
        out[i]=y*env*trem*.80;
      }
    } else if(inst==='buk'||inst==='kick'||inst==='jangguLow'||inst==='jangguHigh'||inst==='wood') {
      var wood=inst==='wood',high=inst==='jangguHigh',janggu=inst.indexOf('janggu')===0;
      var base=wood?midi(e.note)*.86:high?235:janggu?118:inst==='buk'?72:57;
      var dec=wood?.043:high?.075:janggu?.13:inst==='buk'?.19:.135;
      for(i=0;i<len;i++) {
        t=i/rate;var fq=base*(1+(wood?.05:high?.20:.62)*Math.exp(-t*(wood?95:38)));
        phase+=TAU*fq/rate;noise=rnd()*2-1;lp+=.24*(noise-lp);
        env=(1-Math.exp(-t*1700))*Math.exp(-t/dec);
        y=Math.sin(phase)+(wood?.45:.30)*Math.sin(phase*(wood?1.67:1.54))+.13*Math.sin(phase*2.71);
        y+=noise*(wood?.33:janggu?.35:.20)*Math.exp(-t*70);
        out[i]=y*env*.70*smoothEnv(t,d,.001,release);
      }
    } else if(inst==='snare'||inst==='shaker'||inst==='hat'||inst==='metal') {
      var metal=inst==='metal',snare=inst==='snare',hat=inst==='hat';
      osc=makeOscillators(metal?750:330,[1,1.47,2.09,2.73,4.17,5.41],[.33,.24,.18,.14,.10,.08],rate,seed);
      for(i=0;i<len;i++) {
        t=i/rate;noise=rnd()*2-1;lp+=(snare?.25:.50)*(noise-lp);
        var hp=noise-lp,decay=metal?.22:snare?.075:hat?.028:.040;
        env=(1-Math.exp(-t*2200))*Math.exp(-t/decay)*smoothEnv(t,d,.001,release);
        y=metal?sumOsc(osc)*.66+hp*.18:snare?hp*.85+Math.sin(TAU*180*t)*.17:hp*.77+(hat?sumOsc(osc)*.10:0);
        out[i]=y*env*.82;
      }
    } else if(inst==='whoosh') {
      var p1=0,p2=0;
      for(i=0;i<len;i++) {
        t=i/rate;var u=clamp(t/d,0,1);noise=rnd()*2-1;p1+=.14*(noise-p1);p2+=.045*(noise-p2);
        phase+=TAU*(f*(.70+u*.80))/rate;
        env=Math.sin(Math.PI*u)*smoothEnv(t,d,.015,release);
        out[i]=((p1-p2)*1.6+Math.sin(phase)*.18)*env*.70;
      }
    } else if(inst==='rolling') {
      for(i=0;i<len;i++) {
        t=i/rate;noise=rnd()*2-1;lp+=.12*(noise-lp);phase+=TAU*(112-28*clamp(t/d,0,1))/rate;
        var bumps=.55+.45*Math.pow(Math.cos(TAU*14*t),4);
        env=smoothEnv(t,d,.012,release)*Math.exp(-t*1.8);
        out[i]=(lp*.7+Math.sin(phase)*.40+Math.sin(phase*2.03)*.14)*bumps*env;
      }
    } else if(inst==='boing') {
      for(i=0;i<len;i++) {
        t=i/rate;phase+=TAU*f*(.48+.52*Math.exp(-t*5))*(1+.018*Math.sin(TAU*10*t))/rate;
        env=smoothEnv(t,d,.012,release)*Math.exp(-t*3.0);
        out[i]=(Math.sin(phase)+.23*Math.sin(2*phase))*env*.66;
      }
    }
    // A final short zero ramp prevents clicks even for percussion cut-offs.
    var end=Math.min(128,len);
    for(i=0;i<end;i++)out[len-1-i]*=i/end;
    return out;
  }
  function voiceKey(e,rate) {return rate+'|'+e.instrument+'|'+e.note+'|'+e.d.toFixed(4)+'|'+finite(e.bend,0);}
  function makeBank(rate,maxBytes) {
    var map=new Map(),bytes=0,limit=maxBytes||20*1024*1024;
    return {get:function(e){
      var key=voiceKey(e,rate),v=map.get(key);
      if(v){map.delete(key);map.set(key,v);return v;}
      v=voicePCM(e,rate);map.set(key,v);bytes+=v.byteLength;
      while(bytes>limit&&map.size>1){var first=map.keys().next().value;bytes-=map.get(first).byteLength;map.delete(first);}
      return v;
    },clear:function(){map.clear();bytes=0;},bytes:function(){return bytes;}};
  }

  var ALIASES={tok:'land',big:'bonus',done:'finish',capture:'catch',step:'walk',fall:'nak'};
  function effectScore(kind,options) {
    options=options||{};kind=ALIASES[kind]||kind;
    var e=[],pan=clamp(finite(options.pan,0),-.7,.7),team=clamp(Math.floor(finite(options.team,0)),0,3);
    var base=62+[0,2,5,7][team],count=clamp(Math.floor(finite(options.count,2)),2,6);
    function fx(t,d,inst,n,v,p,extra){add(e,t,d,inst,n,v,p===undefined?pan:p,extra).bus='effects';}
    if(kind==='throw') {
      [0,.055,.13,.23,.34,.48].forEach(function(t,i){fx(t,.075,'wood',73+(i*7)%12,.45+i*.035,pan+(i%2?.12:-.12));});
      fx(.02,.37,'shaker',72,.53,pan);
    } else if(kind==='land') {
      [0,.027,.064,.101].forEach(function(t,i){fx(t,.08,'wood',78-i*3,.65-i*.055,pan+(i-1.5)*.07);});
      fx(.10,.15,'jangguLow',50,.42,pan);
    } else if(kind==='walk') {
      fx(0,.045,'wood',65,.39,pan-.05);fx(.075,.05,'wood',70,.28,pan+.05);
    } else if(kind==='fly') {
      fx(0,.17,'whoosh',78,.60,pan);fx(.045,.055,'shaker',78,.30,pan+.12);
    } else if(kind==='roll') {
      fx(0,.22,'rolling',48,.75,pan);fx(.12,.045,'wood',61,.20,pan);
    } else if(kind==='impact') {
      fx(0,.18,'buk',38,.89,pan);fx(.008,.09,'wood',72,.80,pan);fx(.02,.13,'jangguHigh',66,.45,pan);
    } else if(kind==='catch') {
      fx(0,.14,'jangguHigh',67,.57,pan);
      [0,2,7,12].forEach(function(n,i){fx(.045+i*.095,.18,'gayageum',base+n,.72-i*.05,pan+(i-1.5)*.07);});
      fx(.33,.30,'bell',base+19,.33,pan+.18);
    } else if(kind==='return') {
      [12,7,2,0].forEach(function(n,i){fx(i*.064,.11,'gayageum',base+n,.37,pan);});
      fx(.10,.17,'whoosh',69,.35,pan);
    } else if(kind==='stack') {
      for(var i=0;i<count;i++)fx(i*.075,.20,'gayageum',base+[0,2,5,7,9,12][i],.56+i*.025,pan+(i/count-.5)*.25);
      fx(.10+count*.07,.25,'bell',base+12,.46,pan);
      fx(0,.14,'wood',64,.35,pan);
    } else if(kind==='finish') {
      [0,5,7,12,14].forEach(function(n,i){fx(i*.12,.26,'gayageum',base+n,.67,pan+(i-2)*.07);});
      fx(.38,.45,'bell',base+19,.43,pan+.18);fx(.02,.28,'metal',78,.38,pan-.2);
    } else if(kind==='winner') {
      var tune=[[0,0],[.16,2],[.32,7],[.58,12],[1.02,9],[1.22,7],[1.45,5],[1.70,7],[2.10,12]];
      tune.forEach(function(x,i){fx(x[0],i===tune.length-1?.95:.30,'gayageum',base+x[1],.78,pan-.12);fx(x[0]+.014,i===tune.length-1?.95:.26,'daegeum',base+x[1],.41,pan+.15);});
      [0,1.02,2.10].forEach(function(t,i){fx(t,.30,'buk',39,.72,0);fx(t,.65,'metal',80,.39,.30);[0,7,12].forEach(function(n){fx(t,.75,'organ',base-12+n,.53,-.13);});});
      [2.1,2.25,2.4].forEach(function(t,i){fx(t,.55,'bell',base+12+[0,7,12][i],.46,-.25+i*.25);});
    } else if(kind==='bonus') {
      [0,5,9,12].forEach(function(n,i){fx(i*.085,.22,'gayageum',base+n,.65,pan);});
      fx(.04,.20,'jangguHigh',68,.48,pan-.12);fx(.27,.30,'bell',base+12,.42,pan+.20);
    } else if(kind==='nak') {
      fx(0,.38,'boing',60,.70,pan);fx(.16,.11,'wood',59,.53,pan-.12);fx(.28,.12,'jangguLow',48,.33,pan+.10);
    } else {
      fx(0,.07,'wood',72,.48,pan);
    }
    e.sort(function(a,b){return a.t-b.t;});
    var duration=0;e.forEach(function(v){duration=Math.max(duration,v.t+v.d+tailFor(v.instrument));});
    return {kind:kind,duration:duration,events:e};
  }

  function create(options) {
    options=options||{};
    var music=options.music!==false,effects=options.effects!==false,muted=!!options.muted;
    var volume=clamp(finite(options.volume,.35),0,1),musicVolume=clamp(finite(options.musicVolume,.82),0,1);
    var effectsVolume=clamp(finite(options.effectsVolume,.95),0,1),track=options.track==='trot'?'trot':'folk';
    var onChange=typeof options.onChange==='function'?options.onChange:function(){};
    var ctx=null,graph=null,unlocked=false,disposed=false,playing=false,hidden=!!(root.document&&root.document.hidden),gamePaused=false;
    var timer=null,hideTimer=null,origin=0,nextIndex=0,nextCycle=0,position=0,score=compose(track),stateMark='',gameId='';
    var voices=new Set(),bank=makeBank(LIVE_RATE),buffers=new Map(),lastFX={};
    var bufferBytes=0,bufferLimit=20*1024*1024,duckUntil=0,duckFactor=1;
    function status() {
      var reason=disposed?'disposed':!unlocked?'gesture':hidden?'hidden':muted||volume===0?'muted':gamePaused?'game-over':!music?'music-off':ctx&&ctx.state!=='running'?'context-suspended':playing?'playing':'ready';
      return {version:VERSION,unlocked:unlocked,contextState:ctx?ctx.state:'not-created',music:music,effects:effects,muted:muted,
        volume:volume,musicVolume:musicVolume,effectsVolume:effectsVolume,track:track,trackName:score.name,
        playing:playing,paused:!!(unlocked&&music&&!playing),reason:reason,activeVoices:voices.size,disposed:disposed};
    }
    function emit(){try{onChange(status());}catch(ignore){}}
    function ramp(param,value,seconds) {
      if(!ctx)return;var now=ctx.currentTime;
      try{if(param.cancelAndHoldAtTime)param.cancelAndHoldAtTime(now);else{param.cancelScheduledValues(now);param.setValueAtTime(param.value,now);}param.linearRampToValueAtTime(value,now+(seconds||.04));}
      catch(ignore){param.value=value;}
    }
    function setup() {
      var mix=ctx.createGain(),m=ctx.createGain(),fx=ctx.createGain(),master=ctx.createGain(),limiter=ctx.createWaveShaper(),nodes=[];
      var curve=new Float32Array(4097);for(var i=0;i<curve.length;i++)curve[i]=soft(i/(curve.length-1)*2-1);
      limiter.curve=curve;limiter.oversample='none';
      m.gain.value=musicVolume;fx.gain.value=effectsVolume;master.gain.value=muted?0:volume;
      m.connect(mix);fx.connect(mix);mix.connect(master);master.connect(limiter);limiter.connect(ctx.destination);
      ECHOES.forEach(function(p){var delay=ctx.createDelay(.5),gain=ctx.createGain();delay.delayTime.value=p[0];gain.gain.value=p[1];mix.connect(delay);delay.connect(gain);gain.connect(master);nodes.push(delay,gain);});
      nodes.push(mix,m,fx,master,limiter);graph={music:m,effects:fx,master:master,nodes:nodes};
    }
    function applyMusicGain() {
      if(!graph||!ctx)return;
      var now=ctx.currentTime,ducked=now<duckUntil,param=graph.music.gain,target=musicVolume*(ducked?duckFactor:1);
      ramp(param,target,.022);
      if(ducked){param.setValueAtTime(target,duckUntil);param.linearRampToValueAtTime(musicVolume,duckUntil+.24);}
    }
    function duckMusic(kind) {
      var profile=DUCK[kind];if(!profile||!ctx||!graph)return;
      var now=ctx.currentTime;
      duckFactor=now<duckUntil?Math.min(duckFactor,profile[0]):profile[0];
      duckUntil=Math.max(duckUntil,now+profile[1]);applyMusicGain();
    }
    function audioBuffer(e) {
      var key=voiceKey(e,LIVE_RATE),v=buffers.get(key);
      if(v){buffers.delete(key);buffers.set(key,v);return v;}
      var pcm=bank.get(e);v=ctx.createBuffer(1,pcm.length,LIVE_RATE);v.copyToChannel(pcm,0);buffers.set(key,v);bufferBytes+=pcm.byteLength;
      while(bufferBytes>bufferLimit&&buffers.size>1){var first=buffers.keys().next().value,old=buffers.get(first);bufferBytes-=old.length*4;buffers.delete(first);}
      return v;
    }
    function releaseVoice(v) {
      voices.delete(v);
      try{v.source.disconnect();v.gain.disconnect();if(v.pan)v.pan.disconnect();}catch(ignore){}
    }
    function schedule(e,at,bus) {
      if(!ctx||!graph||ctx.state!=='running'||disposed)return;
      if(voices.size>=VOICE_LIMIT) {
        var victim=null;
        voices.forEach(function(v){if(!victim&&v.bus==='music'&&v.end<=ctx.currentTime+.15)victim=v;});
        if(victim){try{victim.source.stop(ctx.currentTime+.01);}catch(ignore){}releaseVoice(victim);}else return;
      }
      var source=ctx.createBufferSource(),gain=ctx.createGain(),pan=ctx.createStereoPanner?ctx.createStereoPanner():null;
      source.buffer=audioBuffer(e);gain.gain.value=MIX_GAIN*(GAINS[e.instrument]||.25)*e.v;
      source.connect(gain);if(pan){pan.pan.value=e.pan;gain.connect(pan);pan.connect(graph[bus]);}else gain.connect(graph[bus]);
      var v={source:source,gain:gain,pan:pan,bus:bus,end:at+source.buffer.duration};voices.add(v);
      source.onended=function(){releaseVoice(v);};
      try{source.start(Math.max(ctx.currentTime+.002,at));}catch(ignore){releaseVoice(v);}
    }
    function stopVoices(bus,seconds) {
      if(!ctx)return;var now=ctx.currentTime,d=seconds||.035;
      Array.from(voices).forEach(function(v){if(bus&&v.bus!==bus)return;ramp(v.gain.gain,0,d);try{v.source.stop(now+d+.005);}catch(ignore){releaseVoice(v);}});
    }
    function lowerBound(t) {
      var lo=0,hi=score.events.length;
      while(lo<hi){var mid=(lo+hi)>>1;if(score.events[mid].t<t)lo=mid+1;else hi=mid;}
      return lo;
    }
    function locate(t) {
      nextCycle=Math.max(0,Math.floor(t/score.duration));
      nextIndex=lowerBound(mod(t,score.duration));
      if(nextIndex>=score.events.length){nextIndex=0;nextCycle++;}
    }
    function tick() {
      if(!playing||!ctx||ctx.state!=='running')return;
      var now=ctx.currentTime,horizon=now+LOOKAHEAD,count=0;
      var next=origin+nextCycle*score.duration+score.events[nextIndex].t;
      // A delayed/background timer must never replay a queue of stale notes.
      if(next<now-.10)locate(Math.max(0,now-origin+.035));
      while(count++<256) {
        var e=score.events[nextIndex],at=origin+nextCycle*score.duration+e.t;
        if(at>horizon)break;
        if(at>=now-.015)schedule(e,Math.max(at,now+.004),'music');
        nextIndex++;if(nextIndex>=score.events.length){nextIndex=0;nextCycle++;}
      }
    }
    function halt(reset) {
      if(playing&&ctx)position=mod(Math.max(0,ctx.currentTime-origin),score.duration);
      if(reset)position=0;
      playing=false;if(timer){root.clearInterval(timer);timer=null;}stopVoices('music',.055);
    }
    function sync() {
      var should=!!(ctx&&ctx.state==='running'&&unlocked&&music&&!muted&&volume>0&&!hidden&&!gamePaused&&!disposed);
      if(!should){if(playing)halt(false);emit();return;}
      if(!playing){origin=ctx.currentTime+.09-position;locate(position);playing=true;tick();timer=root.setInterval(tick,TICK_MS);}
      emit();
    }
    function unlock() {
      if(disposed)return Promise.resolve(status());
      if(!ctx){
        var C=root.AudioContext||root.webkitAudioContext;
        if(!C){emit();return Promise.resolve(status());}
        try{ctx=new C({latencyHint:'interactive'});setup();
          ctx.onstatechange=function(){if(ctx&&ctx.state!=='running'&&playing)halt(false);if(ctx&&ctx.state==='running')sync();else emit();};
        }catch(ignore){ctx=null;emit();return Promise.resolve(status());}
      }
      return Promise.resolve(ctx.state==='running'?null:ctx.resume()).then(function(){
        if(disposed)return status();unlocked=ctx.state==='running';sync();return status();
      }).catch(function(){emit();return status();});
    }
    function visibility() {
      hidden=!!root.document.hidden;
      if(hideTimer){root.clearTimeout(hideTimer);hideTimer=null;}
      if(hidden){halt(false);stopVoices(null,.045);emit();hideTimer=root.setTimeout(function(){
        if(hidden&&ctx&&ctx.state==='running')ctx.suspend().then(function(){
          // A very fast tab return can race the asynchronous suspend request.
          if(!hidden&&!disposed&&unlocked&&ctx&&ctx.state==='suspended')ctx.resume().then(sync).catch(emit);
        }).catch(function(){});
      },70);}
      else if(ctx&&unlocked&&ctx.state==='suspended')ctx.resume().then(sync).catch(emit);
      else sync();
    }
    if(root.document&&root.document.addEventListener)root.document.addEventListener('visibilitychange',visibility);
    function setMusic(value){music=!!value;sync();return status();}
    function setEffects(value){effects=!!value;if(!effects)stopVoices('effects',.04);emit();return status();}
    function setMuted(value){muted=!!value;if(graph)ramp(graph.master.gain,muted?0:volume,.055);if(muted)stopVoices('effects',.045);sync();return status();}
    function setVolume(value) {
      if(typeof value==='number')volume=clamp(finite(value,volume),0,1);
      else if(value&&typeof value==='object') {
        if(value.master!==undefined)volume=clamp(finite(value.master,volume),0,1);
        if(value.music!==undefined)musicVolume=clamp(finite(value.music,musicVolume),0,1);
        if(value.effects!==undefined)effectsVolume=clamp(finite(value.effects,effectsVolume),0,1);
      }
      if(graph){ramp(graph.master.gain,muted?0:volume);applyMusicGain();ramp(graph.effects.gain,effectsVolume);}
      sync();return status();
    }
    function setTrack(id) {
      var next=id==='trot'?'trot':'folk';if(next===track)return status();
      halt(true);track=next;score=compose(track);sync();return status();
    }
    function setState(game) {
      if(!game||typeof game!=='object')return status();
      var nextId=String(game.game_id||''),last=game.last||{},mark=nextId+'|'+last.kind+'|'+last.at;
      var changedGame=!!(gameId&&nextId&&gameId!==nextId);
      if(changedGame){halt(true);stopVoices('effects',.04);}
      if(changedGame||(mark!==stateMark&&/^(undo|reset|restore)$/.test(last.kind||''))){
        stopVoices('effects',.04);duckUntil=0;duckFactor=1;applyMusicGain();
      }
      gameId=nextId||gameId;stateMark=mark;
      var nextPaused=game.phase==='over'||game.paused===true;
      if(nextPaused!==gamePaused||changedGame){gamePaused=nextPaused;sync();}
      return status();
    }
    function play(kind,opts) {
      kind=ALIASES[kind]||kind;
      if(!ctx||ctx.state!=='running'||!unlocked||!effects||muted||volume<=0||hidden||disposed)return false;
      var now=ctx.currentTime,minGap={walk:.055,fly:.09,roll:.09,throw:.30,land:.08,impact:.09,catch:.22,return:.16,stack:.20,finish:.35,winner:2.0,bonus:.25,nak:.25}[kind]||.055;
      if(lastFX[kind]!==undefined&&now-lastFX[kind]<minGap)return false;lastFX[kind]=now;
      var fx=effectScore(kind,opts),at=now+.012;
      duckMusic(kind);
      fx.events.forEach(function(e){schedule(e,at+e.t,'effects');});return true;
    }
    function dispose() {
      if(disposed)return;halt(true);stopVoices(null,.05);disposed=true;
      if(hideTimer)root.clearTimeout(hideTimer);
      if(root.document&&root.document.removeEventListener)root.document.removeEventListener('visibilitychange',visibility);
      bank.clear();buffers.clear();bufferBytes=0;emit();
      if(ctx){var old=ctx;old.onstatechange=null;root.setTimeout(function(){if(graph)graph.nodes.forEach(function(n){try{n.disconnect();}catch(ignore){}});if(old.state!=='closed')old.close().catch(function(){});},90);}
    }
    return {unlock:unlock,start:unlock,setMusic:setMusic,setEffects:setEffects,setVolume:setVolume,
      setMuted:setMuted,setTrack:setTrack,setState:setState,play:play,status:status,dispose:dispose};
  }

  // Same score + procedural voices as live playback, mixed without any browser.
  // Original dry mix, early reflections, equal-power pan, bus/master levels and
  // soft ceiling are shared. No normalisation hides clipping or level issues.
  function renderPCM(options) {
    options=options||{};
    var rate=Math.round(clamp(finite(options.sampleRate,44100),8000,48000)),score=compose(options.track);
    var duration=finite(options.seconds,score.duration*Math.max(1,finite(options.loops,1)));
    var tail=clamp(finite(options.tail,1),0,3);
    if(duration<=0||duration>300)throw new Error('Preview duration must be 0–300 seconds.');
    var len=Math.ceil((duration+tail)*rate),L=new Float32Array(len),R=new Float32Array(len),bank=makeBank(rate,32*1024*1024);
    var volume=clamp(finite(options.volume,.65),0,1),mv=clamp(finite(options.musicVolume,.82),0,1),fv=clamp(finite(options.effectsVolume,.95),0,1);
    function mix(e,at) {
      if(at>=duration)return;var pcm=bank.get(e),start=Math.max(0,Math.round(at*rate)),p=(e.pan+1)*Math.PI/4;
      var g=MIX_GAIN*(GAINS[e.instrument]||.25)*e.v*(e.bus==='effects'?fv:mv),gl=Math.cos(p)*g,gr=Math.sin(p)*g;
      var end=Math.min(pcm.length,len-start);
      for(var i=0;i<end;i++){L[start+i]+=pcm[i]*gl;R[start+i]+=pcm[i]*gr;}
    }
    if(options.music!==false) {
      for(var c=0;c*score.duration<duration;c++)score.events.forEach(function(e){mix(e,c*score.duration+e.t);});
    }
    // The same short musical duck used by live catch/stack/celebration cues.
    if(options.sfx&&options.sfx.length&&options.music!==false) {
      var ducks=new Float32Array(len);ducks.fill(1);
      options.sfx.forEach(function(spec){
        var p=DUCK[ALIASES[spec.kind]||spec.kind];if(!p)return;
        var at=finite(spec.at,0),start=Math.max(0,Math.floor(at*rate)),end=Math.min(len,Math.ceil((at+p[1]+.24)*rate));
        for(var i=start;i<end;i++){
          var dt=i/rate-at,g=dt<.022?1-(1-p[0])*dt/.022:dt<p[1]?p[0]:p[0]+(1-p[0])*(dt-p[1])/.24;
          ducks[i]=Math.min(ducks[i],g);
        }
      });
      for(var j=0;j<len;j++){L[j]*=ducks[j];R[j]*=ducks[j];}
    }
    (options.sfx||[]).forEach(function(spec){var fx=effectScore(spec.kind,spec);fx.events.forEach(function(e){mix(e,finite(spec.at,0)+e.t);});});
    var dryL=L.slice(),dryR=R.slice();
    ECHOES.forEach(function(p){var offset=Math.round(p[0]*rate),g=p[1];for(var i=offset;i<len;i++){L[i]+=dryL[i-offset]*g;R[i]+=dryR[i-offset]*g;}});
    var fade=options.fade!==false,fadeIn=Math.round(.025*rate),fadeOut=Math.round(Math.min(.65,duration/8)*rate);
    var preLimitPeak=0,ceilingSamples=0;
    for(var i=0;i<len;i++) {
      var env=fade?Math.min(1,i/fadeIn,(len-1-i)/fadeOut):1;
      var rawPeak=Math.max(Math.abs(L[i]*volume),Math.abs(R[i]*volume));
      preLimitPeak=Math.max(preLimitPeak,rawPeak);if(rawPeak>=1)ceilingSamples++;
      L[i]=soft(L[i]*volume)*Math.max(0,env);R[i]=soft(R[i]*volume)*Math.max(0,env);
    }
    bank.clear();
    return {sampleRate:rate,channels:[L,R],duration:len/rate,track:score.id,name:score.name,bars:32,
      preLimitPeak:preLimitPeak,ceilingSamples:ceilingSamples};
  }
  function wavBytes(pcm) {
    var L=pcm.channels[0],R=pcm.channels[1]||L,n=L.length,bytes=new Uint8Array(44+n*4),v=new DataView(bytes.buffer);
    function str(at,s){for(var j=0;j<s.length;j++)v.setUint8(at+j,s.charCodeAt(j));}
    str(0,'RIFF');v.setUint32(4,36+n*4,true);str(8,'WAVE');str(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,2,true);
    v.setUint32(24,pcm.sampleRate,true);v.setUint32(28,pcm.sampleRate*4,true);v.setUint16(32,4,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,n*4,true);
    for(var i=0;i<n;i++){v.setInt16(44+i*4,Math.round(clamp(L[i],-1,1)*(L[i]<0?32768:32767)),true);v.setInt16(46+i*4,Math.round(clamp(R[i],-1,1)*(R[i]<0?32768:32767)),true);}
    return bytes;
  }
  var EFFECT_DEMO=[
    {at:.25,kind:'throw'},{at:1.0,kind:'land'},{at:1.8,kind:'walk'},{at:2.15,kind:'walk'},
    {at:2.7,kind:'fly'},{at:3.25,kind:'roll'},{at:4.0,kind:'impact'},
    {at:4.15,kind:'catch',team:2},{at:4.9,kind:'return'},{at:5.6,kind:'stack',count:4},
    {at:6.8,kind:'bonus'},{at:7.8,kind:'nak'},{at:8.9,kind:'finish'},
    {at:10.3,kind:'winner'}
  ];
  var api={version:VERSION,tracks:TRACKS,create:create,compose:compose,effectScore:effectScore,
    renderPCM:renderPCM,wavBytes:wavBytes,renderWav:function(o){return wavBytes(renderPCM(o));},effectDemo:EFFECT_DEMO};
  root.YutAudio=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
