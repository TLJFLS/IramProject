#!/usr/bin/env python3
"""Mr. Gustave : génère des vidéos TikTok éducatives (9:16) à partir d'épisodes JSON.

Usage : python3 gustave.py episode1.json [episode2.json ...] [--out-dir videos/gustave]
Chaque épisode produit <slug>.mp4 et <slug>.txt (description + hashtags à copier).
"""
import argparse, asyncio, json, math, os, random, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "video", "scripts"))
import render as R

W, H, FPS = 1080, 1920, 30
BX0, BY0, BX1, BY1 = 50, 250, 1030, 1000
DESK_Y = 1500
NAME_PLATE = "M. GUSTAVE"
CHALK = (240, 240, 228)
YEL, PINK, BLUE, ORANGE = (255, 230, 120), (255, 170, 190), (150, 210, 255), (255, 180, 110)
rnd = random.Random(7)

# remplis par build_timeline()
SCRIPT = []      # (début, fin, texte du sous-titre, débuts des mots ou None)
ENVELOPE = None  # volume de la voix par image (0..1) pour animer la bouche
VOICE = "fr-FR-HenriNeural"
SR = 24000
BOARD = []       # (début, clé du tableau)
POINTS = []      # instants où le prof pointe le tableau


def episode_lines(ep):
    sections = [("intro", ep["intro"]["say"])]
    for i, f in enumerate(ep["facts"]):
        sections.append((f"fact{i}", f["say"]))
    sections.append(("outro", ep["outro"]["say"]))
    return sections


def build_timeline(ep, voice=None):
    """Minutage : durée réelle de la voix si `voice` est fourni, sinon ≈ 3,7 mots/s.
    voice : {texte: (n_échantillons, [débuts des mots en s])}"""
    SCRIPT.clear(); BOARD.clear(); POINTS.clear()
    t = 0.1
    for key, lines in episode_lines(ep):
        BOARD.append((max(0.0, t - 0.1), key))
        if key.startswith("fact"):
            POINTS.append(t)
        for line in lines:
            if voice:
                n_samp, starts = voice[line]
                d = n_samp / SR + 0.02
            else:
                d = max(1.0, 0.27 * len(line.split()) + 0.15)
                starts = None
            SCRIPT.append((t, t + d, line, starts))
            t += d + (0.05 if voice else 0.08)
        t += 0.2
    return t + 0.4


def tts_text(line):
    """Texte envoyé à la synthèse vocale : sans emojis ni symboles décoratifs."""
    txt = "".join(ch for is_e, ch in R.runs(line) if not is_e)
    txt = txt.replace("~", "environ ").replace("≈", "environ ").replace("%", " pour cent")
    return re.sub(r"\s+", " ", txt).strip()


async def _synth(line, path):
    import edge_tts
    c = edge_tts.Communicate(tts_text(line), VOICE, rate="+12%", boundary="WordBoundary",
                             proxy=os.environ.get("HTTPS_PROXY") or None)
    words = []
    with open(path, "wb") as fh:
        async for ch in c.stream():
            if ch["type"] == "audio":
                fh.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append((ch["offset"] / 1e7, ch["text"]))
    return words


def synth_voice(ep, tmp):
    """Génère la voix ligne par ligne avec edge-tts. Renvoie {texte: (échantillons numpy, débuts des mots)}."""
    import numpy as np
    out = {}
    k = 0
    for _, lines in episode_lines(ep):
        for line in lines:
            mp3 = os.path.join(tmp, f"l{k}.mp3")
            k += 1
            words = asyncio.run(_synth(line, mp3))
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-f", "s16le", "-ac", "1",
                                  "-ar", str(SR), "-"], capture_output=True, check=True).stdout
            a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            nz = np.where(np.abs(a) > 0.02)[0]
            if len(nz):  # coupe les silences : 0,05 s avant, 0,15 s après
                i0 = max(0, nz[0] - int(0.05 * SR))
                a = a[i0:nz[-1] + int(0.15 * SR)]
                words = [(o - i0 / SR, w) for o, w in words]
            out[line] = (a, align_words(display_words(line), words, len(a) / SR))
    return out


def _norm(w):
    return "".join(c for c in w.lower() if c.isalnum())


def align_words(disp, bounds, dur):
    """Associe chaque mot affiché à son instant dans la voix (par le texte, puis interpolation)."""
    starts = [None] * len(disp)
    j = 0
    for i, w in enumerate(disp):
        nw = _norm(w)
        for k in range(j, min(j + 3, len(bounds))):
            nb = _norm(bounds[k][1])
            if nw and nb and (nw == nb or nw.startswith(nb) or nb.startswith(nw)):
                starts[i] = max(0.0, bounds[k][0])
                j = k + 1
                break
    known = [(i, v) for i, v in enumerate(starts) if v is not None]
    if not known:
        return [dur * i / len(disp) for i in range(len(disp))]
    for i in range(len(disp)):
        if starts[i] is None:
            prev = max([(a, v) for a, v in known if a < i], default=(-1, 0.0))
            nxt = min([(a, v) for a, v in known if a > i], default=(len(disp), dur))
            starts[i] = prev[1] + (nxt[1] - prev[1]) * (i - prev[0]) / (nxt[0] - prev[0])
    return starts


def display_words(txt):
    """Mots des sous-titres : « : », « ! » et les emojis seuls restent collés au mot précédent."""
    words = []
    for w in txt.split():
        if words and not any(c.isalnum() for c in w):
            words[-1] += " " + w
        else:
            words.append(w)
    return words


def voice_track(voice, dur):
    """Assemble la piste voix complète et calcule l'enveloppe pour la bouche."""
    import numpy as np
    global ENVELOPE
    track = np.zeros(int(dur * SR) + SR, dtype=np.float32)
    for s, e, line, _ in SCRIPT:
        a = voice[line][0]
        i = int(s * SR)
        track[i:i + len(a)] += a[:len(track) - i]
    hop = SR // FPS
    n = len(track) // hop
    rms = np.sqrt((track[:n * hop].reshape(n, hop) ** 2).mean(axis=1))
    peak = np.percentile(rms[rms > 0.01], 95) if (rms > 0.01).any() else 1.0
    env = np.clip(rms / peak, 0, 1)
    ENVELOPE = np.convolve(env, [0.25, 0.5, 0.25], mode="same")
    return track


def speaking(t):
    for item in SCRIPT:
        if item[0] <= t <= item[1]:
            return item
    return None


def point_amount(t):
    best = 0.0
    for s in POINTS:
        dt = t - s
        if 0 <= dt <= 2.0:
            best = max(best, R.ease(dt / 0.4) * min(1.0, (2.0 - dt) / 0.4))
    return best


def fit_font(d, txt, size, max_w, kind="bold"):
    f = R.font(kind, size)
    while R.text_len(d, txt, f) > max_w and f.size > 28:
        f = R.font(kind, f.size - 2)
    return f


def board_layers(ep):
    """Un calque craie + un calque emoji par tableau."""
    out = {}
    keys = ["intro"] + [f"fact{i}" for i in range(len(ep["facts"]))] + ["outro"]
    for key in keys:
        chalk = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        emo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(chalk)
        if key == "intro":
            for _ in range(36):
                x, y = rnd.randint(BX0 + 40, BX1 - 40), rnd.randint(BY0 + 40, BY1 - 40)
                if 150 < x < 930 and 330 < y < 900:
                    continue
                s = rnd.randint(6, 14)
                chalk_line(d, [(x - s, y), (x + s, y)], CHALK, 4)
                chalk_line(d, [(x, y - s), (x, y + s)], CHALK, 4)
            big = ep["intro"].get("board", ep["theme"]).upper()
            f = fit_font(d, big, 130, 860)
            d.text(((W - d.textlength(big, font=f)) / 2, 640), big, font=f, fill=CHALK + (235,))
            sub = ep["intro"].get("board_sub", "3 faits fous")
            f2 = fit_font(d, sub, 76, 820)
            d.text(((W - d.textlength(sub, font=f2)) / 2, 800), sub, font=f2, fill=YEL + (235,))
            em = ep["intro"].get("emoji")
        elif key == "outro":
            txt = ep["outro"].get("board", "Like si t'en savais aucun !")
            lines = R.wrap(d, txt, R.font("bold", 96), 860)
            y = 640
            for ln in lines:
                f = fit_font(d, ln, 96, 860)
                d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=CHALK + (235,))
                y += 110
            em = ep["outro"].get("emoji", "👍")
        else:
            i = int(key[4:])
            fact = ep["facts"][i]
            chalk_circle(d, (165, 345), 55, YEL)
            chalk_text(d, (165, 310), str(i + 1), 70, YEL, center=True)
            title = fact["title"].upper()
            f = fit_font(d, title, 72, 740)
            d.text((250, 345 - f.size * 0.6), title, font=f, fill=CHALK + (235,))
            chalk_line(d, [(250, 405), (250 + min(740, d.textlength(title, font=f)), 409)], CHALK, 5)
            key_txt = fact.get("key", "")
            if key_txt:
                kl = R.wrap(d, key_txt, R.font("bold", 84), 880)[:2]
                y = 760 if len(kl) == 1 else 720
                for ln in kl:
                    kf = fit_font(d, ln, 84, 880)
                    d.text(((W - d.textlength(ln, font=kf)) / 2, y), ln, font=kf, fill=PINK + (235,))
                    y += 96
            if fact.get("note"):
                nf = fit_font(d, fact["note"], 44, 540, "regular")
                d.text((90, 925), fact["note"], font=nf, fill=CHALK + (220,))
            em = fact.get("emoji")
        # grain de craie
        noise = Image.effect_noise((W, H), 70).point(lambda v: 150 + v // 3 if v > 60 else 90)
        a = chalk.getchannel("A")
        chalk.putalpha(Image.composite(noise, a, a.point(lambda v: 255 if v > 0 else 0)))
        if em:
            size = 170 if key == "outro" else 230
            img = R.emoji_img(em, size)
            if img is not None:
                y = {"intro": 380, "outro": 840}.get(key, 470)
                emo.alpha_composite(img, ((W - img.width) // 2, y))
        chalk.alpha_composite(emo)
        out[key] = chalk
    return out


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


def classroom(title):
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
    tf = R.font("bold", 52)
    while R.text_len(d, title, tf) > 820 and tf.size > 30:
        tf = R.font("bold", tf.size - 2)
    R.draw_text(im, d, ((W - R.text_len(d, title, tf)) / 2, 160), title, tf, (60, 40, 30, 255), shadow=False)
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
    # name plate
    d.polygon([(395, DESK_Y - 22), (625, DESK_Y - 22), (610, DESK_Y - 84), (410, DESK_Y - 84)], fill=(60, 40, 25, 255))
    d.rectangle((420, DESK_Y - 78, 600, DESK_Y - 30), fill=(212, 175, 90, 255))
    d.rectangle((426, DESK_Y - 72, 594, DESK_Y - 36), outline=(160, 125, 50, 255), width=2)
    nf = R.font("bold", 30)
    d.text((510 - d.textlength(NAME_PLATE, font=nf) / 2, DESK_Y - 70), NAME_PLATE, font=nf, fill=(50, 35, 20, 255))
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
    if ENVELOPE is not None:
        o = float(ENVELOPE[min(len(ENVELOPE) - 1, int(t * FPS))])
    elif talk:
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


def draw_word(layer, d, xy, word, f, fill, stroke):
    x, y = xy
    for is_e, chunk in R.runs(word):
        if is_e:
            em = R.emoji_img(chunk, int(f.size * 0.95))
            if em is not None:
                layer.alpha_composite(em, (int(x), int(y + f.size * 0.12)))
                x += em.width + f.size * 0.05
        else:
            d.text((x, y), chunk, font=f, fill=fill, stroke_width=stroke, stroke_fill=(15, 15, 25, 255))
            x += d.textlength(chunk, font=f)




SUB_Y = 1290  # centre des sous-titres : hors de la zone recouverte par l'interface TikTok
SUB_GROUP = 4  # mots affichés à la fois


def subtitles(img, t):
    talk = speaking(t)
    if not talk:
        return
    s, e, txt, starts = talk
    words = display_words(txt)
    per = (e - s) / len(words)
    cur = min(len(words) - 1, int((t - s) / per))
    if starts and len(starts) == len(words):  # minutage exact de la voix
        cur = max([0] + [i for i, w0 in enumerate(starts) if s + w0 <= t])
        per = 0.0
    g0 = (cur // SUB_GROUP) * SUB_GROUP
    group = list(range(g0, min(len(words), g0 + SUB_GROUP)))
    base = R.font("bold", 84)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    space = d.textlength(" ", font=base)
    # mise en page sur 1 ou 2 lignes, largeur max 800 px (marges de sécurité)
    lines, line, lw = [], [], 0
    for i in group:
        wl = R.text_len(d, words[i], base)
        if line and lw + space + wl > 800:
            lines.append((line, lw))
            line, lw = [], 0
        lw += (space if line else 0) + wl
        line.append((i, wl))
    lines.append((line, lw))
    lh = 108
    y = SUB_Y - len(lines) * lh / 2
    for line, lw in lines:
        x = (W - lw) / 2
        for i, wl in line:
            w = words[i]
            if i == cur:  # mot actif : pastille jaune + petit rebond
                k = (t - s - (starts[i] if starts and len(starts) == len(words) else i * per)) / 0.12
                sc = 1.0 + 0.12 * math.sin(min(1.0, max(0.0, k)) * math.pi)
                f = R.font("bold", int(84 * sc))
                ww = R.text_len(d, w, f)
                cx = x + wl / 2
                d.rounded_rectangle((cx - ww / 2 - 16, y - 6 - (sc - 1) * 40, cx + ww / 2 + 16, y + f.size * 1.15),
                                    22, fill=(255, 205, 40, 255))
                draw_word(layer, d, (cx - ww / 2, y - (sc - 1) * 40), w, f, (20, 20, 30, 255), stroke=0)
            else:
                draw_word(layer, d, (x, y), w, base, (255, 255, 255, 255), stroke=7)
            x += wl + space
        y += lh
    soft = layer.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 0.55)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 255))
    shadow.putalpha(soft)
    img.alpha_composite(shadow, (0, 8))
    img.alpha_composite(layer)




def render_episode(ep, out_dir, use_voice=True):
    global ENVELOPE
    ENVELOPE = None
    tmp = tempfile.mkdtemp()
    voice = None
    if use_voice and ep.get("voice", True):
        try:
            voice = synth_voice(ep, tmp)
        except Exception as exc:  # pas de réseau / edge-tts absent : vidéo sans voix
            print(f"  voix indisponible ({exc.__class__.__name__}) -> sous-titres seuls", flush=True)
    dur = build_timeline(ep, {k: (len(v[0]), v[1]) for k, v in voice.items()} if voice else None)
    if voice:
        track = voice_track(voice, dur)
    slug = ep["slug"]
    out = os.path.join(out_dir, slug + ".mp4")
    print(f"[{slug}] {dur:.1f}s", flush=True)
    bg = classroom(ep["title"])
    desk_l = desk()
    boards = board_layers(ep)
    silent = os.path.join(tmp, "v.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "20", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    for i in range(int(dur * FPS)):
        t = i / FPS
        img = bg.copy()
        cur = [b for b in BOARD if b[0] <= t][-1]
        k = (t - cur[0]) / 0.8
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
        fade = min(1.0, (dur - t) / 0.3)  # pas de fondu au début : l'accroche doit être visible tout de suite
        if fade < 1:
            img = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, max(0.0, fade))
        enc.stdin.write(img.convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    music = ep.get("music", False)
    inputs, filt = ["-i", silent], []
    if voice:
        import numpy as np, wave
        vpath = os.path.join(tmp, "voice.wav")
        with wave.open(vpath, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
            wf.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())
        inputs += ["-i", vpath]
    if music:
        mpath = os.path.join(tmp, "m.wav")
        R.music_track(mpath, dur, music if isinstance(music, str) else "happy")
        inputs += ["-i", mpath]
    if voice and music:
        filt = ["-filter_complex", "[2:a]volume=0.25[m];[1:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]"]
    elif voice or music:
        filt = ["-map", "0:v", "-map", "1:a"]
    else:  # sans son : piste silencieuse pour la compatibilité
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        filt = ["-map", "0:v", "-map", "1:a"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, *filt, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-ar", "44100", "-shortest", out], check=True)
    with open(os.path.join(out_dir, slug + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(ep.get("caption", "").strip() + "\n")
    print(f"[{slug}] prêt : {out}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episodes", nargs="+")
    ap.add_argument("--out-dir", default="videos/gustave")
    ap.add_argument("--no-voice", action="store_true", help="sous-titres seuls, sans voix off")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    for path in args.episodes:
        with open(path, encoding="utf-8") as fh:
            render_episode(json.load(fh), args.out_dir, use_voice=not args.no_voice)


if __name__ == "__main__":
    main()
