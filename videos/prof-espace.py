#!/usr/bin/env python3
"""TikTok 9:16, 20 s : un prof (lunettes, chemise bleue, cheveux gominés) donne 3 faits sur l'espace.
Sans voix : sous-titres animés mot par mot. Le texte est dans SCRIPT ci-dessous."""
import math, os, random, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".claude", "skills", "video", "scripts"))
import render as R

W, H, FPS, DUR = 1080, 1920, 30, 20.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prof-espace.mp4")

# (début, fin, sous-titre)
SCRIPT = [
    (0.3, 2.8, "Salut ! Voici 3 faits fous sur l'espace 🚀"),
    (3.0, 5.6, "Numéro 1 : sur Vénus, un jour dure plus longtemps"),
    (5.6, 8.2, "qu'une année entière. 243 jours contre 225 !"),
    (8.6, 11.2, "Numéro 2 : Saturne est si peu dense"),
    (11.2, 13.8, "qu'elle flotterait dans une baignoire géante 🛁"),
    (14.2, 16.6, "Numéro 3 : la lumière du Soleil"),
    (16.6, 18.6, "met environ 8 minutes pour arriver jusqu'à nous ☀️"),
    (18.8, 19.9, "Abonne-toi pour la suite !"),
]
# (début, nom du tableau) ; le bras pointe le tableau au début de chaque fait
BOARD = [(0.0, "intro"), (3.0, "venus"), (8.4, "saturne"), (14.0, "lumiere"), (18.7, "outro")]

BX0, BY0, BX1, BY1 = 50, 250, 1030, 1000
DESK_Y = 1500
CHALK = (240, 240, 228)
YEL, PINK, BLUE, ORANGE = (255, 230, 120), (255, 170, 190), (150, 210, 255), (255, 180, 110)
rnd = random.Random(7)


def chalk_line(d, pts, col, w=7):
    d.line(pts, fill=col + (235,), width=w, joint="curve")


def chalk_circle(d, c, r, col, w=7):
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=col + (235,), width=w)


def chalk_text(d, xy, txt, size, col, center=False):
    f = R.font("bold", size)
    x, y = xy
    if center:
        x -= d.textlength(txt, font=f) / 2
    d.text((x, y), txt, font=f, fill=col + (235,))


def header(d, n, title):
    chalk_circle(d, (165, 345), 55, YEL)
    chalk_text(d, (165, 310), str(n), 70, YEL, center=True)
    chalk_text(d, (250, 305), title, 76, CHALK)
    chalk_line(d, [(250, 400), (250 + 32 * len(title) + 120, 404)], CHALK, 5)


def board_layer(name):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if name == "intro":
        for _ in range(40):
            x, y = rnd.randint(BX0 + 40, BX1 - 40), rnd.randint(BY0 + 40, BY1 - 40)
            if 180 < x < 900 and 430 < y < 800:
                continue
            s = rnd.randint(6, 14)
            chalk_line(d, [(x - s, y), (x + s, y)], CHALK, 4)
            chalk_line(d, [(x, y - s), (x, y + s)], CHALK, 4)
        chalk_text(d, (540, 450), "L'ESPACE", 150, CHALK, center=True)
        chalk_text(d, (540, 640), "3 faits fous", 80, YEL, center=True)
        chalk_circle(d, (870, 380), 60, ORANGE)
        d.ellipse((780, 360, 960, 400), outline=ORANGE + (235,), width=6)
    elif name == "venus":
        header(d, 1, "VÉNUS")
        chalk_circle(d, (290, 690), 150, ORANGE, 9)
        for k in range(-2, 3):
            chalk_line(d, [(170, 690 + k * 45), (410, 690 + k * 45 + 10)], ORANGE, 4)
        chalk_text(d, (500, 540), "1 jour = 243 j", 64, CHALK)
        chalk_text(d, (640, 630), ">", 90, PINK)
        chalk_text(d, (500, 750), "1 an  = 225 j", 64, CHALK)
        chalk_text(d, (540, 880), "un jour > une année !", 56, YEL, center=True)
    elif name == "saturne":
        header(d, 2, "SATURNE")
        # bathtub
        d.rounded_rectangle((200, 640, 880, 880), 90, outline=CHALK + (235,), width=8)
        d.rectangle((190, 600, 890, 660), fill=(0, 0, 0, 0))
        chalk_line(d, [(170, 650), (910, 650)], CHALK, 8)
        chalk_line(d, [(260, 880), (240, 930)], CHALK, 8)
        chalk_line(d, [(820, 880), (840, 930)], CHALK, 8)
        for i in range(3):
            y = 700 + i * 22
            pts = [(225 + k * 20, y + 8 * math.sin(k * 1.3)) for k in range(32)]
            chalk_line(d, pts, BLUE, 5)
        chalk_circle(d, (540, 610), 95, YEL, 8)
        d.ellipse((380, 585, 700, 645), outline=PINK + (235,), width=7)
        chalk_text(d, (90, 925), "densité 0,69 < eau (1)", 44, CHALK)
    elif name == "lumiere":
        header(d, 3, "LA LUMIÈRE")
        chalk_circle(d, (230, 680), 95, YEL, 9)
        for a in range(0, 360, 30):
            r = math.radians(a)
            chalk_line(d, [(230 + 115 * math.cos(r), 680 + 115 * math.sin(r)),
                           (230 + 150 * math.cos(r), 680 + 150 * math.sin(r))], YEL, 6)
        chalk_circle(d, (860, 680), 55, BLUE, 8)
        chalk_line(d, [(830, 660), (855, 650), (870, 690)], (140, 220, 150), 6)
        for x in range(400, 770, 40):
            chalk_line(d, [(x, 680), (x + 22, 680)], CHALK, 7)
        chalk_line(d, [(760, 655), (795, 680), (760, 705)], CHALK, 7)
        chalk_text(d, (590, 560), "≈ 8 min 20 s", 64, PINK, center=True)
        chalk_text(d, (540, 850), "150 millions de km", 58, CHALK, center=True)
    elif name == "outro":
        chalk_text(d, (540, 470), "À demain !", 130, CHALK, center=True)
        chalk_circle(d, (540, 790), 100, YEL, 9)
        d.arc((480, 760, 600, 860), 20, 160, fill=YEL + (235,), width=8)
        d.ellipse((500, 750, 516, 766), fill=YEL + (235,))
        d.ellipse((564, 750, 580, 766), fill=YEL + (235,))
    # chalk grain
    noise = Image.effect_noise((W, H), 70).point(lambda v: 150 + v // 3 if v > 60 else 90)
    a = im.getchannel("A")
    im.putalpha(Image.composite(noise, a, a.point(lambda v: 255 if v > 0 else 0)))
    return im


def classroom():
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        f = y / H
        d.line([(0, y), (W, y)], fill=(int(236 - 30 * f), int(222 - 34 * f), int(190 - 40 * f), 255))
    d.rectangle((0, 1460, W, H), fill=(150, 100, 60, 255))  # floor
    for x in range(-40, W, 90):
        d.line([(x, 1460), (x - 140, H)], fill=(130, 85, 50, 255), width=3)
    d.rectangle((0, 1440, W, 1460), fill=(210, 190, 160, 255))  # baseboard
    # board
    d.rounded_rectangle((BX0 - 24, BY0 - 24, BX1 + 24, BY1 + 24), 10, fill=(120, 80, 45, 255))
    d.rectangle((BX0, BY0, BX1, BY1), fill=(38, 74, 58, 255))
    smear = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(smear)
    for _ in range(14):
        x, y = rnd.randint(BX0, BX1 - 200), rnd.randint(BY0, BY1 - 80)
        sd.ellipse((x, y, x + rnd.randint(150, 350), y + rnd.randint(40, 90)), fill=(255, 255, 255, 14))
    im.alpha_composite(smear.filter(ImageFilter.GaussianBlur(20)))
    d = ImageDraw.Draw(im)
    d.rectangle((BX0 + 40, BY1 + 24, BX1 - 40, BY1 + 44), fill=(105, 70, 40, 255))  # tray
    d.rectangle((300, BY1 + 14, 360, BY1 + 26), fill=(250, 250, 245, 255))
    d.rectangle((420, BY1 + 16, 460, BY1 + 26), fill=(255, 200, 200, 255))
    # title above board
    R.draw_text(im, d, ((W - R.text_len(d, "3 FAITS FOUS SUR L'ESPACE 🚀", R.font("bold", 64))) / 2, 120),
                "3 FAITS FOUS SUR L'ESPACE 🚀", R.font("bold", 64), (60, 40, 30, 255), shadow=False)
    # bookshelf left
    d.rectangle((50, 1080, 330, 1440), fill=(110, 72, 42, 255))
    for sy in (1080, 1200, 1320):
        d.rectangle((62, sy + 12, 318, sy + 110), fill=(80, 50, 30, 255))
        x = 66
        while x < 300:
            bw = rnd.randint(18, 34)
            bh = rnd.randint(70, 96)
            d.rectangle((x, sy + 110 - bh, x + bw, sy + 110),
                        fill=rnd.choice([(200, 60, 60), (60, 120, 200), (230, 180, 60), (80, 160, 90), (150, 90, 170)]) + (255,))
            x += bw + 3
    # wall clock right
    d.ellipse((920, 1060, 1040, 1180), fill=(250, 250, 245, 255), outline=(60, 60, 60, 255), width=8)
    return im


def desk():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((360, DESK_Y, W + 10, H), fill=(140, 90, 52, 255))
    d.rectangle((345, DESK_Y - 22, W + 10, DESK_Y + 10), fill=(165, 110, 65, 255))
    d.line([(360, DESK_Y + 60), (W, DESK_Y + 60)], fill=(120, 76, 44, 255), width=4)
    # globe
    d.rectangle((440, DESK_Y - 40, 500, DESK_Y - 22), fill=(90, 60, 40, 255))
    d.rectangle((466, DESK_Y - 70, 474, DESK_Y - 40), fill=(90, 60, 40, 255))
    d.ellipse((410, DESK_Y - 190, 530, DESK_Y - 70), fill=(80, 150, 220, 255))
    d.polygon([(440, DESK_Y - 165), (480, DESK_Y - 170), (470, DESK_Y - 130), (450, DESK_Y - 110)], fill=(100, 180, 90, 255))
    d.polygon([(495, DESK_Y - 120), (515, DESK_Y - 130), (505, DESK_Y - 95)], fill=(100, 180, 90, 255))
    # books + apple
    for i, c in enumerate([(200, 60, 60), (60, 110, 190), (230, 180, 60)]):
        d.rectangle((900 - i * 6, DESK_Y - 22 - (i + 1) * 30, 1050 - i * 6, DESK_Y - 22 - i * 30), fill=c + (255,))
    d.ellipse((990, DESK_Y - 170, 1050, DESK_Y - 110), fill=(210, 40, 40, 255))
    d.line([(1020, DESK_Y - 168), (1025, DESK_Y - 188)], fill=(80, 50, 30, 255), width=5)
    d.ellipse((1024, DESK_Y - 192, 1046, DESK_Y - 178), fill=(80, 160, 70, 255))
    return im


def limb(d, a, b, w, col):
    d.line([a, b], fill=col, width=w)
    for p in (a, b):
        d.ellipse((p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2), fill=col)


def mix(a, b, p):
    return (a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p)


def speaking(t):
    for s, e, txt in SCRIPT:
        if s <= t <= e:
            return s, e, txt
    return None


def point_amount(t):
    best = 0.0
    for s, name in BOARD[1:4]:
        dt = t - s
        if 0 <= dt <= 2.0:
            best = max(best, R.ease(dt / 0.4) * min(1.0, (2.0 - dt) / 0.4))
    return best


def draw_prof(img, t):
    d = ImageDraw.Draw(img)
    talk = speaking(t)
    bob = 5 * math.sin(t * 2.3) + (4 * math.sin(t * 9) if talk else 0)
    cx, cy = 760, 1080 + bob  # head centre
    skin, skin_d = (240, 196, 160), (220, 170, 135)
    shirt, shirt_d, shirt_l = (70, 130, 215), (50, 100, 180), (120, 170, 235)
    hair, hair_l = (45, 32, 25), (140, 120, 105)

    # torso
    d.rounded_rectangle((cx - 175, cy + 170, cx + 175, DESK_Y + 40), 70, fill=shirt)
    d.rectangle((cx - 28, cy + 95, cx + 28, cy + 185), fill=skin_d)  # neck
    d.polygon([(cx - 70, cy + 165), (cx, cy + 230), (cx - 10, cy + 165)], fill=shirt_l)  # collar
    d.polygon([(cx + 70, cy + 165), (cx, cy + 230), (cx + 10, cy + 165)], fill=shirt_l)
    d.line([(cx, cy + 230), (cx, DESK_Y)], fill=shirt_d, width=4)
    for by in range(int(cy + 260), DESK_Y, 60):
        d.ellipse((cx - 7, by - 7, cx + 7, by + 7), fill=(235, 240, 250))
    d.rectangle((cx + 60, cy + 280, cx + 130, cy + 290), fill=shirt_d)  # pocket
    d.rectangle((cx + 80, cy + 262, cx + 88, cy + 290), fill=(230, 60, 60))  # pen

    # left arm (viewer right): resting on desk, small gestures when talking
    sh_r = (cx + 160, cy + 215)
    g = 0.5 + 0.5 * math.sin(t * 3.1) if talk else 0
    hand_r = mix((cx + 175, DESK_Y - 25), (cx + 230, cy + 300), g * 0.7)
    elb_r = (cx + 225, (sh_r[1] + hand_r[1]) / 2 + 60)
    limb(d, sh_r, elb_r, 62, shirt)
    limb(d, elb_r, hand_r, 54, shirt)
    d.ellipse((hand_r[0] - 30, hand_r[1] - 30, hand_r[0] + 30, hand_r[1] + 30), fill=skin)

    # right arm (viewer left): rests, or points at the board
    p = point_amount(t)
    sh_l = (cx - 160, cy + 215)
    rest_e, rest_h = (cx - 230, cy + 330), (cx - 170, DESK_Y - 25)
    pt_e, pt_h = (cx - 300, cy + 90), (cx - 380, cy - 60)
    e = mix(rest_e, pt_e, p)
    h = mix(rest_h, pt_h, p)
    limb(d, sh_l, e, 62, shirt)
    limb(d, e, h, 54, shirt)
    d.ellipse((h[0] - 30, h[1] - 30, h[0] + 30, h[1] + 30), fill=skin)
    if p > 0.3:  # index finger
        f = (h[0] + (h[0] - e[0]) * 0.45, h[1] + (h[1] - e[1]) * 0.45)
        limb(d, h, f, 18, skin)

    # head
    d.ellipse((cx - 112, cy - 30, cx - 80, cy + 40), fill=skin_d)  # ears
    d.ellipse((cx + 80, cy - 30, cx + 112, cy + 40), fill=skin_d)
    d.ellipse((cx - 95, cy - 120, cx + 95, cy + 120), fill=skin)
    # slicked-back hair with side part and gel shine
    d.chord((cx - 100, cy - 140, cx + 100, cy + 30), 180, 360, fill=hair)
    d.polygon([(cx - 100, cy - 55), (cx - 98, cy - 10), (cx - 85, cy - 40)], fill=hair)
    d.polygon([(cx + 100, cy - 55), (cx + 98, cy - 10), (cx + 85, cy - 40)], fill=hair)
    d.line([(cx - 40, cy - 128), (cx - 55, cy - 60)], fill=(25, 18, 14), width=5)  # parting
    for k, off in enumerate((-20, 10, 40, 70)):
        d.arc((cx - 70 + off, cy - 125, cx + 60 + off, cy - 40), 200, 290, fill=hair_l, width=4)
    d.arc((cx - 10, cy - 118, cx + 60, cy - 80), 190, 300, fill=(230, 230, 230), width=4)  # shine

    # eyebrows (raise at the start of each line)
    raise_ = 0
    if talk:
        raise_ = 12 * max(0.0, 1 - (t - talk[0]) / 0.5)
    for sx in (-1, 1):
        d.line([(cx + sx * 25, cy - 52 - raise_), (cx + sx * 70, cy - 48 - raise_ * 0.6)], fill=hair, width=9)

    # eyes + glasses
    blink = (t % 3.4) < 0.12
    for sx in (-1, 1):
        ex = cx + sx * 45
        if blink:
            d.line([(ex - 12, cy - 12), (ex + 12, cy - 12)], fill=(40, 30, 30), width=4)
        else:
            d.ellipse((ex - 11, cy - 24, ex + 11, cy - 2), fill=(40, 30, 30))
            d.ellipse((ex - 5, cy - 20, ex + 1, cy - 14), fill=(255, 255, 255))
        d.rounded_rectangle((ex - 38, cy - 42, ex + 38, cy + 18), 18, outline=(25, 25, 30), width=7)
    d.line([(cx - 7, cy - 22), (cx + 7, cy - 22)], fill=(25, 25, 30), width=6)
    d.line([(cx - 83, cy - 30), (cx - 98, cy - 22)], fill=(25, 25, 30), width=6)
    d.line([(cx + 83, cy - 30), (cx + 98, cy - 22)], fill=(25, 25, 30), width=6)
    # glass shine
    for sx in (-1, 1):
        ex = cx + sx * 45
        d.line([(ex + 12, cy - 34), (ex + 26, cy - 22)], fill=(255, 255, 255), width=3)

    # nose, cheeks
    d.arc((cx - 14, cy, cx + 14, cy + 34), 300, 80, fill=skin_d, width=5)
    cheeks = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(cheeks)
    for sx in (-1, 1):
        cd.ellipse((cx + sx * 58 - 22, cy + 30, cx + sx * 58 + 22, cy + 56), fill=(240, 120, 120, 70))
    img.alpha_composite(cheeks)
    d = ImageDraw.Draw(img)

    # mouth
    my = cy + 70
    if talk:
        o = abs(math.sin(t * 17)) * (0.45 + 0.55 * abs(math.sin(t * 6.3 + 1)))
    else:
        o = 0
    if o < 0.12:
        d.arc((cx - 35, my - 25, cx + 35, my + 15), 20, 160, fill=(150, 60, 60), width=6)
    else:
        mh = 10 + 38 * o
        d.ellipse((cx - 32, my - mh / 2, cx + 32, my + mh / 2), fill=(110, 30, 40))
        d.rectangle((cx - 22, my - mh / 2 + 2, cx + 22, my - mh / 2 + 9), fill=(250, 250, 250))
        d.ellipse((cx - 16, my + mh / 2 - 12, cx + 16, my + mh / 2), fill=(220, 100, 110))


def clock_hands(img, t):
    d = ImageDraw.Draw(img)
    c = (980, 1120)
    a = math.radians(t * 18)
    d.line([c, (c[0] + 45 * math.sin(a), c[1] - 45 * math.cos(a))], fill=(200, 40, 40), width=3)
    d.line([c, (c[0] + 25, c[1] - 20)], fill=(40, 40, 40), width=6)
    d.line([c, (c[0], c[1] - 38)], fill=(40, 40, 40), width=5)


def subtitles(img, t):
    talk = speaking(t)
    if not talk:
        return
    s, e, txt = talk
    words = txt.split()
    per = (e - s) / len(words)
    cur = min(len(words) - 1, int((t - s) / per))
    f = R.font("bold", 60)
    d = ImageDraw.Draw(img)
    space = d.textlength(" ", font=f)
    lines, line, lw = [], [], 0
    for i, w in enumerate(words):
        wl = R.text_len(d, w, f)
        if line and lw + space + wl > 900:
            lines.append((line, lw))
            line, lw = [], 0
        lw += (space if line else 0) + wl
        line.append((i, w, wl))
    lines.append((line, lw))
    lh = 78
    box_h = len(lines) * lh + 40
    y0 = 1720 - box_h // 2
    maxw = max(l for _, l in lines)
    pop = R.ease((t - s) / 0.15)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle(((W - maxw) / 2 - 30, y0, (W + maxw) / 2 + 30, y0 + box_h), 28, fill=(10, 10, 20, int(185 * pop)))
    y = y0 + 20
    for line, lw in lines:
        x = (W - lw) / 2
        for i, w, wl in line:
            col = (255, 214, 60, 255) if i == cur else (255, 255, 255, 255) if i < cur else (255, 255, 255, 170)
            R.draw_text(layer, ld, (x, y), w, f, col)
            x += wl + space
        y += lh
    img.alpha_composite(layer)


def main():
    print("préparation…", flush=True)
    bg = classroom()
    desk_l = desk()
    boards = {name: board_layer(name) for _, name in BOARD}
    tmp = tempfile.mkdtemp()
    silent = os.path.join(tmp, "v.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "20", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        t = i / FPS
        img = bg.copy()
        # current board, revealed with a left-to-right chalk wipe; previous one erased
        cur = [b for b in BOARD if b[0] <= t][-1]
        k = (t - cur[0]) / 1.0
        layer = boards[cur[1]]
        if k < 1:
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).rectangle((0, 0, int(BX0 + (BX1 - BX0) * R.ease(k) + 40), H), fill=255)
            layer = Image.composite(layer, Image.new("RGBA", (W, H), (0, 0, 0, 0)), mask)
        img.alpha_composite(layer)
        clock_hands(img, t)
        draw_prof(img, t)
        img.alpha_composite(desk_l)
        subtitles(img, t)
        ImageDraw.Draw(img).rectangle((0, H - 10, int(W * t / DUR), H), fill=(255, 209, 102, 255))
        fade = min(1.0, t / 0.3, (DUR - t) / 0.4)
        if fade < 1:
            img = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, max(0.0, fade))
        enc.stdin.write(img.convert("RGB").tobytes())
        if i % 150 == 0:
            print(f"  {t:.0f}s / {DUR:.0f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    audio = os.path.join(tmp, "a.wav")
    R.music_track(audio, DUR, "happy")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", audio, "-c:v", "copy",
                    "-af", "volume=0.6", "-c:a", "aac", "-b:a", "160k", "-shortest", OUT], check=True)
    print("Vidéo prête :", OUT)


if __name__ == "__main__":
    main()
