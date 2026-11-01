#!/usr/bin/env python3
"""Render an MP4 video from a JSON storyboard (Pillow frames piped into ffmpeg).

Usage: python3 render.py storyboard.json [-o out.mp4]
"""
import argparse, json, math, os, random, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}
FONT_DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
             "/System/Library/Fonts", "/Library/Fonts", "C:/Windows/Fonts"]
FONT_NAMES = {
    "bold": ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"],
    "regular": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf", "arial.ttf"],
}
_font_cache = {}


def find_font(kind):
    for d in FONT_DIRS:
        for root, _, files in os.walk(d):
            for name in FONT_NAMES[kind]:
                if name in files:
                    return os.path.join(root, name)
    return None


def font(kind, size):
    key = (kind, size)
    if key not in _font_cache:
        path = find_font(kind)
        _font_cache[key] = ImageFont.truetype(path, size) if path else ImageFont.load_default(size)
    return _font_cache[key]


def hex_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def ease(t):  # ease-out cubic, clamped
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            test = f"{line} {word}".strip()
            if draw.textlength(test, font=fnt) <= max_w or not line:
                line = test
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def background(scene, size, t, base_dir):
    w, h = size
    bg = scene.get("background", ["#1e3c72", "#2a5298"])
    if isinstance(bg, str) and not bg.startswith("#"):  # image path -> Ken Burns zoom
        path = bg if os.path.isabs(bg) else os.path.join(base_dir, bg)
        img = scene.setdefault("_img", Image.open(path).convert("RGB"))
        z = 1.0 + 0.12 * t
        scale = max(w / img.width, h / img.height) * z
        im = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
        x, y = (im.width - w) // 2, (im.height - h) // 2
        im = im.crop((x, y, x + w, y + h))
        return Image.blend(im, Image.new("RGB", size, (0, 0, 0)), 0.35)  # darken for legibility
    colors = [hex_rgb(bg)] * 2 if isinstance(bg, str) else [hex_rgb(c) for c in bg]
    # animated diagonal gradient (rendered small, upscaled = fast)
    sw, sh = 64, max(2, int(64 * h / w))
    small = Image.new("RGB", (sw, sh))
    px = small.load()
    shift = 0.25 * math.sin(t * math.pi)
    n = len(colors) - 1
    for y in range(sh):
        for x in range(sw):
            p = max(0.0, min(1.0, (x / sw * 0.5 + y / sh * 0.5) + shift))
            i = min(int(p * n), n - 1)
            f = p * n - i
            a, b = colors[i], colors[i + 1]
            px[x, y] = tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))
    return small.resize(size, Image.BILINEAR)


def particles(img, scene_idx, t, accent):
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rnd = random.Random(scene_idx * 7919)
    for _ in range(28):
        x = rnd.random() * w
        y = (rnd.random() * h - t * h * rnd.uniform(0.05, 0.2)) % h
        r = rnd.uniform(2, 9) * w / 1920
        d.ellipse((x - r, y - r, x + r, y + r), fill=accent + (rnd.randint(40, 110),))
    img.paste(layer, (0, 0), layer)


def render_scene_frame(scene, idx, size, t_sec, dur, style, base_dir):
    w, h = size
    t = t_sec / dur
    img = background(scene, size, t, base_dir).convert("RGBA")
    accent = hex_rgb(scene.get("accent", style.get("accent", "#ffd166")))
    if style.get("particles", True):
        particles(img, idx, t, accent)
    over = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    color = hex_rgb(scene.get("color", style.get("color", "#ffffff")))
    unit = min(w, h)
    max_w = int(w * 0.84)
    anim = scene.get("animation", "rise")

    blocks = []  # (lines, font, color, delay)
    if scene.get("emoji_text"):  # large symbol/number on top (plain glyphs only)
        blocks.append((wrap(d, scene["emoji_text"], font("bold", int(unit * 0.16)), max_w),
                       font("bold", int(unit * 0.16)), accent, 0.0))
    if scene.get("title"):
        f = font("bold", int(unit * scene.get("title_scale", 0.085)))
        blocks.append((wrap(d, scene["title"], f, max_w), f, color, 0.1))
    if scene.get("text"):
        f = font("regular", int(unit * 0.055))
        blocks.append((wrap(d, scene["text"], f, max_w), f, color, 0.35))

    gap = int(unit * 0.03)
    heights = [len(L) * int(f.size * 1.25) for L, f, _, _ in blocks]
    total = sum(heights) + gap * max(0, len(blocks) - 1)
    y = (h - total) // 2
    for (lines, f, col, delay), bh in zip(blocks, heights):
        p = ease((t_sec - delay) / 0.6)
        if anim == "typewriter" and f.size < unit * 0.06:
            n_chars = int(sum(len(l) for l in lines) * min(1, max(0, (t_sec - delay) / (dur * 0.6))))
            p = 1.0 if t_sec > delay else 0.0
        alpha = int(255 * p)
        dy = int((1 - p) * unit * 0.05) if anim in ("rise", "typewriter") else 0
        sc = 0.85 + 0.15 * p if anim == "zoom" else 1.0
        dx = int((1 - p) * w * 0.15) if anim == "slide" else 0
        ly = y
        shown = 0
        for line in lines:
            txt = line
            if anim == "typewriter" and f.size < unit * 0.06:
                txt = line[:max(0, n_chars - shown)]
                shown += len(line)
            if sc != 1.0:
                f2 = font("bold" if f.size > unit * 0.06 else "regular", max(8, int(f.size * sc)))
            else:
                f2 = f
            lw = d.textlength(txt, font=f2)
            x = (w - lw) / 2 + dx
            d.text((x + 3, ly + dy + 4), txt, font=f2, fill=(0, 0, 0, alpha // 3))  # soft shadow
            d.text((x, ly + dy), txt, font=f2, fill=col + (alpha,))
            ly += int(f.size * 1.25)
        y += bh + gap
    img = Image.alpha_composite(img, over)

    if style.get("progress_bar", True):  # thin progress line at bottom
        bar = ImageDraw.Draw(img)
        bar.rectangle((0, h - int(unit * 0.008), int(w * style["_global_t"]), h), fill=accent + (255,))

    fade = min(0.35, dur / 4)  # fade in/out each scene
    k = min(1.0, t_sec / fade, (dur - t_sec) / fade)
    if k < 1.0:
        img = Image.blend(Image.new("RGBA", size, (0, 0, 0, 255)), img, max(0.0, k))
    return img.convert("RGB")


def music_track(path, total, mood):
    chords = {
        "calm": [(220.0, 277.18, 329.63), (196.0, 246.94, 293.66), (174.61, 220.0, 261.63), (196.0, 246.94, 329.63)],
        "epic": [(110.0, 164.81, 220.0), (98.0, 146.83, 196.0), (87.31, 130.81, 174.61), (98.0, 146.83, 196.0)],
        "happy": [(261.63, 329.63, 392.0), (293.66, 369.99, 440.0), (349.23, 440.0, 523.25), (392.0, 493.88, 587.33)],
    }[mood if mood in ("calm", "epic", "happy") else "calm"]
    seg = 2.0
    terms = []
    for i, ch in enumerate(chords):
        cond = f"between(mod(t,{seg * len(chords)}),{i * seg},{(i + 1) * seg})"
        tones = "+".join(f"sin(2*PI*{f}*t)" for f in ch)
        terms.append(f"{cond}*({tones})")
    expr = f"0.08*({'+'.join(terms)})*(0.6+0.4*sin(2*PI*0.5*t))"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"aevalsrc='{expr}':s=44100:d={total}",
                    "-af", f"lowpass=f=1800,afade=t=in:d=1,afade=t=out:st={max(0, total - 1.5)}:d=1.5",
                    path], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg introuvable : installe-le (apt install ffmpeg / brew install ffmpeg).")
    with open(args.storyboard, encoding="utf-8") as fh:
        sb = json.load(fh)
    base_dir = os.path.dirname(os.path.abspath(args.storyboard))
    size = FORMATS.get(sb.get("format", "16:9"), FORMATS["16:9"])
    if sb.get("preview"):
        size = (size[0] // 2, size[1] // 2)
    fps = int(sb.get("fps", 30))
    style = sb.get("style", {})
    scenes = sb["scenes"]
    total = sum(float(s.get("duration", 3)) for s in scenes)
    out = args.output or sb.get("output", "video.mp4")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    tmp = tempfile.mkdtemp()
    silent = os.path.join(tmp, "v.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", silent],
                           stdin=subprocess.PIPE)
    elapsed = 0.0
    for i, sc in enumerate(scenes):
        dur = float(sc.get("duration", 3))
        n = int(round(dur * fps))
        for f in range(n):
            ts = f / fps
            style["_global_t"] = (elapsed + ts) / total
            enc.stdin.write(render_scene_frame(sc, i, size, ts, dur, style, base_dir).tobytes())
        elapsed += dur
        print(f"  scène {i + 1}/{len(scenes)} ok", flush=True)
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("échec de l'encodage ffmpeg")

    music = sb.get("music", "calm")
    if music:
        audio = os.path.join(tmp, "a.wav")
        if isinstance(music, str) and os.path.exists(os.path.join(base_dir, music)):
            src = os.path.join(base_dir, music)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-t", str(total),
                            "-af", f"afade=t=out:st={max(0, total - 1.5)}:d=1.5", audio], check=True)
        else:
            music_track(audio, total, music)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", audio, "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "160k", "-shortest", out], check=True)
    else:
        shutil.move(silent, out)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Vidéo prête : {os.path.abspath(out)} ({total:.1f}s, {size[0]}x{size[1]})")


if __name__ == "__main__":
    main()
