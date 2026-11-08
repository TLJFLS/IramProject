---
name: fruitdrama
description: Crée des vidéos TikTok « fruit drama » avec images IA réalistes style Pixar (humains à tête de fruit dans des décors comme prison, décharge, mine, restaurant de luxe), histoires à rebondissement choisies par Claude, narrateur + voix par personnage, sous-titres. Utiliser quand l'utilisateur demande des vidéos fruit drama, des histoires de fruits IA, ou "N vidéos du genre fruit drama".
---

# Fruit drama (images IA)

L'utilisateur demande N vidéos. **Tu choisis les sujets** (sauf s'il en donne), tu écris les histoires,
tu génères les images, tu montes, tu livres MP4 + descriptions. Pas de questions.

## Coût : vérifier d'abord

Les images viennent de kie.ai (`KIE_API_KEY`, ~4 crédits par image, 3–4 images par vidéo).
Avant de générer : `curl -sS -H "Authorization: Bearer $KIE_API_KEY" https://api.kie.ai/api/v1/chat/credit`.
Si les crédits ne suffisent pas pour tout, fais moins de vidéos ou moins d'images, et dis-le.
Hôtes réseau nécessaires : `api.kie.ai`, `tempfile.aiquickdraw.com`, `speech.platform.bing.com`.

## Étapes

1. **Écrire** `videos/fruitdrama/<slug>.json` (modèles dans `videos/fruitdrama/*.json`).
2. **Images** (payant, en cache : jamais régénérées) :
   `python3 .claude/skills/fruitdrama/scripts/fruitdrama.py videos/fruitdrama/<slug>.json --images-only`
   puis **regarder** les images (planche contact) avant de continuer.
3. **Montage** (gratuit) : même commande sans `--images-only`.
4. **Vérifier** 3–4 images des MP4, **livrer** MP4 + descriptions.

## Recette des histoires (ce qui perce)

- 3–4 scènes, 10–20 s. Scène 1 = la situation injuste, tout de suite (narrateur).
- Thèmes qui marchent : prison (le caïd puni), pauvre → riche (décharge, ticket gagnant), patron
  exploiteur puni (mine, usine), jugé sur ses habits (restaurant, boutique de luxe), harcelé → patron
  (« 10 ans plus tard »), trahison amoureuse, belle-mère méchante, mariage gâché, hôpital, avion.
- Karma : le méchant est puni ou humilié à la dernière scène, phrase finale qui claque.
- `title` court en majuscules + emoji ; description = accroche + question qui divise + « Partie 2 ? » + hashtags.

## Format de l'épisode

- `cast` : `{id: {"voice", "pitch", "color", "label", "emoji"}}` (voix edge-tts fr-FR / fr-CA / fr-BE / fr-CH).
  `narrateur` est toujours disponible dans `lines` (voix grave, sans étiquette).
- `scenes` : `{"image": description EN ANGLAIS de la scène, "lines": [{"who", "say"}], "motion"?}`.
  Décris chaque personnage par sa tête de fruit + ses vêtements, de la même façon dans chaque scène.
  La 1re image fixe les personnages ; les suivantes sont générées à partir d'elle.
  Évite les chiffres écrits dans l'image qui pourraient contredire le texte dit.
- `motion` : `zoom_in`, `zoom_out`, `pan_right`, `pan_left` (alterné par défaut). Musique `"epic"` par défaut.

## Publication TikTok

Pas encore automatique : l'API TikTok (gratuite) exige une app validée par TikTok ; avant validation les
publications sont privées. En attendant, envoyer les MP4 + descriptions à l'utilisateur.
