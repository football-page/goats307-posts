"""Make a كوكب الرياضة (@goats_307) news card.

Usage: python3 tools/make_card.py spec.json out.jpg

spec.json keys:
  tag       short Arabic label, e.g. "دوري الأمم الأوروبية"
  theme     one of: gold, blue, green, red, purple
  headline  Arabic headline (one or two lines)
  facts     list of up to 3 short Arabic bullet points
  source    e.g. "ESPN، ITV"
  date      e.g. "16.11.2026"
  home, away, home_score, away_score   (optional; omit all four for a non-match news card)
  status    (optional) label under the score: "النهاية" (default), "الشوط الأول", "مباشر - الدقيقة 67"
  format    (optional) "story" for a 1080x1920 Instagram Story image; default is a 1080x1350 feed post

Needs: pip install pillow  (Pillow must be built with libraqm for Arabic shaping).
Output: 1080x1350 JPEG (4:5), ready for Instagram.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont, features

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = {w: os.path.join(HERE, "fonts", f"cairo-{w}.ttf") for w in (400, 700, 900)}
W, H = 1080, 1350
THEMES = {
    "gold": ((255, 196, 0), (18, 32, 74), (6, 10, 30)),
    "blue": ((80, 200, 255), (10, 40, 90), (4, 12, 34)),
    "green": ((40, 220, 130), (8, 50, 40), (3, 16, 14)),
    "red": ((255, 80, 80), (70, 14, 20), (22, 4, 8)),
    "purple": ((190, 130, 255), (40, 20, 80), (12, 6, 28)),
}
DARK = (10, 14, 28)


def is_ar(t):
    return any("؀" <= c <= "ۿ" for c in str(t))


def font(weight, size):
    return ImageFont.truetype(FONT[weight], size, layout_engine=ImageFont.Layout.RAQM)


def text(d, xy, s, f, fill, anchor):
    kw = {"direction": "rtl"} if is_ar(s) else {}
    d.text(xy, s, font=f, fill=fill, anchor=anchor, **kw)


def width(d, s, f):
    kw = {"direction": "rtl"} if is_ar(s) else {}
    return d.textlength(s, font=f, **kw)


def wrap(d, s, f, maxw):
    lines, cur = [], ""
    for w in s.split():
        test = (cur + " " + w).strip()
        if width(d, test, f) <= maxw or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def make(spec, out):
    if not features.check("raqm"):
        sys.exit("Pillow lacks libraqm: Arabic text would render broken.")
    accent, top, bottom = THEMES[spec.get("theme", "gold")]
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))

    d.rectangle([0, 0, W, 120], fill=DARK)
    d.rectangle([0, 116, W, 124], fill=accent)
    text(d, (W - 60, 60), "كوكب الرياضة", font(900, 46), "white", "rm")
    text(d, (60, 60), "@goats_307", font(700, 34), (200, 205, 220), "lm")

    tf = font(700, 36)
    tw = width(d, spec["tag"], tf)
    d.rounded_rectangle([(W - tw) / 2 - 36, 175, (W + tw) / 2 + 36, 245], radius=35, fill=accent)
    text(d, (W / 2, 210), spec["tag"], tf, DARK, "mm")

    y = 290
    if "home" in spec:
        d.rounded_rectangle([60, 290, W - 60, 620], radius=36, outline=(255, 255, 255), width=3)
        nf, sf = font(900, 54), font(900, 190)
        # RTL layout: home team on the right
        text(d, (W - 230, 545), spec["home"], nf, "white", "mm")
        text(d, (230, 545), spec["away"], nf, "white", "mm")
        text(d, (W - 230, 420), str(spec["home_score"]), sf, "white", "mm")
        text(d, (230, 420), str(spec["away_score"]), sf, "white", "mm")
        text(d, (W / 2, 420), "-", font(900, 140), accent, "mm")
        text(d, (W / 2, 545), spec.get("status", "النهاية"), font(700, 34), accent, "mm")
        y = 680
    else:
        # news card without a score: centre the text block vertically
        hf0, ff0 = font(900, 72), font(700, 40)
        block = len(wrap(d, spec["headline"], hf0, W - 140)) * 104 + 30
        for fact in spec.get("facts", [])[:3]:
            block += len(wrap(d, fact, ff0, W - 190)) * 60 + 12
        y = max(300, 270 + (H - 110 - 270 - block) // 2)

    hf = font(900, 72 if "home" not in spec else 64)
    for line in wrap(d, spec["headline"], hf, W - 140):
        text(d, (W - 70, y), line, hf, "white", "ra")
        y += 104 if "home" not in spec else 92
    y += 30
    ff = font(700, 40)
    for fact in spec.get("facts", [])[:3]:
        for i, line in enumerate(wrap(d, fact, ff, W - 190)):
            if i == 0:
                d.ellipse([W - 92, y + 22, W - 72, y + 42], fill=accent)
            text(d, (W - 110, y), line, ff, (225, 230, 240), "ra")
            y += 60
        y += 12
    if y > H - 110:
        sys.exit(f"Text too long: content ends at y={y}, shorten the headline or facts.")

    d.rectangle([0, H - 90, W, H], fill=DARK)
    text(d, (W - 60, H - 45), "المصدر: " + spec["source"], font(400, 32), (170, 175, 190), "rm")
    text(d, (60, H - 45), spec["date"], font(700, 32), (170, 175, 190), "lm")
    if spec.get("format") == "story":
        # 9:16 canvas for Instagram Stories, card centred on it
        story = Image.new("RGB", (W, 1920), bottom)
        sd = ImageDraw.Draw(story)
        for y in range(1920):
            k = y / 1920
            sd.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
        story.paste(img, (0, (1920 - H) // 2))
        img = story
    img.save(out, "JPEG", quality=92)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as fh:
        make(json.load(fh), sys.argv[2])
    print("saved", sys.argv[2])
