---
name: fruits
description: Crée des vidéos TikTok de fruits qui parlent en 3D (Blender), format feuilleton / drama (disputes, trahisons, rebondissements), avec une voix différente par fruit et des sous-titres. Utiliser quand l'utilisateur demande des fruits qui parlent, un fruit drama, un épisode de feuilleton de fruits, ou "N vidéos de fruits".
---

# Fruits qui parlent (3D) : feuilleton TikTok

L'utilisateur donne une idée (« la pomme découvre que l'orange lui a volé son mec ») ou juste « 3 épisodes ».
Tu écris le scénario et tu produis le MP4 + la description. Pas de questions.

## Étapes

1. **Écrire l'épisode** `videos/fruits/<slug>.json` (modèle : `examples/trahison.json`).
2. **Générer** (≈ 5 min par épisode, le rendu 3D est le plus long) :
   ```bash
   python3 .claude/skills/fruits/scripts/fruits.py videos/fruits/<slug>.json --out-dir videos/fruits
   ```
   Lance-le en arrière-plan s'il y a plusieurs épisodes.
3. **Vérifier** 5–6 images (`ffmpeg -ss <t> -i x.mp4 -frames:v 1 f.png`) : visages visibles, sous-titres lisibles.
4. **Livrer** : envoyer les MP4 et coller la description de chaque épisode.

## Écriture (ce qui perce sur TikTok)

- **20–30 s**, 6–9 répliques courtes (5–12 mots). La 1re réplique = le conflit, tout de suite.
- **Rebondissement** au milieu (aveu, révélation), **cliffhanger** à la fin (« C'est fini entre nous », « …et toi alors ? »).
- Humour : jeux de mots fruits / cuisine (frigo, mixeur, compote, éplucher, pourri…).
- Format série : `title` = « NOM DE LA SÉRIE 💔 épisode N », mêmes personnages d'un épisode à l'autre.
- Pas de guillemets « » dans `say` (ils s'affichent seuls dans les sous-titres).
- Description : accroche + question qui divise (« Team Fraise ou Team Kiwi ? ») + « La suite demain ? » + hashtags
  (#fruits #drama #fruitdrama #humour #fyp #pourtoi + noms des fruits).

## Format de l'épisode

- `cast` : 2–3 personnages `{"name", "fruit", "label"}` ; options `voice`, `pitch`, `color`, `emoji`.
  Fruits disponibles : `fraise`, `banane`, `kiwi`, `orange`, `pomme`, `citron` (voix et couleur par défaut pour chacun).
- `lines` : `{"who", "say", "emotion", "shot", "pause"}`.
  - `emotion` : `neutre`, `joie`, `colere`, `triste`, `choc`, `malin`.
  - `shot` : `close` (défaut, gros plan), `zoom` (très gros plan, automatique pour `choc`), `wide` (tout le monde).
  - Chaque combinaison personnage + émotion + plan = un rendu 3D (~40 s) : réutilise-les pour aller plus vite.

## Technique

- Blender en module Python (`pip install bpy`, Blender 5.x), rendu Cycles sur le processeur en 720×1280,
  agrandi en 1080×1920. Voix : edge-tts (voir le skill gustave), une voix par fruit.
- Pour chaque plan : une image 3D complète + seulement la zone du visage pour 3 ouvertures de bouche
  et un clignement ; la bouche suit le volume de la voix, petit zoom caméra, « coup de zoom » sur les chocs.
- Les rendus sont mis en cache dans `<out-dir>/.cache/<slug>/` : relancer après une petite correction de texte est rapide
  (supprimer le cache si on change les personnages ou la caméra).
