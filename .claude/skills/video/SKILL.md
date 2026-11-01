---
name: video
description: Crée une vidéo MP4 complète (scènes animées, texte, dégradés ou images, musique) à partir d'une seule demande en langage naturel. Utiliser quand l'utilisateur demande une vidéo, un short, un reel, un TikTok, une story, une vidéo promo, explicative ou de présentation, même en une phrase.
---

# Skill vidéo en 1 prompt

L'utilisateur décrit la vidéo en une phrase. Tu fais TOUT le reste sans poser de questions,
sauf si la demande est vraiment incompréhensible.

## Étapes

1. **Choisir les réglages** à partir de la demande (valeurs par défaut entre parenthèses) :
   - `format` : `9:16` pour TikTok/Reels/Shorts/story, `16:9` pour YouTube/présentation, `1:1` ou `4:5` pour un post. (`9:16`)
   - durée totale : (≈ 15–30 s, 5 à 8 scènes de 2,5 à 5 s)
   - `music` : `calm`, `happy`, `epic`, un chemin vers un fichier audio, ou `false`. (choisis selon le ton)
   - langue : celle de l'utilisateur.

2. **Écrire le scénario** dans `videos/<slug>.json` :
   - scène 1 = accroche forte (titre court, `animation: "zoom"`)
   - scènes du milieu = un message par scène (titre ≤ 5 mots, `text` ≤ 15 mots)
   - dernière scène = conclusion / appel à l'action
   - varie les `animation` et les couleurs de fond ; garde une palette cohérente.

3. **Générer** :
   ```bash
   python3 .claude/skills/video/scripts/render.py videos/<slug>.json
   ```
   (Pour un essai rapide, ajoute `"preview": true` au JSON : demi-résolution.)

4. **Vérifier** : extrais 3–4 images (`ffmpeg -ss <t> -i out.mp4 -frames:v 1 f.png`) et regarde-les.
   Corrige le JSON si du texte déborde ou est illisible, puis relance.

5. **Livrer** : donne le chemin du MP4 (et envoie le fichier si l'outil le permet), résume la vidéo en 2 lignes.

## Format du scénario

```json
{
  "format": "9:16",
  "fps": 30,
  "music": "happy",
  "output": "videos/mon-short.mp4",
  "style": { "accent": "#ffd166", "color": "#ffffff", "particles": true, "progress_bar": true },
  "scenes": [
    {
      "title": "Titre en gros",
      "text": "Phrase secondaire plus petite",
      "emoji_text": "1",
      "background": ["#141e30", "#243b55"],
      "duration": 3.5,
      "animation": "rise"
    }
  ]
}
```

Champs d'une scène (tous optionnels sauf au moins un texte) :

| Champ | Rôle |
|---|---|
| `title` | gros texte en gras |
| `text` | texte secondaire |
| `emoji_text` | très grand chiffre/symbole au-dessus, couleur d'accent (pas d'emoji couleur : police sans emoji) |
| `background` | `"#hex"`, liste de 2+ couleurs (dégradé animé) ou chemin d'image (zoom Ken Burns, relatif au JSON) |
| `duration` | secondes (défaut 3) |
| `animation` | `rise` (défaut), `zoom`, `slide`, `fade`, `typewriter` |
| `accent`, `color`, `title_scale` | surcharges par scène |

## Règles

- N'utilise pas d'emoji : la police n'en a pas, ils s'affichent en carrés.
- Prévois ~1 s de lecture par 3 mots dans `duration`.
- Nécessite `python3`, `Pillow` (`pip install pillow`) et `ffmpeg`.
- Un exemple complet est dans `examples/demo.json`.
