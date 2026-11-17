"""Make a "who scored this goal?" quiz Reel (1080x1920 MP4) for كوكب الرياضة (@goats_307).

Usage: python3 tools/make_goal_quiz.py quiz.json out.mp4

The goal is an animated top-down recreation (no footage, no crests, no names on shirts).
Pitch coordinates are metres: x 0..68 across (0 = left touchline), y = distance from
our own goal line, attacking UPWARDS towards the goal line at y = 105. Visible: y 40..105.

quiz.json:
  question      Arabic hook, e.g. "مين سجّل هذا الهدف؟"
  clues         list of short Arabic clue lines shown at the end (year, competition ...)
  cta           list of Arabic call-to-action lines (comment / answer tomorrow)
  label         small honesty label, default "تجسيد للهدف"
  theme         gold, blue, green, red, purple (accent colour)
  anim_seconds  length of the animation, default 7.5
  goal_time     animation time (s) when the ball crosses the line
  players       list of {"id", "team": "a"|"b"|"gk", "scorer": bool,
                         "keys": [[t, x, y], ...]}   (t = seconds into the animation)
  ball          list of keyframes: [t, x, y]  or  [t, "<player id>"] (ball at that
                player's feet; between two keys on the same player the ball is dribbled)
"""
import json
import os
import subprocess
import sys

from PIL import ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_card as mc  # noqa: E402
from make_reel import ease, header, layer, put, background, OY  # noqa: E402

W, H, FPS = 1080, 1920, 30
PX0, GOAL_Y, S = 90, 600, 900 / 68.0  # pitch left edge, goal-line screen y, px per metre
Y_MIN = 40
INTRO, HOLD, END = 1.2, 0.8, 5.0
TEAM = {"a": ((255, 196, 0), (60, 40, 0)), "b": ((240, 244, 250), (40, 60, 110)),
        "gk": ((40, 220, 130), (5, 60, 30))}


def P(x, y):
    return (PX0 + x * S, GOAL_Y + (105 - y) * S)


def catmull(keys, t):
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    if t >= keys[-1][0]:
        return keys[-1][1], keys[-1][2]
    for i in range(len(keys) - 1):
        if keys[i][0] <= t <= keys[i + 1][0]:
            break
    p0 = keys[max(i - 1, 0)]
    p1, p2 = keys[i], keys[i + 1]
    p3 = keys[min(i + 2, len(keys) - 1)]
    u = (t - p1[0]) / (p2[0] - p1[0])
    out = []
    for k in (1, 2):
        a, b, c, d = p0[k], p1[k], p2[k], p3[k]
        out.append(0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u
                          + (-a + 3 * b - 3 * c + d) * u ** 3))
    return out[0], out[1]


def pitch_base(theme):
    base = background(theme)
    d = ImageDraw.Draw(base)
    top, bot = P(0, 105)[1], P(0, Y_MIN)[1]
    for i in range(14):
        y0 = 105 - i * 5
        a, b = P(0, y0)[1], P(0, max(y0 - 5, Y_MIN))[1]
        if a >= bot:
            break
        d.rectangle([PX0, a, PX0 + 68 * S, min(b, bot)], fill=(30, 110, 55) if i % 2 else (36, 124, 62))
    line = (235, 245, 235)
    w = 4
    d.rectangle([PX0, top, PX0 + 68 * S, bot], outline=line, width=w)
    d.line([P(0, 52.5), P(68, 52.5)], fill=line, width=w)
    cx, cy = P(34, 52.5)
    r = 9.15 * S
    d.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=line, width=w)
    d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=line)
    x0, y0 = P(13.84, 105)
    x1, y1 = P(54.16, 88.5)
    d.rectangle([x0, y0, x1, y1], outline=line, width=w)
    x0, y0 = P(24.84, 105)
    x1, y1 = P(43.16, 99.5)
    d.rectangle([x0, y0, x1, y1], outline=line, width=w)
    sx, sy = P(34, 94)
    d.ellipse([sx - 5, sy - 5, sx + 5, sy + 5], fill=line)
    d.arc([sx - r, sy - r, sx + r, sy + r], 37, 143, fill=line, width=w)
    # goal + net
    gx0, gy0 = P(30.34, 107.2)
    gx1, gy1 = P(37.66, 105)
    for k in range(int(gx0), int(gx1), 12):
        d.line([(k, gy0), (k, gy1)], fill=(200, 210, 200), width=1)
    for k in range(int(gy0), int(gy1), 10):
        d.line([(gx0, k), (gx1, k)], fill=(200, 210, 200), width=1)
    d.rectangle([gx0, gy0, gx1, gy1], outline="white", width=6)
    return base


def ball_at(spec, pos, t):
    keys = spec["ball"]

    def resolve(k, tt):
        if isinstance(k[1], str):
            x, y = pos(k[1], tt)
            return x, y + 1.2  # just in front of the player's feet
        return k[1], k[2]

    if t <= keys[0][0]:
        return resolve(keys[0], t)
    if t >= keys[-1][0]:
        return resolve(keys[-1], keys[-1][0])
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a[0] <= t <= b[0]:
            if isinstance(a[1], str) and a[1] == b[1]:
                return resolve(a, t)
            u = (t - a[0]) / (b[0] - a[0])
            ax, ay = resolve(a, a[0])
            bx, by = resolve(b, b[0])
            return ax + (bx - ax) * u, ay + (by - ay) * u


def render(spec, out):
    theme = spec.get("theme", "gold")
    accent = mc.THEMES[theme][0]
    A = float(spec.get("anim_seconds", 7.5))
    gt = float(spec["goal_time"])
    total = INTRO + A + HOLD + END
    players = {p["id"]: p for p in spec["players"]}

    def pos(pid, t):
        return catmull(players[pid]["keys"], t)

    base0 = pitch_base(theme)
    header(base0, accent)
    scorer = next(p["id"] for p in spec["players"] if p.get("scorer"))
    trail_pts = []

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", "-shortest", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(round(total * FPS))
    qf, lf, nf = mc.font(900, 66), mc.font(700, 30), mc.font(900, 34)
    for i in range(n):
        T = i / FPS
        t = min(max(T - INTRO, 0), A)
        img = base0.copy()
        d = ImageDraw.Draw(img)

        # question
        lay = layer()
        mc.text(ImageDraw.Draw(lay), (W / 2, OY + 195), spec["question"], qf, "white", "mm")
        put(img, lay, ease(T / 0.5), 0)
        d = ImageDraw.Draw(img)
        lab = spec.get("label", "تجسيد للهدف")
        lw = mc.width(d, lab, lf)
        d.rounded_rectangle([PX0 + 10, P(0, Y_MIN)[1] - 58, PX0 + lw + 50, P(0, Y_MIN)[1] - 12],
                            radius=20, fill=(0, 0, 0))
        mc.text(d, (PX0 + 30 + lw / 2, P(0, Y_MIN)[1] - 35), lab, lf, (230, 230, 230), "mm")

        # clue strip under the pitch
        strip = "  •  ".join(spec["clues"])
        mc.text(d, (W / 2, P(0, Y_MIN)[1] + 55), strip, mc.font(700, 38), (225, 230, 240), "mm")

        # scorer trail
        if T >= INTRO:
            sx, sy = pos(scorer, t)
            if not trail_pts or (trail_pts[-1][0] - sx) ** 2 + (trail_pts[-1][1] - sy) ** 2 > 0.8:
                if t < A:
                    trail_pts.append((sx, sy))
        pts = [P(*p) for p in trail_pts]
        for k in range(0, len(pts) - 1, 2):
            d.line([pts[k], pts[k + 1]], fill=accent, width=5)

        # players
        for p in spec["players"]:
            x, y = pos(p["id"], t)
            X, Y = P(x, y)
            fill, edge = TEAM[p["team"]]
            r = 20
            d.ellipse([X - r + 3, Y - r + 6, X + r + 3, Y + r + 6], fill=(10, 40, 20))
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=fill, outline=edge, width=4)
            if p.get("scorer"):
                pr = r + 10 + 5 * abs(((T * 2) % 2) - 1)
                d.ellipse([X - pr, Y - pr, X + pr, Y + pr], outline="white", width=4)
                mc.text(d, (X, Y + 2), "؟", nf, (40, 25, 0), "mm")

        # ball
        bx, by = ball_at(spec, pos, t)
        BX, BY = P(bx, by)
        d.ellipse([BX - 10, BY - 10, BX + 10, BY + 10], fill="white", outline=(20, 20, 20), width=3)

        # goal flash
        lt = T - INTRO - gt
        if 0 <= lt < 1.6:
            p = ease(lt / 0.25) * (1 - ease((lt - 1.1) / 0.5))
            lay = layer()
            ld = ImageDraw.Draw(lay)
            mc.text(ld, (W / 2, 1000), "هدف!", mc.font(900, 190), accent, "mm")
            put(img, lay, p, 0)

        # end panel
        et = T - (INTRO + A + HOLD)
        if et >= 0:
            p = ease(et / 0.45)
            lay = layer()
            ld = ImageDraw.Draw(lay)
            ld.rounded_rectangle([60, 880, W - 60, 1420], radius=40, fill=(8, 12, 26, 235),
                                 outline=accent, width=4)
            y = 960
            mc.text(ld, (W / 2, y), "تلميحات", mc.font(900, 54), accent, "mm")
            y += 95
            for c in spec["clues"]:
                mc.text(ld, (W / 2, y), c, mc.font(700, 48), "white", "mm")
                y += 75
            y += 40
            for c in spec["cta"]:
                mc.text(ld, (W / 2, y), c, mc.font(900, 50), accent if c is spec["cta"][-1] else "white", "mm")
                y += 85
            put(img, lay, p, (1 - p) * 80)

        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"saved {out} ({total:.1f}s)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
