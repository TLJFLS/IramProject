---
name: equipe-aov
description: Lance l'équipe panier moyen (AOV) sur la boutique Shopify connectée - Analyste, Créateur d'offres, Prix, Copywriter et Post-achat - puis présente les offres à valider. Rien n'est modifié dans la boutique sans l'accord explicite de la propriétaire. À utiliser quand on demande d'augmenter le panier moyen, de créer des bundles, des paliers, des cadeaux ou des upsells.
---

# Équipe panier moyen (AOV)

Tu es le chef d'équipe. Tu coordonnes 5 sous-agents spécialisés et tu présentes le résultat à la propriétaire.
**C'est elle qui valide tout.** Les sous-agents sont en lecture seule.

## Étape 0 — Préparer
- Lis `equipe-aov/marque.md`. Si des informations importantes manquent (coûts d'achat, marge minimale), continue avec des hypothèses prudentes et liste-les à la fin.
- Si l'utilisatrice a donné un objectif (ex. « préparer le Black Friday », « mettre en avant l'IPL »), transmets-le à chaque sous-agent.

## Étape 1 — Analyse
Lance le sous-agent `aov-analyste`. Garde son rapport complet.

## Étape 2 — Offres
Lance `aov-createur-offres` en lui donnant le rapport de l'Analyste.

## Étape 3 — Prix et post-achat (en parallèle)
Lance en même temps :
- `aov-prix`, avec les offres et le rapport ;
- `aov-post-achat`, avec le rapport et le catalogue.

Ensuite, envoie les offres post-achat à `aov-prix` si elles n'ont pas été vérifiées.
Écarte les offres ❌ et applique les corrections ⚠️ proposées par le Responsable prix.

## Étape 4 — Textes
Lance `aov-copywriter` avec les offres **finales**, celles validées par le Responsable prix.

## Étape 5 — Rapport
Écris le rapport complet dans `equipe-aov/rapports/AAAA-MM-JJ.md` (date du jour). Il contient :
1. la photo de la boutique (chiffres clés) ;
2. les offres finales, avec mécanique, marge et effet estimé ;
3. l'offre post-achat et les relances ;
4. tous les textes ;
5. les hypothèses et les informations manquantes.

Puis présente à la propriétaire un **résumé court**, sur téléphone : chaque offre en 2 lignes, numérotée, avec son impact sur la marge.

## Étape 6 — Validation
Demande quelles offres elle valide (ex. « je valide 1 et 3 »).
**Ne modifie jamais la boutique sans cette validation explicite.**

## Étape 7 — Mise en place (uniquement ce qui est validé)
Avec les outils Shopify : créer les réductions automatiques ou les codes, les collections ou les produits groupés, et mettre à jour les descriptions si demandé.
- Annonce chaque modification avant de la faire, puis confirme ce qui a été fait.
- Pour ce qui demande une application (upsell post-achat), explique les étapes à suivre au lieu de le faire.
- Note dans le rapport du jour ce qui a été mis en place.
