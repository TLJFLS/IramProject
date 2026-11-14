# Équipe panier moyen (AOV)

Une équipe de 5 agents IA qui tourne **dans Claude**, avec l'abonnement Claude existant : pas de n8n, pas de crédits API.

```
/equipe-aov
├── Analyste          → trouve ce que les clients achètent ensemble
├── Créateur d'offres → bundles, paliers, gift ladders
├── Prix              → des remises qui ne tuent pas la marge
├── Copywriter        → écrit chaque offre avec le ton de la marque
└── Post-achat        → upsell en 1 clic après le paiement + relances
```

**C'est la propriétaire qui valide tout.** Les agents ne font que lire la boutique. Seules les offres validées sont mises en place.

## Utilisation
Dans une session Claude Code ouverte sur ce dépôt, avec le connecteur Shopify :
- `/equipe-aov` : mission complète ;
- `/equipe-aov préparer le Black Friday` : mission avec un objectif.

## Fichiers
- `equipe-aov/marque.md` : ton de la marque, coûts et marges. **À compléter** pour des calculs exacts.
- `equipe-aov/rapports/` : un rapport par mission.
- `.claude/agents/aov-*.md` : les instructions de chaque agent.
- `.claude/skills/equipe-aov/SKILL.md` : le chef d'équipe, qui enchaîne les agents.
