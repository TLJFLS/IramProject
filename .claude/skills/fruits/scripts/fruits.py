#!/usr/bin/env python3
"""Fruits qui parlent (3D) : feuilleton TikTok 9:16 à partir d'un épisode JSON.

Usage : python3 fruits.py episode.json [episode2.json ...] [--out-dir videos/fruits]
Chaque épisode donne <slug>.mp4 et <slug>.txt (description).
Méthode rapide : pour chaque plan, Blender calcule l'image en 3D une fois, puis seulement la zone du
visage pour les poses de bouche (3 ouvertures) et le clignement ; l'animation choisit la pose selon la voix.
"""
import argparse, asyncio, hashlib, json, math, os, re, subprocess, sys, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "video", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "gustave", "scripts"))
import render as R
import gustave as G  # sous-titres, alignement des mots

W, H, FPS, SR = 1080, 1920, 30, 24000
DEFAULTS = {  # fruit -> (voix, hauteur, couleur, emoji)
    "fraise": ("fr-FR-DeniseNeural", "+25Hz", (255, 77, 109), "🍓"),
    "banane": ("fr-FR-HenriNeural", "+0Hz", (255, 210, 63), "🍌"),
    "kiwi": ("fr-FR-RemyMultilingualNeural", "+5Hz", (139, 195, 74), "🥝"),
    "orange": ("fr-CA-AntoineNeural", "+0Hz", (255, 159, 28), "🍊"),
    "pomme": ("fr-FR-VivienneMultilingualNeural", "+10Hz", (230, 57, 70), "🍎"),
    "citron": ("fr-FR-EloiseNeural", "+10Hz", (247, 231, 51), "🍋"),
}


# ---------- voix ----------
async def _synth(text, voice, pitch, path):
    import edge_tts
    c = edge_tts.Communicate(G.tts_text(text), voice, rate="+10%", pitch=pitch, boundary="WordBoundary",
                             proxy=os.environ.get("HTTPS_PROXY") or None)
    words = []
    with open(path, "wb") as fh:
        async for ch in c.stream():
            if ch["type"] == "audio":
                fh.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append((ch["offset"] / 1e7, ch["text"]))
    return words


def synth_line(text, voice, pitch, tmp, k):
    mp3 = os.path.join(tmp, f"l{k}.mp3")
    words = asyncio.run(_synth(text, voice, pitch, mp3))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    nz = np.where(np.abs(a) > 0.02)[0]
    if len(nz):
        i0 = max(0, nz[0] - int(0.05 * SR))
        a = a[i0:nz[-1] + int(0.12 * SR)]
        words = [(o - i0 / SR, w) for o, w in words]
    return a, G.align_words(G.display_words(text), words, len(a) / SR)


# ---------- rendu 3D des plans ----------
def render_shots(ep, plan, cache):
    import fruits3d as F
    F.build_scene(ep["cast"])
    out = {}
    for key in sorted(set(p["key"] for p in plan)):
        speaker, emotion, kind = key
        d = os.path.join(cache, f"{speaker}-{emotion}-{kind}")
        os.makedirs(d, exist_ok=True)
        for n in F.CHARS:
            F.pose(n, "neutre")
        F.shot(kind, speaker if kind != "wide" else None)
        F.pose(speaker, emotion, 0)
        base = os.path.join(d, "base.png")
        if not os.path.exists(base):
            F.render(base)
        region = F.face_region(speaker)
        variants = {}
        for name, (mouth, blink) in {"m1": (1, False), "m2": (2, False), "m3": (3, False), "blink": (0, True)}.items():
            path = os.path.join(d, name + ".png")
            if not os.path.exists(path):
                F.pose(speaker, emotion, mouth, blink)
                F.render(path, region)
            variants[name] = path
        out[key] = {"base": base, "region": region, **variants}
        print(f"  plan {speaker}/{emotion}/{kind} ok", flush=True)
    return out


def load_shot(info):
    base = Image.open(info["base"]).convert("RGB")
    bw, bh = base.size
    x0, y0, x1, y1 = info["region"]
    box = (int(round(x0 * bw)), int(round((1 - y1) * bh)))
    layers = {"m0": base}
    for name in ("m1", "m2", "m3", "blink"):
        crop = Image.open(info[name]).convert("RGB")
        mask = Image.new("L", crop.size, 0)
        ImageDraw.Draw(mask).rectangle((6, 6, crop.width - 7, crop.height - 7), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(4))
        im = base.copy()
        im.paste(crop, box, mask)
        layers[name] = im
    return layers


# ---------- montage ----------
def name_tag(img, who, ep):
    ch = next(c for c in ep["cast"] if c["name"] == who)
    col = tuple(ch.get("color", DEFAULTS[ch["fruit"]][2]))
    label = f'{ch.get("emoji", DEFAULTS[ch["fruit"]][3])} {ch.get("label", who.capitalize())}'
    f = R.font("bold", 54)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw = R.text_len(d, label, f)
    x, y = (W - tw) / 2, 1110
    d.rounded_rectangle((x - 26, y - 10, x + tw + 26, y + 72), 36, fill=col + (255,))
    R.draw_text(layer, d, (x, y), label, f, (20, 20, 30, 255), shadow=False)
    img.alpha_composite(layer)


def render_episode(ep, out_dir):
    slug = ep["slug"]
    tmp = tempfile.mkdtemp()
    cache = os.path.join(out_dir, ".cache", slug)
    cast = {c["name"]: c for c in ep["cast"]}
    # 1) voix
    print(f"[{slug}] voix…", flush=True)
    lines, t = [], 0.15
    for k, ln in enumerate(ep["lines"]):
        c = cast[ln["who"]]
        voice, pitch = c.get("voice", DEFAULTS[c["fruit"]][0]), c.get("pitch", DEFAULTS[c["fruit"]][1])
        a, starts = synth_line(ln["say"], voice, pitch, tmp, k)
        emo = ln.get("emotion", "neutre")
        kind = ln.get("shot", "zoom" if emo == "choc" else "close")
        lines.append({**ln, "audio": a, "start": t, "end": t + len(a) / SR, "starts": starts,
                      "key": (ln["who"], emo, kind)})
        t += len(a) / SR + ln.get("pause", 0.18)
    dur = t + 0.5
    # 2) 3D
    print(f"[{slug}] rendu 3D de {len(set(l['key'] for l in lines))} plans…", flush=True)
    shots = render_shots(ep, lines, cache)
    # 3) audio + enveloppe
    track = np.zeros(int(dur * SR) + SR, dtype=np.float32)
    for ln in lines:
        i = int(ln["start"] * SR)
        track[i:i + len(ln["audio"])] += ln["audio"]
    hop = SR // FPS
    n = len(track) // hop
    rms = np.sqrt((track[:n * hop].reshape(n, hop) ** 2).mean(axis=1))
    env = np.convolve(np.clip(rms / max(1e-4, np.percentile(rms[rms > 0.01], 92)), 0, 1), [0.3, 0.4, 0.3], mode="same")
    # 4) images
    G.SCRIPT.clear()
    for ln in lines:
        G.SCRIPT.append((ln["start"], ln["end"], ln["say"], ln["starts"]))
    G.ENVELOPE = None
    loaded = {}
    silent = os.path.join(tmp, "v.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                            "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    title_f = R.font("bold", 50)
    for i in range(int(dur * FPS)):
        tt = i / FPS
        cur = lines[0]
        for ln in lines:
            if ln["start"] - 0.1 <= tt:
                cur = ln
        if cur["key"] not in loaded:
            loaded = {cur["key"]: load_shot(shots[cur["key"]])}
        layers = loaded[cur["key"]]
        e = float(env[min(len(env) - 1, i)]) if cur["start"] <= tt <= cur["end"] + 0.05 else 0.0
        lvl = 0 if e < 0.12 else 1 if e < 0.4 else 2 if e < 0.7 else 3
        blink = lvl == 0 and (tt + hash(cur["who"]) % 7 * 0.37) % 3.1 < 0.12
        frame = layers["blink" if blink else f"m{lvl}"]
        # mouvement de caméra : léger zoom avant, « coup de zoom » sur les chocs
        p = (tt - cur["start"]) / max(0.5, cur["end"] - cur["start"] + 0.2)
        z = 1.0 + 0.05 * min(1.0, max(0.0, p))
        if cur.get("emotion") == "choc":
            z += 0.1 * R.ease((tt - cur["start"] + 0.1) / 0.25)
        sx = int(frame.width / z)
        sy = int(frame.height / z)
        ox, oy = (frame.width - sx) // 2, int((frame.height - sy) * 0.4)
        img = frame.crop((ox, oy, ox + sx, oy + sy)).resize((W, H), Image.BICUBIC).convert("RGBA")
        if ep.get("title") and tt < 3.0:
            od = ImageDraw.Draw(img)
            R.draw_text(img, od, ((W - R.text_len(od, ep["title"], title_f)) / 2, 240), ep["title"], title_f,
                        (255, 255, 255, 255))
        if cur["start"] <= tt <= cur["end"]:
            name_tag(img, cur["who"], ep)
        G.subtitles(img, tt)
        fade = min(1.0, (dur - tt) / 0.3)
        if fade < 1:
            img = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, max(0.0, fade))
        enc.stdin.write(img.convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    vpath = os.path.join(tmp, "voice.wav")
    with wave.open(vpath, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())
    out = os.path.join(out_dir, slug + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", vpath, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-shortest", out], check=True)
    with open(os.path.join(out_dir, slug + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(ep.get("caption", "").strip() + "\n")
    print(f"[{slug}] prêt : {out} ({dur:.1f}s)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episodes", nargs="+")
    ap.add_argument("--out-dir", default="videos/fruits")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    for path in args.episodes:
        with open(path, encoding="utf-8") as fh:
            render_episode(json.load(fh), args.out_dir)


if __name__ == "__main__":
    main()
