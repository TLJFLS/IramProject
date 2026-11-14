---
name: softness
description: Crée GRATUITEMENT une vidéo « satisfying » SOFTNESS 0 % → 100 % (9:16) en un seul script Blender : une capsule tombe sur 4 scies qui tournent au-dessus d'un socle troué ; dure elle reste bloquée, molle elle se faufile dans le trou. Utiliser quand l'utilisateur demande une vidéo softness, satisfying, "de 0 à 100 %", capsule / ballon contre des scies, pour TikTok, Reels ou Facebook.
---

# Softness 0 % → 100 % (satisfying)

Une commande, une vidéo. Tout est calculé (Blender + numpy), rien n'est payant.

```bash
python3 .claude/skills/softness/scripts/softness.py --game scies --color bleu --out videos/softness/scies_bleu.mp4
python3 .claude/skills/softness/scripts/softness.py --game tube --color rouge --out videos/softness/tube_rouge.mp4
```

Options :
- `--game` : `scies` (4 scies au-dessus d'un socle troué), `tube` (tube en verre plus étroit que la capsule :
  0 % reste bloquée dessus, plus c'est mou plus elle s'enfonce, 100 % traverse tout) ou `grille`
  (grille de barreaux avec petite ouverture carrée au centre, même comportement que les scies, sans rotation)
  ou `engrenages` (deux engrenages en marbre qui tournent en sens inverse : molle, la pâte est laminée entre
  les dents puis tombe dans le trou).
- `--objet` : `capsule` (défaut) ou `bille`.
- `--style` : `rose` (socle hexagonal rose, texte « SOFTNESS XX % ») ou `marbre` (marbre gris, bagues dorées,
  rayons de lumière, texte noir « XX% SOFT ») ; défaut `marbre` pour `engrenages`, `rose` sinon.
  **Alterner les jeux** d'une vidéo à l'autre pour varier le contenu.
- `--color` : `bleu` (défaut), `rouge`, `vert`, `jaune`, `rose`, `violet`, `orange`, `chrome`, `or` → varier.
- `--steps` : paliers en %, **toujours `0,20,50,75,100`** (exigence de l'utilisateur : jamais tous les 10 %). ~14 s de vidéo, ~30 min de rendu.
  Ne mettre d'autres paliers que si l'utilisateur le demande.
- `--seconds 2.8` (durée par essai), `--fps 24`, `--samples 8`, `--res 540x960` (agrandi en 1080x1920).
- `--test` : 3 images de contrôle (0 %, 50 %, 100 %) en ~1 min, à faire après toute modification.

Lancer le rendu complet en arrière-plan. Prérequis : `pip install bpy` (Blender 5.x), `ffmpeg`, Pillow, numpy.

## Son

Pensé comme les comptes « satisfying » : doux et propre, **aucun bruit de machine** (choix de l'utilisateur).
- Chocs : « tok » court de plastique creux quand c'est dur (à chaque rebond), « plop » rond quand c'est mou.
- Passage : son **gluant de slime** (petites bulles « gloup » dont le nombre suit la vitesse de passage + léger squish),
  puis un « gloup » grave quand la capsule tombe dans le trou.
- Écho discret, niveau modéré avec limiteur doux. Réglages : `tok()`, `bubble()`, `goo_sound()`, `soundtrack()`.
Pour changer le son d'une vidéo déjà rendue sans refaire la 3D :
`python3 .claude/skills/softness/scripts/softness.py --game <jeu> [--steps …] --remux videos/softness/x.mp4`

## Comportement (jeu `scies`)

- 0–20 % : la capsule rebondit sur les scies puis reste posée en vibrant.
- 30–50 % : elle s'écrase, une partie passe sous les scies et reste coincée (bulle de plus en plus grosse).
- 60–100 % : elle se faufile comme de la pâte entre les scies et tombe dans le trou, de plus en plus vite.

Jeu `tube` : 0 % rebondit et reste posée sur le tube ; 20 % entre à peine ; 50 % à mi-chemin ; 75 % presque en bas ;
100 % traverse entièrement et disparaît dans le socle.

- La déformation est calculée (pas de simulation physique) : résultat toujours identique et fiable.
  Réglages dans `state()` (temps, écrasement, vitesse de passage) et `deform()` (forme).

## Publication

Format vertical 9:16 compatible Reels Facebook / TikTok / Shorts. Description type :
« 0 % à 100 % de softness 😳 Laquelle est la plus satisfaisante ? #satisfying #blender #3d #asmr #softness »
