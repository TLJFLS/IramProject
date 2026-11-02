# IramProject

## Skill `/video` : une vidéo en 1 prompt

Le skill Claude Code dans `.claude/skills/video/` transforme une seule phrase en vidéo MP4.

**Utilisation** (dans Claude Code, depuis ce dépôt) :

```
/video un TikTok de 20 s qui donne 3 astuces pour mieux dormir
```

ou simplement : « fais-moi une vidéo YouTube de présentation de mon appli de recettes ».

Claude écrit le scénario (`videos/<nom>.json`), lance le rendu et te donne le MP4.

**Prérequis** : `python3`, `pip install pillow`, `ffmpeg`.

**Rendu manuel** :

```bash
python3 .claude/skills/video/scripts/render.py .claude/skills/video/examples/demo.json
```
