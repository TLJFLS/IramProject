#!/usr/bin/env python3
"""Routine quotidienne : 3 vidéos softness variées, programmées en Reels sur la page Squish lab.

Usage : python3 daily.py [--date 2026-11-20] [--dry-run]
- choisit 3 combinaisons (jeu, couleur, objet) jamais publiées récemment, avec 3 jeux différents si possible ;
- rend les vidéos (≈ 30 min chacune) ;
- les programme à 12 h, 17 h et 20 h (heure de Bruxelles) avec une description en anglais ;
- note tout dans videos/softness/posted.json.
"""
import argparse, datetime, itertools, json, os, random, subprocess, sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
LOG = os.path.join(ROOT, "videos", "softness", "posted.json")
GAMES = ["scies", "tube", "grille", "engrenages"]
COLORS = ["bleu", "rouge", "vert", "jaune", "rose", "violet", "orange", "chrome", "or"]
OBJECTS = ["capsule", "bille"]
SLOTS = [12, 17, 20]
TZ = ZoneInfo("Europe/Brussels")
NAMES = {"scies": "the saws", "tube": "the tube", "grille": "the grid", "engrenages": "the gears"}
HOOKS = ["0% vs 100% soft 😳 How far can it squish through {g}? 👇",
         "Which softness made it through {g}? 0, 20, 50, 75 or 100%? 👇",
         "Soft objects vs {g} 😌 Wait for 100%…",
         "Would you stop at 50% or go all the way to 100%? 🫧",
         "The most satisfying thing you'll see today 😮‍💨 0% → 100% soft",
         "Hard vs soft vs {g} — which one is your favorite? 👇"]
TAGS = "#satisfying #softbody #3d #asmr #oddlysatisfying #blender #squishlab"


def load():
    return json.load(open(LOG)) if os.path.exists(LOG) else []


def pick(day, log):
    recent = {(e["game"], e["color"], e["objet"]) for e in log[-60:]}
    rnd = random.Random(day.toordinal())
    combos = [c for c in itertools.product(GAMES, COLORS, OBJECTS) if c not in recent]
    rnd.shuffle(combos)
    chosen = []
    for c in combos:  # 3 jeux différents et 3 couleurs différentes dans la journée
        if all(c[0] != x[0] and c[1] != x[1] for x in chosen):
            chosen.append(c)
        if len(chosen) == 3:
            break
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    day = datetime.date.fromisoformat(a.date) if a.date else datetime.datetime.now(TZ).date()
    log = load()
    if any(e["date"] == day.isoformat() for e in log):
        print("déjà fait pour", day)
        return
    chosen = pick(day, log)
    rnd = random.Random(day.toordinal() * 7)
    hooks = rnd.sample(HOOKS, len(chosen))  # une accroche différente par vidéo
    sys.path.insert(0, HERE)
    for (game, color, objet), hour, hook in zip(chosen, SLOTS, hooks):
        at = datetime.datetime(day.year, day.month, day.day, hour, 0, tzinfo=TZ)
        desc = hook.format(g=NAMES[game]) + "\n\n" + TAGS
        out = os.path.join(ROOT, "videos", "softness", f"{day.isoformat()}_{game}_{color}_{objet}.mp4")
        print(f"{at:%d/%m %H:%M} → {game} / {color} / {objet}\n   {desc.splitlines()[0]}", flush=True)
        if a.dry_run:
            continue
        if at < datetime.datetime.now(TZ) + datetime.timedelta(minutes=15):
            at = None  # créneau déjà passé : publication immédiate
        subprocess.run([sys.executable, os.path.join(HERE, "softness.py"), "--game", game, "--color", color,
                        "--objet", objet, "--out", out], check=True)
        import fbpost
        vid = fbpost.post_reel(out, desc, at)
        log.append({"date": day.isoformat(), "slot": hour, "game": game, "color": color, "objet": objet,
                    "video_id": vid, "description": desc})
        json.dump(log, open(LOG, "w"), indent=1, ensure_ascii=False)
        print("   programmé, id", vid, flush=True)


if __name__ == "__main__":
    main()
