# app.py
# 夢見る水槽（フル作り直し / シンプル安定版）
# ------------------------------------------------------------
# 依存: streamlit, pillow, numpy
# 実行: streamlit run app.py
#
# ポイント:
#  - JSなし（純CSSアニメ）で“ゆらゆら泳ぐ”を実現 → Streamlitでも安定
#  - 魚画像はPillowで自動生成 or ユーザーアップロード画像をそのまま使用
#  - パフォーマンス重：CSSアニメなので60fpsに近く滑らか
#  - 「もっと物理っぽい挙動」は NiceGUI / Three.js へ拡張推奨（下に解説）

import base64
import io
import random
from dataclasses import dataclass
from typing import List

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import streamlit as st
from string import Template
from streamlit.components.v1 import html as st_html

# -----------------------------
# 配色（背景グラデ + 魚の色）
# -----------------------------
PALETTES = {
    "Calm Ocean": ["#0f172a", "#1e293b", "#334155", "#60a5fa", "#93c5fd"],
    "Warm Sunset": ["#2c1810", "#4a1d1f", "#7a1f2a", "#f59e0b", "#fde68a"],
    "Forest Lake": ["#0b1d1a", "#143b37", "#1e4e48", "#34d399", "#a7f3d0"],
}

@dataclass
class FishSpec:
    seed: int
    scale: float
    depth: float  # 0..1 (遠いほど薄く / 遅く)
    dir_right: bool
    top: float     # 0..100 (% from top)
    swim_sec: float
    bob_sec: float

# -----------------------------
# 画像生成
# -----------------------------

def to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def generate_fish(seed: int, palette: list, size: int = 220) -> Image.Image:
    random.seed(seed); np.random.seed(seed % (2**32-1))
    body = Image.new("RGBA", (size, size), (0,0,0,0))
    d = ImageDraw.Draw(body, "RGBA")

    body_c = palette[3]
    accent = palette[4]

    cx, cy = size//2, size//2
    bw = int(size * random.uniform(0.58, 0.72))
    bh = int(size * random.uniform(0.30, 0.40))
    d.ellipse([cx-bw//2, cy-bh//2, cx+bw//2, cy+bh//2], fill=(255,255,255,0))

    # グラデ体
    base = Image.new("RGBA", body.size, (0,0,0,0))
    db = ImageDraw.Draw(base, "RGBA")
    for i in range(28):
        a = int(220 * (1 - i/28))
        col = hex_to_rgba(body_c, a)
        db.ellipse([cx-bw//2+i, cy-bh//2+i//2, cx+bw//2-i, cy+bh//2-i//2], fill=col)

    # しま
    for i in range(random.randint(2,4)):
        y = cy + int((i-(3/2))*bh/4)
        h = random.randint(6,10)
        db.rounded_rectangle([cx-bw//2+10, y-h//2, cx+bw//2-10, y+h//2], radius=h//2, fill=hex_to_rgba(accent, 70))

    # 尾びれ
    db.polygon([(cx-bw//2-4, cy), (cx-bw//2-40, cy-bh//2), (cx-bw//2-40, cy+bh//2)], fill=hex_to_rgba(body_c, 220))

    # 目
    db.ellipse([cx+bw//4-8, cy-bh//6-8, cx+bw//4+8, cy-bh//6+8], fill=(255,255,255,230))
    db.ellipse([cx+bw//4-4, cy-bh//6-4, cx+bw//4+4, cy-bh//6+4], fill=(30,40,60,230))

    out = base.filter(ImageFilter.GaussianBlur(0.6))
    return out


def hex_to_rgba(hex_str: str, alpha: int):
    h = hex_str.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r, g, b, max(0, min(255, alpha)))

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="夢見る水槽", page_icon="🐟", layout="wide")
st.title("🐟 夢見る水槽 — Dreaming Aquarium")
st.caption("Streamlitでも安定する純CSSアニメ版。落ち着いて眺める専用。")

c1, c2, c3, c4 = st.columns([1.2,1,1,1])
with c1:
    pal_name = st.selectbox("配色", list(PALETTES.keys()), index=0)
with c2:
    n_fish = st.slider("魚の数", 3, 40, 14)
with c3:
    speed_mul = st.slider("速さ倍率", 0.5, 3.0, 1.0)
with c4:
    height = st.slider("水槽の高さ(px)", 360, 900, 540)

use_upload = st.toggle("自分の画像を魚にする", value=False)
uploads = st.file_uploader("PNG/JPGを複数", type=["png","jpg","jpeg"], accept_multiple_files=True, disabled=not use_upload)

palette = PALETTES[pal_name]

# -----------------------------
# 魚データ + 画像URI
# -----------------------------
uris: List[str] = []
if use_upload and uploads:
    for f in uploads:
        try:
            im = Image.open(f).convert("RGBA")
            long = max(im.size)
            scale = 220/long
            im = im.resize((int(im.width*scale), int(im.height*scale)))
            uris.append(to_data_uri(im))
        except Exception:
            pass

if not uris:
    # 自動生成
    for i in range(max(8, n_fish//2)):
        im = generate_fish(random.randint(0, 10_000_000), palette)
        uris.append(to_data_uri(im))

specs: List[FishSpec] = []
for i in range(n_fish):
    specs.append(
        FishSpec(
            seed=random.randint(0, 10_000_000),
            scale=random.uniform(0.6, 1.2),
            depth=random.random(),
            dir_right=bool(random.getrandbits(1)),
            top=random.uniform(5, 90),
            swim_sec=random.uniform(18, 36) / speed_mul,
            bob_sec=random.uniform(4, 8),
        )
    )

# -----------------------------
# HTML/CSS（JSなし）
# -----------------------------
FISH_ITEMS = []
for i, s in enumerate(specs):
    uri = uris[i % len(uris)]
    left = "-20%" if s.dir_right else "120%"
    anim = "swimR" if s.dir_right else "swimL"
    opacity = 0.65 + 0.35*(1 - s.depth)
    scale = s.scale * (0.7 + 0.3*(1 - s.depth))
    delay = -random.uniform(0, s.swim_sec)
    bobdelay = -random.uniform(0, s.bob_sec)

    style = f"top:{s.top}%; left:{left}; opacity:{opacity:.2f}; transform:scale({scale:.2f}) {'scaleX(-1)' if not s.dir_right else ''}; animation: {anim} {s.swim_sec:.1f}s linear infinite, bob {s.bob_sec:.1f}s ease-in-out infinite; animation-delay: {delay:.2f}s, {bobdelay:.2f}s;"
    FISH_ITEMS.append(f'<img class="fish" src="{uri}" style="{style}">')

fish_html = "\n".join(FISH_ITEMS)

T = Template(r"""
<style>
  .aqua { position:relative; width:100%; height:${HEIGHT}px; overflow:hidden; border-radius:16px; box-shadow:0 10px 40px rgba(0,0,0,.15); }
  .aqua::before { content:""; position:absolute; inset:0; background:linear-gradient(180deg, ${BG0}, ${BG1}); }
  .fish { position:absolute; will-change: transform, left, top; }

  @keyframes swimR { from { left:-20%; } to { left:120%; } }
  @keyframes swimL { from { left:120%; } to { left:-20%; } }
  @keyframes bob { 0% { transform: translateY(0); } 50% { transform: translateY(-10px); } 100% { transform: translateY(0); } }

  /* 柔らかい光の筋 */
  .aqua .beam { position:absolute; top:-20%; width:20%; height:140%; background:radial-gradient(ellipse at top, rgba(255,255,255,.15), rgba(255,255,255,0) 60%); filter:blur(8px); opacity:.35; transform:rotate(-8deg); }
  .beam.b1 { left:5%; } .beam.b2 { left:30%; } .beam.b3 { left:55%; } .beam.b4 { left:80%; }

  /* バブル */
  .bubble { position:absolute; bottom:-40px; width:6px; height:6px; background:rgba(255,255,255,.25); border-radius:50%; animation: rise linear infinite; }
  @keyframes rise { from { transform: translateY(0); opacity:.2;} to { transform: translateY(-120%); opacity:.0;} }
</style>
<div class="aqua">
  <div class="beam b1"></div><div class="beam b2"></div><div class="beam b3"></div><div class="beam b4"></div>
  $FISH_ITEMS
  $BUBBLES
</div>
""")

# バブル要素生成
bubble_elems = []
for _ in range(24):
    left = f"{random.uniform(0, 100):.1f}%"
    dur = f"{random.uniform(12, 28)/speed_mul:.1f}s"
    delay = f"{-random.uniform(0, 10):.1f}s"
    size = random.uniform(4, 10)
    bubble_elems.append(f'<span class="bubble" style="left:{left}; width:{size:.0f}px; height:{size:.0f}px; animation-duration:{dur}; animation-delay:{delay};"></span>')

comp_html = T.substitute(
    HEIGHT=height,
    BG0=palette[1],
    BG1=palette[2],
    FISH_ITEMS=fish_html,
    BUBBLES="\n".join(bubble_elems),
)

st_html(comp_html, height=height, scrolling=False)

st.markdown(
    "<small>ヒント: 魚の数や速さを触って、自分が落ち着ける流れを探してね。画像アップで好きな魚を泳がせられます。もっと物理挙動を入れたくなったら NiceGUI / Three.js へ拡張。</small>",
    unsafe_allow_html=True,
)
