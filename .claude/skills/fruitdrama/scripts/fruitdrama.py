#!/usr/bin/env python3
"""Fruit drama (images IA) : histoires de personnages à tête de fruit, format TikTok 9:16.

Usage : python3 fruitdrama.py episode.json [...] [--out-dir videos/fruitdrama] [--images-only]
Images : kie.ai (modèle google/nano-banana, ~4 crédits/image, clé dans KIE_API_KEY).
La 1re image d'un épisode fixe les personnages ; les suivantes sont générées à partir d'elle
(google/nano-banana-edit) pour garder les mêmes têtes de fruits.
Montage : zooms / panoramiques, voix edge-tts (narrateur + une voix par personnage), sous-titres.
"""
import argparse, json, os, subprocess, sys, tempfile, time, urllib.request, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../../video/scripts", "../../gustave/scripts", "../../fruits/scripts"):
    sys.path.insert(0, os.path.join(HERE, p))
import render as R
import gustave as G
from fruits import synth_line

W, H, FPS, SR = 1080, 1920, 30, 24000
API = "https://api.kie.ai/api/v1/jobs"
STYLE = ("Cinematic 3D Pixar-style render, ultra detailed, dramatic movie lighting, vertical 9:16 composition. "
         "The characters are humans with giant realistic fruit heads that have expressive cartoon faces. ")
ALLOW_PAID = False
NARRATOR = {"voice": "fr-FR-RemyMultilingualNeural", "pitch": "-5Hz", "color": (240, 240, 240), "label": "", "emoji": ""}


# ---------- génération d'images (kie.ai) ----------
def kie(method, path, body=None):
    req = urllib.request.Request(f"{API}/{path}", method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {os.environ['KIE_API_KEY']}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def submit(prompt, ref_url=None):
    if ref_url:
        body = {"model": "google/nano-banana-edit",
                "input": {"prompt": prompt, "image_urls": [ref_url], "output_format": "png", "image_size": "9:16"}}
    else:
        body = {"model": "google/nano-banana", "input": {"prompt": prompt, "output_format": "png", "image_size": "9:16"}}
    r = kie("POST", "createTask", body)
    if r.get("code") != 200:
        raise RuntimeError(f"kie.ai : {r}")
    return r["data"]["taskId"]


def wait(task):
    for _ in range(90):
        d = kie("GET", f"recordInfo?taskId={task}")["data"]
        if d["state"] == "success":
            return json.loads(d["resultJson"])["resultUrls"][0]
        if d["state"] == "fail":
            raise RuntimeError(f"génération échouée : {d.get('failMsg')}")
        time.sleep(5)
    raise TimeoutError(task)


def download(url, path):
    for k in range(4):
        try:
            urllib.request.urlretrieve(url, path)
            return
        except Exception:
            time.sleep(10 * (k + 1))
    raise RuntimeError(f"téléchargement impossible : {url}")


def generate_images(ep, cache):
    """Génère les images manquantes. Cache : <cache>/scene<i>.png + urls.json (rien n'est payé deux fois)."""
    os.makedirs(cache, exist_ok=True)
    meta_path = os.path.join(cache, "urls.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    scenes = ep["scenes"]
    missing = [i for i in range(len(scenes)) if str(i) not in meta]
    if missing and not ALLOW_PAID:
        sys.exit("Images manquantes : la génération kie.ai coûte des crédits. L'utilisateur a demandé de NE PAS "
                 "les dépenser. Utiliser plutôt le skill gratuit `fruits` (décors gratuits + fruits 3D). "
                 "Option --use-kie-credits uniquement si l'utilisateur l'autorise explicitement pour cette demande.")

    def prompt_of(sc, i):
        p = STYLE + sc["image"]
        if i > 0:
            p = ("Same characters, same fruit heads, same art style as the reference image, new scene: " + sc["image"]
                 + " " + STYLE)
        return p

    if "0" not in meta:
        meta["0"] = wait(submit(prompt_of(scenes[0], 0)))
        json.dump(meta, open(meta_path, "w"), indent=1)
    if not os.path.exists(os.path.join(cache, "scene0.png")):
        download(meta["0"], os.path.join(cache, "scene0.png"))
    todo = {i: submit(prompt_of(sc, i), meta["0"]) for i, sc in enumerate(scenes) if i > 0 and str(i) not in meta}
    for i, task in todo.items():
        meta[str(i)] = wait(task)
        json.dump(meta, open(meta_path, "w"), indent=1)
    for i in range(1, len(scenes)):
        p = os.path.join(cache, f"scene{i}.png")
        if not os.path.exists(p):
            download(meta[str(i)], p)
    print(f"  {len(todo) + ('0' not in meta)} image(s) générée(s), {len(scenes)} au total", flush=True)


# ---------- montage ----------
def who_info(ep, who):
    if who == "narrateur":
        return NARRATOR
    c = ep["cast"][who]
    return {"voice": c["voice"], "pitch": c.get("pitch", "+0Hz"), "color": tuple(c.get("color", (255, 214, 60))),
            "label": c.get("label", who.capitalize()), "emoji": c.get("emoji", "")}


def name_tag(img, info):
    if not info["label"]:
        return
    f = R.font("bold", 52)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    label = f'{info["emoji"]} {info["label"]}'.strip()
    tw = R.text_len(d, label, f)
    x, y = (W - tw) / 2, 1112
    d.rounded_rectangle((x - 26, y - 10, x + tw + 26, y + 70), 34, fill=info["color"] + (255,))
    R.draw_text(layer, d, (x, y), label, f, (20, 20, 30, 255), shadow=False)
    img.alpha_composite(layer)


MOTIONS = ["zoom_in", "pan_right", "zoom_out", "pan_left"]


def camera(img, p, motion):
    """Effet Ken Burns : renvoie l'image 1080x1920 pour l'avancement p (0..1) du plan."""
    base = max(W / img.width, H / img.height) * 1.12
    p = p * p * (3 - 2 * p)  # mouvement doux
    if motion == "zoom_in":
        s, cx, cy = base * (1 + 0.12 * p), 0.5, 0.45
    elif motion == "zoom_out":
        s, cx, cy = base * (1.12 - 0.12 * p), 0.5, 0.45
    elif motion == "pan_right":
        s, cx, cy = base * 1.05, 0.42 + 0.16 * p, 0.45
    else:
        s, cx, cy = base * 1.05, 0.58 - 0.16 * p, 0.45
    cw, ch = W / s, H / s
    x0 = min(max(0, cx * img.width - cw / 2), img.width - cw)
    y0 = min(max(0, cy * img.height - ch / 2), img.height - ch)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def render_episode(ep, out_dir, images_only=False):
    slug = ep["slug"]
    cache = os.path.join(out_dir, ".cache", slug)
    print(f"[{slug}] images…", flush=True)
    generate_images(ep, cache)
    if images_only:
        return
    tmp = tempfile.mkdtemp()
    print(f"[{slug}] voix…", flush=True)
    lines, t, k = [], 0.1, 0
    scene_spans = []
    for si, sc in enumerate(ep["scenes"]):
        s0 = t
        for ln in sc["lines"]:
            info = who_info(ep, ln["who"])
            a, starts = synth_line(ln["say"], info["voice"], info["pitch"], tmp, k)
            k += 1
            lines.append({**ln, "info": info, "audio": a, "start": t, "end": t + len(a) / SR, "starts": starts})
            t += len(a) / SR + 0.15
        t += 0.2
        scene_spans.append((s0 - (0.1 if si == 0 else 0.2), t - 0.2))
    dur = t + 0.4
    track = np.zeros(int(dur * SR) + SR, dtype=np.float32)
    for ln in lines:
        i = int(ln["start"] * SR)
        track[i:i + len(ln["audio"])] += ln["audio"]
    G.SCRIPT.clear()
    for ln in lines:
        G.SCRIPT.append((ln["start"], ln["end"], ln["say"], ln["starts"]))
    imgs = [Image.open(os.path.join(cache, f"scene{i}.png")).convert("RGB") for i in range(len(ep["scenes"]))]
    silent = os.path.join(tmp, "v.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                            "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    title_f = R.font("bold", 58)
    for fi in range(int(dur * FPS)):
        tt = fi / FPS
        si = max([i for i, (a, b) in enumerate(scene_spans) if a <= tt] or [0])
        a, b = scene_spans[si]
        b = scene_spans[si + 1][0] if si + 1 < len(scene_spans) else dur
        motion = ep["scenes"][si].get("motion", MOTIONS[si % len(MOTIONS)])
        frame = camera(imgs[si], min(1.0, (tt - a) / max(0.1, b - a)), motion)
        if si > 0 and tt - a < 0.25:  # fondu rapide entre deux scènes
            prev = camera(imgs[si - 1], 1.0, ep["scenes"][si - 1].get("motion", MOTIONS[(si - 1) % len(MOTIONS)]))
            frame = Image.blend(prev, frame, (tt - a) / 0.25)
        img = frame.convert("RGBA")
        if ep.get("title") and tt < 2.8:
            od = ImageDraw.Draw(img)
            tw = R.text_len(od, ep["title"], title_f)
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.rounded_rectangle(((W - tw) / 2 - 30, 250, (W + tw) / 2 + 30, 340), 20, fill=(200, 20, 40, 230))
            R.draw_text(layer, ld, ((W - tw) / 2, 262), ep["title"], title_f, (255, 255, 255, 255), shadow=False)
            img.alpha_composite(layer)
        cur = next((ln for ln in lines if ln["start"] <= tt <= ln["end"]), None)
        if cur:
            name_tag(img, cur["info"])
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
    music = os.path.join(tmp, "m.wav")
    R.music_track(music, dur, ep.get("music", "epic"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", vpath, "-i", music,
                    "-filter_complex", "[2:a]volume=0.18[m];[1:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
                    "-shortest", out], check=True)
    with open(os.path.join(out_dir, slug + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(ep.get("caption", "").strip() + "\n")
    print(f"[{slug}] prêt : {out} ({dur:.1f}s)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episodes", nargs="+")
    ap.add_argument("--out-dir", default="videos/fruitdrama")
    ap.add_argument("--images-only", action="store_true")
    ap.add_argument("--use-kie-credits", action="store_true",
                    help="autorise à dépenser des crédits kie.ai (seulement avec l'accord explicite de l'utilisateur)")
    args = ap.parse_args()
    global ALLOW_PAID
    ALLOW_PAID = args.use_kie_credits
    os.makedirs(args.out_dir, exist_ok=True)
    for path in args.episodes:
        with open(path, encoding="utf-8") as fh:
            render_episode(json.load(fh), args.out_dir, args.images_only)


if __name__ == "__main__":
    main()
