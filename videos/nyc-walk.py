#!/usr/bin/env python3
"""TikTok 9:16, 15 s : un personnage marche dans une rue façon New York (animation 2D)."""
import math, os, random, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".claude", "skills", "video", "scripts"))
import render as R  # fonts, emoji text, music

W, H, FPS, DUR = 1080, 1920, 30, 15.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nyc-walk.mp4")
SIDEWALK_Y, CURB_Y = 1450, 1610
STREET_SPEED, MID_SPEED, FAR_SPEED = 420, 90, 25
rnd = random.Random(42)


def lerp(a, b, f):
    return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))


def sky():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    stops = [(0, (22, 18, 58)), (0.35, (88, 48, 120)), (0.62, (230, 110, 110)), (0.78, (255, 170, 100)), (1, (255, 200, 130))]
    for y in range(H):
        p = y / H
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= p <= p1:
                d.line([(0, y), (W, y)], fill=lerp(c0, c1, (p - p0) / (p1 - p0)))
                break
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((380, 980, 700, 1300), fill=(255, 230, 160, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    im.paste(glow, (0, 0), glow)
    return im


def skyline_far():
    w = int(FAR_SPEED * DUR) + W + 200
    im = Image.new("RGBA", (w, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (70, 40, 90, 255)
    x = 0
    while x < w:
        bw, bh = rnd.randint(60, 140), rnd.randint(250, 600)
        d.rectangle((x, SIDEWALK_Y - bh, x + bw, SIDEWALK_Y), fill=col)
        x += bw - rnd.randint(0, 20)
    # Empire State style
    ex = 420
    for i, (hw, top) in enumerate([(90, 650), (65, 820), (45, 900), (25, 960)]):
        d.rectangle((ex - hw, SIDEWALK_Y - top, ex + hw, SIDEWALK_Y), fill=col)
    d.polygon([(ex - 6, SIDEWALK_Y - 960), (ex + 6, SIDEWALK_Y - 960), (ex, SIDEWALK_Y - 1100)], fill=col)
    # Chrysler style
    cx = 150
    d.rectangle((cx - 50, SIDEWALK_Y - 760, cx + 50, SIDEWALK_Y), fill=col)
    for i in range(5):
        r = 50 - i * 9
        d.pieslice((cx - r, SIDEWALK_Y - 760 - r - i * 28, cx + r, SIDEWALK_Y - 760 + r - i * 28), 180, 360, fill=col)
    d.polygon([(cx - 5, SIDEWALK_Y - 880), (cx + 5, SIDEWALK_Y - 880), (cx, SIDEWALK_Y - 990)], fill=col)
    return im


def towers_mid():
    w = int(MID_SPEED * DUR) + W + 200
    im = Image.new("RGBA", (w, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = -20
    while x < w:
        bw, bh = rnd.randint(140, 260), rnd.randint(500, 900)
        base = rnd.choice([(48, 40, 78), (58, 46, 86), (40, 36, 70)])
        top = SIDEWALK_Y - bh
        d.rectangle((x, top, x + bw, SIDEWALK_Y), fill=base + (255,))
        for wy in range(top + 20, SIDEWALK_Y - 20, 26):
            for wx in range(x + 12, x + bw - 12, 22):
                if rnd.random() < 0.35:
                    d.rectangle((wx, wy, wx + 9, wy + 13), fill=(255, 210, 130, 230))
        if rnd.random() < 0.4:  # water tower
            tx = x + bw // 2
            d.rectangle((tx - 22, top - 55, tx + 22, top - 15), fill=(60, 40, 40, 255))
            d.polygon([(tx - 26, top - 55), (tx + 26, top - 55), (tx, top - 80)], fill=(50, 32, 32, 255))
            d.line([(tx - 18, top - 15), (tx - 18, top)], fill=(40, 30, 30, 255), width=4)
            d.line([(tx + 18, top - 15), (tx + 18, top)], fill=(40, 30, 30, 255), width=4)
        x += bw + rnd.randint(10, 40)
    return im


SIGNS = ["DELI", "PIZZA", "BAGELS", "COFFEE", "BODEGA", "24H", "BOOKS", "DINER", "TACOS", "VINYL"]


def street_front():
    w = int(STREET_SPEED * DUR) + W + 400
    im = Image.new("RGBA", (w, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sign_font = R.font("bold", 46)
    x = 0
    while x < w:
        bw = rnd.randint(380, 520)
        floors = rnd.randint(2, 3)
        fh = 250
        top = SIDEWALK_Y - 430 - floors * fh
        brick = rnd.choice([(150, 70, 55), (125, 60, 50), (170, 95, 70), (110, 75, 65), (140, 110, 90)])
        d.rectangle((x, top, x + bw, SIDEWALK_Y), fill=brick + (255,))
        d.rectangle((x - 8, top - 22, x + bw + 8, top + 6), fill=lerp(brick, (40, 30, 30), 0.5) + (255,))  # cornice
        cols = 3 if bw < 450 else 4
        cw = bw / cols
        for f in range(floors):
            wy = top + 45 + f * fh
            for c in range(cols):
                wx = int(x + c * cw + cw * 0.22)
                ww = int(cw * 0.56)
                lit = rnd.random() < 0.45
                d.rectangle((wx - 6, wy - 6, wx + ww + 6, wy + 156), fill=(235, 225, 210, 255))
                d.rectangle((wx, wy, wx + ww, wy + 150), fill=(255, 205, 120, 255) if lit else (40, 45, 70, 255))
                d.line([(wx + ww // 2, wy), (wx + ww // 2, wy + 150)], fill=(235, 225, 210, 255), width=4)
        if rnd.random() < 0.7:  # fire escape
            fx0, fx1 = int(x + cw * 0.1), int(x + cw * 2.0)
            for f in range(1, floors):
                py = top + f * fh + 5
                d.rectangle((fx0, py, fx1, py + 8), fill=(25, 25, 30, 255))
                for rx in range(fx0, fx1, 14):
                    d.line([(rx, py - 40), (rx, py)], fill=(25, 25, 30, 255), width=3)
                d.line([(fx0, py - 40), (fx1, py - 40)], fill=(25, 25, 30, 255), width=4)
                if f < floors - 1:
                    d.line([(fx0 + 20, py), (fx1 - 30, py + fh - 40)], fill=(25, 25, 30, 255), width=6)
        # shop
        sy = SIDEWALK_Y - 430
        d.rectangle((x + 10, sy, x + bw - 10, SIDEWALK_Y), fill=(30, 30, 38, 255))
        d.rectangle((x + 30, sy + 110, x + bw - 140, SIDEWALK_Y - 40), fill=(255, 225, 160, 255))
        d.rectangle((x + bw - 125, sy + 90, x + bw - 35, SIDEWALK_Y), fill=(80, 50, 40, 255))
        aw = rnd.choice([(200, 40, 50), (30, 110, 70), (30, 70, 150), (220, 140, 30)])
        for i in range(0, bw - 20, 40):
            d.rectangle((x + 10 + i, sy, x + 30 + i, sy + 70), fill=aw + (255,))
            d.rectangle((x + 30 + i, sy, x + 50 + i, sy + 70), fill=(245, 240, 230, 255))
        sign = rnd.choice(SIGNS)
        tw = d.textlength(sign, font=sign_font)
        sx = x + (bw - tw) / 2
        d.rectangle((sx - 20, sy - 70, sx + tw + 20, sy - 8), fill=(20, 20, 25, 255))
        d.text((sx, sy - 66), sign, font=sign_font, fill=rnd.choice([(255, 80, 120), (90, 230, 255), (255, 220, 80)]) + (255,))
        x += bw + 6
    return im


def lamp_sprite():
    im = Image.new("RGBA", (300, 760), (0, 0, 0, 0))
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((60, 20, 240, 200), fill=(255, 220, 140, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    im.alpha_composite(glow)
    d = ImageDraw.Draw(im)
    pole = (28, 50, 40, 255)
    d.rectangle((140, 100, 158, 760), fill=pole)
    d.rectangle((128, 720, 170, 760), fill=pole)
    d.polygon([(110, 110), (188, 110), (172, 80), (126, 80)], fill=pole)
    d.ellipse((124, 104, 174, 130), fill=(255, 240, 190, 255))
    return im


def taxi_sprite(flip=False):
    im = Image.new("RGBA", (420, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y0 = 60
    d.rounded_rectangle((10, y0 + 30, 410, y0 + 105), 22, fill=(250, 195, 20, 255))
    d.polygon([(110, y0 + 32), (150, y0 - 10), (300, y0 - 10), (340, y0 + 32)], fill=(250, 195, 20, 255))
    d.polygon([(125, y0 + 30), (158, y0 - 2), (220, y0 - 2), (220, y0 + 30)], fill=(60, 80, 110, 255))
    d.polygon([(230, y0 + 30), (230, y0 - 2), (292, y0 - 2), (325, y0 + 30)], fill=(60, 80, 110, 255))
    d.rectangle((10, y0 + 62, 410, y0 + 72), fill=(25, 25, 25, 255))  # checker stripe
    for i in range(10, 410, 20):
        d.rectangle((i, y0 + 62, i + 10, y0 + 67), fill=(245, 245, 245, 255))
    d.ellipse((12, y0 + 45, 34, y0 + 62), fill=(255, 250, 220, 255))
    d.ellipse((392, y0 + 45, 408, y0 + 62), fill=(220, 40, 40, 255))
    for wx in (95, 325):
        d.ellipse((wx - 38, y0 + 72, wx + 38, y0 + 148), fill=(20, 20, 20, 255))
        d.ellipse((wx - 16, y0 + 94, wx + 16, y0 + 126), fill=(160, 160, 165, 255))
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        d = ImageDraw.Draw(im)
    d.rectangle((180, y0 - 32, 240, y0 - 10), fill=(255, 245, 210, 255))
    d.text((188, y0 - 32), "TAXI", font=R.font("bold", 18), fill=(30, 30, 30, 255))
    return im.resize((int(im.width * 1.35), int(im.height * 1.35)), Image.LANCZOS)


def limb(d, a, b, width, color):
    d.line([a, b], fill=color, width=width)
    r = width // 2
    for p in (a, b):
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=color)


def at(p, ang_deg, length):
    a = math.radians(ang_deg)
    return (p[0] + length * math.sin(a), p[1] + length * math.cos(a))


def draw_walker(img, t):
    d = ImageDraw.Draw(img)
    ph = 2 * math.pi * t * (STREET_SPEED / 480)  # stride matches sidewalk speed
    ground = 1575
    bob = 9 * abs(math.cos(ph))
    hip = (520, ground - 268 - bob)
    skin, hoodie, hoodie_d = (198, 140, 100), (215, 60, 55), (160, 40, 40)
    jeans, jeans_d = (45, 70, 125), (32, 50, 95)
    # shadow
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((420, ground - 14, 640, ground + 18), fill=(0, 0, 0, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)

    def leg(phase, col):
        th = 30 * math.sin(phase)
        knee_bend = 50 * max(0.0, math.cos(phase)) + 4
        k = at(hip, th, 135)
        sh_ang = th - knee_bend
        a = at(k, sh_ang, 135)
        limb(d, hip, k, 46, col)
        limb(d, k, a, 40, col)
        toe = (a[0] + 48 * math.cos(math.radians(sh_ang)), a[1] - 48 * math.sin(math.radians(sh_ang)) * 0.3)
        limb(d, (a[0] - 10, a[1] + 8), (toe[0], toe[1] + 8), 26, (240, 240, 240) if col == jeans else (200, 200, 200))

    lean = 6
    shoulder = at(hip, 180 + lean, 205)

    def arm(phase, col, hand):
        up = -32 * math.sin(phase)
        e = at(shoulder, up, 110)
        f = at(e, up + 28, 100)
        limb(d, shoulder, e, 36, col)
        limb(d, e, f, 32, col)
        d.ellipse((f[0] - 15, f[1] - 15, f[0] + 15, f[1] + 15), fill=hand)

    arm(ph, hoodie_d, (170, 118, 85))       # back arm
    leg(ph + math.pi, jeans_d)               # back leg
    # backpack
    bp = at(hip, 180 + lean, 120)
    d.rounded_rectangle((bp[0] - 92, bp[1] - 80, bp[0] - 30, bp[1] + 60), 18, fill=(35, 35, 40))
    leg(ph, jeans)                           # front leg
    limb(d, hip, shoulder, 92, hoodie)       # torso
    # head
    neck = at(shoulder, 180 + lean, 22)
    head = at(neck, 180 + lean, 52)
    d.ellipse((head[0] - 62, head[1] - 40, head[0] + 18, head[1] + 50), fill=hoodie_d)  # hood
    d.ellipse((head[0] - 48, head[1] - 52, head[0] + 48, head[1] + 52), fill=skin)
    d.polygon([(head[0] + 44, head[1] - 4), (head[0] + 58, head[1] + 12), (head[0] + 42, head[1] + 16)], fill=skin)
    d.ellipse((head[0] + 18, head[1] - 12, head[0] + 28, head[1] - 2), fill=(30, 25, 25))
    d.chord((head[0] - 54, head[1] - 70, head[0] + 52, head[1] + 20), 180, 360, fill=(25, 25, 30))  # beanie
    d.rectangle((head[0] - 54, head[1] - 30, head[0] + 52, head[1] - 18), fill=(230, 180, 40))
    arm(ph + math.pi, hoodie, skin)          # front arm


def ground(img, t):
    d = ImageDraw.Draw(img)
    off = (t * STREET_SPEED) % 160
    d.rectangle((0, SIDEWALK_Y, W, CURB_Y), fill=(150, 142, 138))
    for x in range(-int(off), W + 160, 160):
        d.line([(x, SIDEWALK_Y), (x - 60, CURB_Y)], fill=(125, 118, 115), width=4)
    d.rectangle((0, CURB_Y, W, CURB_Y + 22), fill=(185, 180, 175))
    d.rectangle((0, CURB_Y + 22, W, H), fill=(48, 48, 55))
    off2 = (t * STREET_SPEED) % 220
    for x in range(-int(off2), W + 220, 220):
        d.rectangle((x, 1800, x + 120, 1812), fill=(240, 240, 230))


def main():
    print("préparation des décors…", flush=True)
    bg = sky().convert("RGBA")
    far, mid, front = skyline_far(), towers_mid(), street_front()
    lamp, taxi = lamp_sprite(), taxi_sprite()
    taxi_r = taxi_sprite(flip=True)
    vign = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vign).ellipse((-300, -200, W + 300, H + 200), fill=255)
    vign = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), Image.new("RGBA", (W, H), (0, 0, 0, 120)),
                           vign.filter(ImageFilter.GaussianBlur(160)))

    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for y in range(650):
        sd.line([(0, y), (W, y)], fill=(10, 8, 25, int(170 * (1 - y / 650) ** 1.2)))
    vign.alpha_composite(shade)

    tmp = tempfile.mkdtemp()
    silent = os.path.join(tmp, "v.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "20", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    title_f, sub_f = R.font("bold", 92), R.font("regular", 52)
    n = int(DUR * FPS)
    for i in range(n):
        t = i / FPS
        img = bg.copy()
        img.alpha_composite(far.crop((int(t * FAR_SPEED), 0, int(t * FAR_SPEED) + W, H)))
        img.alpha_composite(mid.crop((int(t * MID_SPEED), 0, int(t * MID_SPEED) + W, H)))
        img.alpha_composite(front.crop((int(t * STREET_SPEED), 0, int(t * STREET_SPEED) + W, H)))
        ground(img, t)
        wl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_walker(wl, t)
        wl = wl.crop((250, 950, 850, 1610)).resize((300, 330), Image.LANCZOS)
        img.alpha_composite(wl, (520 - 135, 1575 - 312))
        for k in range(-1, 4):  # street lamps on the curb
            lx = k * 700 - (t * STREET_SPEED) % 700 + 350
            img.alpha_composite(lamp, (int(lx), CURB_Y - 740))
        for start, lane_y, speed, spr in ((0.5, 1600, -650, taxi), (4.0, 1600, -650, taxi), (8.5, 1600, -650, taxi),
                                          (2.0, 1700, 260, taxi_r), (9.0, 1700, 260, taxi_r)):
            if speed < 0:
                x = W + 50 + (t - start) * (speed - STREET_SPEED)
            else:
                x = -600 + (t - start) * (speed + 0)
            if -600 < x < W + 60:
                img.alpha_composite(spr, (int(x), lane_y))
        img.alpha_composite(vign)
        over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(over)
        for txt, f, y, t0, t1 in (("Une balade à New York 🗽", title_f, 200, 0.3, 4.5),
                                   ("golden hour sur Brooklyn", sub_f, 440, 0.8, 4.5),
                                   ("NYC vibes 🌆", title_f, 260, 10.8, 15.0),
                                   ("Abonne-toi pour la suite", sub_f, 390, 11.3, 15.0)):
            if t0 <= t <= t1:
                p = R.ease((t - t0) / 0.6) * min(1.0, (t1 - t) / 0.5)
                lines = R.wrap(od, txt, f, int(W * 0.86))
                for j, line in enumerate(lines):
                    lw = R.text_len(od, line, f)
                    R.draw_text(over, od, ((W - lw) / 2, y + j * f.size * 1.2 + (1 - p) * 40), line, f,
                                (255, 255, 255, int(255 * max(0, p))))
        img.alpha_composite(over)
        ImageDraw.Draw(img).rectangle((0, H - 10, int(W * t / DUR), H), fill=(255, 209, 102, 255))
        fade = min(1.0, t / 0.4, (DUR - t) / 0.5)
        if fade < 1:
            img = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, max(0.0, fade))
        enc.stdin.write(img.convert("RGB").tobytes())
        if i % 90 == 0:
            print(f"  {t:.0f}s / {DUR:.0f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    audio = os.path.join(tmp, "a.wav")
    R.music_track(audio, DUR, "calm")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", audio, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", OUT], check=True)
    print("Vidéo prête :", OUT)


if __name__ == "__main__":
    main()
