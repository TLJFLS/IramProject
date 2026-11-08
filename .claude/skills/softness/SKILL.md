---
name: softness
description: Crée GRATUITEMENT une vidéo « satisfying » SOFTNESS 0 % → 100 % (9:16) en un seul script Blender : une capsule tombe sur 4 scies qui tournent au-dessus d'un socle troué ; dure elle reste bloquée, molle elle se faufile dans le trou. Utiliser quand l'utilisateur demande une vidéo softness, satisfying, "de 0 à 100 %", capsule / ballon contre des scies, pour TikTok, Reels ou Facebook.
---

# Softness 0 % → 100 % (satisfying)

Une commande, une vidéo. Tout est calculé (Blender + numpy), rien n'est payant.

```bash
python3 .claude/skills/softness/scripts/softness.py --out videos/softness/softness_bleu.mp4
```

Options :
- `--color` : `bleu` (défaut), `rouge`, `vert`, `jaune`, `rose`, `violet`, `orange` → varier pour faire une série.
- `--steps` : paliers en %, défaut `0,10,…,100` (11 essais, ~31 s de vidéo, **~1 h de rendu**).
  `--steps 0,20,40,60,80,100` ≈ 17 s de vidéo, ~35 min de rendu.
- `--seconds 2.8` (durée par essai), `--fps 24`, `--samples 8`, `--res 540x960` (agrandi en 1080x1920).
- `--test` : 3 images de contrôle (0 %, 40 %, 100 %) en ~1 min, à faire après toute modification.

Lancer le rendu complet en arrière-plan. Prérequis : `pip install bpy` (Blender 5.x), `ffmpeg`, Pillow, numpy.

## Comportement

- 0–20 % : la capsule rebondit sur les scies puis reste posée en vibrant (grincement métallique).
- 30–50 % : elle s'écrase, une partie passe sous les scies et reste coincée (bulle de plus en plus grosse).
- 60–100 % : elle se faufile comme de la pâte entre les scies et tombe dans le trou, de plus en plus vite (plouf).
- La déformation est calculée (pas de simulation physique) : résultat toujours identique et fiable.
  Réglages dans `state()` (temps, écrasement, vitesse de passage) et `deform()` (forme).

## Publication

Format vertical 9:16 compatible Reels Facebook / TikTok / Shorts. Description type :
« 0 % à 100 % de softness 😳 Laquelle est la plus satisfaisante ? #satisfying #blender #3d #asmr #softness »
