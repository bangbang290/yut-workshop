"""참고 이미지로 새로 제작한 3D 캐릭터.

assets/*.png: 생성 원본 · *.webp: 화면 전송용 경량 버전(투명도 보존).
각 캐릭터를 SVG 뷰포트에 넣어 기존 말판·아바타와 같은 좌표를 사용합니다.
외부 이미지 주소, 폰트, API 연결이 필요하지 않습니다.
"""
from __future__ import annotations
import base64
import json
from pathlib import Path
from functools import lru_cache
import font_bundle

_ASSETS = Path(__file__).resolve().parent / 'assets'
_NAMES = ['heungbu','nolbu','swallow','gourd']
_CLASSES = ['person','person','bird','gourd']
_SIZES = [(64,96),(64,96),(96,72),(64,64)]
MOTION = ['walk','walk','fly','roll']
AVATAR_VB = ['0 0 64 64','0 0 64 64','0 0 96 72','0 0 64 64']
DEFS = '<svg class="yk-defs" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true"><defs></defs></svg>'

@lru_cache(maxsize=4)
def _sprite(i: int) -> str:
    name = _NAMES[i]
    p = _ASSETS/(name+'.webp')
    encoded = base64.b64encode(p.read_bytes()).decode('ascii')
    meta = json.loads((_ASSETS/'layout.json').read_text())[_NAMES[i]]
    x0,y0,x1,y1=meta['bounds']
    w,h = _SIZES[i]
    # Compute placement from the alpha bounds without cutting the original image.
    scale=min(w/(x1-x0),h/(y1-y0))
    iw,ih=meta['width']*scale,meta['height']*scale
    x=(w-(x1-x0)*scale)/2-x0*scale
    y=h-y1*scale
    return (f'<svg class="spr {_CLASSES[i]}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">'
            f'<image href="data:image/webp;base64,{encoded}" x="{x:.3f}" y="{y:.3f}" width="{iw:.3f}" height="{ih:.3f}" preserveAspectRatio="none"/></svg>')

SPRITES = [_sprite(i) for i in range(4)]
HEUNGBU,NOLBU,JEBI,BAK=SPRITES
SPRITE_CSS = font_bundle.css() + '\n.spr{display:block;overflow:visible}.spr image{pointer-events:none}'

def avatar(i: int) -> str:
    i%=4
    w,h=_SIZES[i]
    return SPRITES[i].replace(f'viewBox="0 0 {w} {h}"',f'viewBox="{AVATAR_VB[i]}" style="overflow:hidden"',1)

@lru_cache(maxsize=1)
def js_bundle() -> str:
    return json.dumps({'defs':DEFS,'spr':SPRITES,'av':[avatar(i) for i in range(4)],'motion':MOTION,'avb':AVATAR_VB,'css':SPRITE_CSS},ensure_ascii=False)
