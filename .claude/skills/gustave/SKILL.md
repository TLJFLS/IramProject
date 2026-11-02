---
name: gustave
description: Génère des vidéos TikTok éducatives avec Mr. Gustave (petit prof à lunettes, chemise bleue, cheveux gominés, dans une salle de classe) qui donne 3 faits fous sur un sujet. Une ou plusieurs vidéos d'un coup. Utiliser quand l'utilisateur demande une vidéo Mr. Gustave, une vidéo éducative / "faits fous", ou "N vidéos sur X, Y, Z".
---

# Mr. Gustave : vidéos éducatives en série

L'utilisateur donne un ou plusieurs sujets (« 5 vidéos : les requins, les pyramides, le cerveau… »).
Pour chaque sujet tu produis un MP4 prêt à poster + sa description. Pas de questions, sauf sujet incompréhensible.

## Étapes (pour chaque sujet)

1. **Rechercher** 3 faits surprenants et **vérifiés** (WebSearch si disponible ; sinon uniquement des faits
   très établis). Pas de mythe ni de chiffre douteux : arrondis honnêtement (« près de », « environ »).
   Varie les sujets d'une vidéo à l'autre.
2. **Écrire l'épisode** `videos/gustave/<slug>.json` (modèle : `examples/requins.json`).
3. **Générer** toutes les vidéos d'un coup :
   ```bash
   python3 .claude/skills/gustave/scripts/gustave.py videos/gustave/*.json --out-dir videos/gustave
   ```
   Chaque épisode donne `<slug>.mp4` et `<slug>.txt` (description).
4. **Vérifier** 3–4 images par vidéo (`ffmpeg -ss <t> -i x.mp4 -frames:v 1 f.png`) : texte du tableau
   lisible, rien de caché par la tête du prof. Corriger le JSON et relancer si besoin.
5. **Livrer** : envoyer les MP4, et coller chaque description dans la réponse, prête à copier.

## Règles d'écriture (TikTok)

- **Durée 15–22 s** : ~55–65 mots au total. Le script calcule le minutage tout seul (~3,7 mots/s).
- **Accroche** = 1re ligne de `intro.say`, le fait le plus choquant, dès la 1re seconde, avec 🤯.
  2e ligne : « C'est Mr. Gustave, 3 faits fous ! » (il se présente toujours).
- **Chaque fait** : 2 lignes de 5–8 mots ; la 1re commence par « Numéro N : ».
- **Tableau** : `title` ≤ 3 mots ; `key` = le chiffre ou la formule choc (≤ 25 caractères) ;
  `emoji` = une illustration ; `note` (optionnelle, ≤ 30 caractères, coin bas gauche).
- **Fin** : demande de like (« Like si t'en savais aucun ! 👍 »).
- **Musique** : `"music": false` par défaut → l'utilisateur ajoute un son tendance dans TikTok.
  Mettre `"happy"`, `"calm"` ou `"epic"` seulement si demandé.
- **Description** (`caption`) : accroche + les 3 faits en 1 ligne chacun avec emoji + question
  (« Lequel t'a le plus choqué ? 1, 2 ou 3 ? 👇 ») + « Abonne-toi pour un fait fou chaque jour avec
  Mr. Gustave 🤓 » + 8–10 hashtags (sujet + #science #lesaviezvous #apprendresurtiktok #culturegenerale #fyp #pourtoi).

## Ce qui est automatique (ne pas refaire à la main)

- Personnage, classe, plaque « M. GUSTAVE » sur le bureau, bras qui pointe le tableau à chaque fait.
- Sous-titres style CapCut : 3–4 mots, gros, contour noir, mot actif sur pastille jaune,
  placés à y ≈ 1290 (hors de la zone recouverte par l'interface TikTok).
- Titre du haut réduit automatiquement pour ne pas être rogné ; pas de fondu au début.

## Publication conseillée

5 vidéos/jour max, espacées de 2–3 h (ex. 12 h, 15 h, 18 h, 20 h, 22 h), sujets variés, même format.
