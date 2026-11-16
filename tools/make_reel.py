"""Make an animated Instagram Reel (1080x1920 MP4) for كوكب الرياضة (@goats_307).

Usage: python3 tools/make_reel.py reel.json out.mp4

reel.json:
  title          Arabic intro title, e.g. "أبرز نتائج الليلة"
  subtitle       (optional) Arabic line under the title, e.g. "دوري أبطال أوروبا"
  theme          intro/outro theme: gold, blue, green, red, purple
  slide_seconds  (optional) seconds per slide, default 3.6
  slides         list of card specs, same keys as tools/make_card.py
                 (tag, theme, headline, facts, source, date, and optional home/away/scores/status)

A single-slide reel works too (e.g. one big full-time result).
Needs ffmpeg. Video has a silent audio track; trending sounds can be added later in the Instagram app.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_card as mc  # noqa: E402

W, H, FPS = 1080, 1920, 30
OY = 285  # card content starts here; keeps text clear of the Reels UI overlays
INTRO, OUTRO = 1.8, 2.2
_bg_cache = {}


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def background(theme):
    if theme not in _bg_cache:
        _, top, bottom = mc.THEMES[theme]
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        for y in range(H):
            k = y / H
            d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
        _bg_cache[theme] = img.convert("RGBA")
    return _bg_cache[theme].copy()


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def put(base, lay, alpha=1.0, dy=0.0):
    alpha = max(0.0, min(1.0, alpha))
    if alpha <= 0:
        return
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    base.alpha_composite(lay, (0, int(dy)))


def header(base, accent):
    d = ImageDraw.Draw(base)
    d.rectangle([0, OY, W, OY + 120], fill=mc.DARK)
    d.rectangle([0, OY + 116, W, OY + 124], fill=accent)
    mc.text(d, (W - 60, OY + 60), "كوكب الرياضة", mc.font(900, 46), "white", "rm")
    mc.text(d, (60, OY + 60), "@goats_307", mc.font(700, 34), (200, 205, 220), "lm")


def slide_frame(spec, t):
    theme = spec.get("theme", "gold")
    accent = mc.THEMES[theme][0]
    base = background(theme)
    header(base, accent)

    # tag pill
    lay = layer()
    d = ImageDraw.Draw(lay)
    tf = mc.font(700, 36)
    tw = mc.width(d, spec["tag"], tf)
    d.rounded_rectangle([(W - tw) / 2 - 36, OY + 175, (W + tw) / 2 + 36, OY + 245], radius=35, fill=accent)
    mc.text(d, (W / 2, OY + 210), spec["tag"], tf, mc.DARK, "mm")
    put(base, lay, ease(t / 0.3))

    match = "home" in spec
    y = OY + 680 if match else OY + 330
    if match:
        p = ease((t - 0.15) / 0.45)
        lay = layer()
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle([60, OY + 290, W - 60, OY + 620], radius=36, outline=(255, 255, 255), width=3)
        nf = mc.font(900, 54)
        mc.text(d, (W - 230, OY + 545), spec["home"], nf, "white", "mm")
        mc.text(d, (230, OY + 545), spec["away"], nf, "white", "mm")
        mc.text(d, (W / 2, OY + 545), spec.get("status", "النهاية"), mc.font(700, 34), accent, "mm")
        mc.text(d, (W / 2, OY + 420), "-", mc.font(900, 140), accent, "mm")
        # scores count up
        c = ease((t - 0.5) / 0.7)
        sf = mc.font(900, 190)
        hs, as_ = int(spec["home_score"]), int(spec["away_score"])
        mc.text(d, (W - 230, OY + 420), str(round(hs * c)), sf, "white", "mm")
        mc.text(d, (230, OY + 420), str(round(as_ * c)), sf, "white", "mm")
        put(base, lay, p, (1 - p) * 120)

    hf = mc.font(900, 64 if match else 72)
    step = 92 if match else 104
    d0 = ImageDraw.Draw(base)
    lines = mc.wrap(d0, spec["headline"], hf, W - 140)
    start = 1.1 if match else 0.4
    for i, line in enumerate(lines):
        p = ease((t - start - i * 0.15) / 0.35)
        lay = layer()
        mc.text(ImageDraw.Draw(lay), (W - 70, y), line, hf, "white", "ra")
        put(base, lay, p, (1 - p) * 40)
        y += step
    y += 30
    ff = mc.font(700, 40)
    k = 0
    for fact in spec.get("facts", [])[:3]:
        p = ease((t - start - 0.5 - k * 0.3) / 0.35)
        lay = layer()
        d = ImageDraw.Draw(lay)
        for i, line in enumerate(mc.wrap(d, fact, ff, W - 190)):
            if i == 0:
                d.ellipse([W - 92, y + 22, W - 72, y + 42], fill=accent)
            mc.text(d, (W - 110, y), line, ff, (225, 230, 240), "ra")
            y += 60
        y += 12
        put(base, lay, p, (1 - p) * 40)
        k += 1

    d = ImageDraw.Draw(base)
    d.rectangle([0, OY + 1260, W, OY + 1350], fill=mc.DARK)
    mc.text(d, (W - 60, OY + 1305), "المصدر: " + spec["source"], mc.font(400, 32), (170, 175, 190), "rm")
    mc.text(d, (60, OY + 1305), spec["date"], mc.font(700, 32), (170, 175, 190), "lm")
    return base


def intro_frame(reel, t):
    theme = reel.get("theme", "gold")
    accent = mc.THEMES[theme][0]
    base = background(theme)
    header(base, accent)
    p = ease(t / 0.6)
    lay = layer()
    d = ImageDraw.Draw(lay)
    tf = mc.font(900, 92)
    y = 760
    for line in mc.wrap(d, reel["title"], tf, W - 160):
        mc.text(d, (W / 2, y), line, tf, "white", "mm")
        y += 120
    put(base, lay, p, (1 - p) * 80)
    d = ImageDraw.Draw(base)
    bar = int((W - 320) * ease((t - 0.3) / 0.6))
    d.rectangle([W / 2 - bar / 2, y - 20, W / 2 + bar / 2, y - 10], fill=accent)
    if reel.get("subtitle"):
        lay = layer()
        mc.text(ImageDraw.Draw(lay), (W / 2, y + 60), reel["subtitle"], mc.font(700, 48), accent, "mm")
        put(base, lay, ease((t - 0.6) / 0.5))
    return base


def outro_frame(reel, t):
    theme = reel.get("theme", "gold")
    accent = mc.THEMES[theme][0]
    base = background(theme)
    lay = layer()
    d = ImageDraw.Draw(lay)
    mc.text(d, (W / 2, 820), "كوكب الرياضة", mc.font(900, 110), "white", "mm")
    mc.text(d, (W / 2, 960), "تابعونا لكل جديد في عالم كرة القدم", mc.font(700, 46), (225, 230, 240), "mm")
    d.rounded_rectangle([W / 2 - 230, 1050, W / 2 + 230, 1140], radius=45, fill=accent)
    mc.text(d, (W / 2, 1095), "@goats_307", mc.font(900, 48), mc.DARK, "mm")
    p = ease(t / 0.5)
    put(base, lay, p, (1 - p) * 60)
    return base


def render(reel, out):
    sec = float(reel.get("slide_seconds", 3.6))
    parts = [(INTRO, lambda t: intro_frame(reel, t))]
    for s in reel["slides"]:
        parts.append((sec, lambda t, s=s: slide_frame(s, t)))
    parts.append((OUTRO, lambda t: outro_frame(reel, t)))
    total = sum(p[0] for p in parts)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", "-shortest", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for dur, fn in parts:
        n = int(round(dur * FPS))
        for i in range(n):
            proc.stdin.write(fn(i / FPS).convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"saved {out} ({total:.1f}s)")


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as fh:
        render(json.load(fh), sys.argv[2])
