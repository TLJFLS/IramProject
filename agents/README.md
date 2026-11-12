# Naylia — Système multi-agents (n8n)

Un seul fichier à importer dans n8n : `naylia-multi-agents.json`.

## Architecture

```
CÔTÉ PROPRIÉTAIRE (Telegram)                      CÔTÉ CLIENTES (chat du site)

 Message Telegram ─┐                               Chat du site
 Nouvelle commande ├─► 🧠 ORCHESTRATEUR ─► Telegram      │
 Chaque matin 8h ──┘        │                            ▼
                            ├─ 🛒 Agent Commandes        💬 Agent Service client
                            ├─ 📦 Agent Stock et Rapports    ├─ 🔎 Agent Suivi de commande
                            └─ 📣 Agent Marketing            ├─ Catalogue produits
                                  └─ ✍️ Rédactrice fiches    └─ Alerter la propriétaire (Telegram)
```

- **Orchestrateur** : comprend la demande ou l'événement et l'envoie au bon spécialiste.
- **Agents spécialisés** : chacun a son rôle, ses instructions et uniquement ses outils. L'Agent Marketing a sa propre sous-agente.
- **Mémoire** : chaque agent a sa mémoire (10 derniers échanges), séparée par conversation.
- **Déclencheurs autonomes** : nouvelle commande Shopify, chaque matin à 8 h (heure de Bruxelles), message Telegram, message d'une cliente sur le site.
- **Modèle** : Claude Opus 5.5 (`claude-opus-5-5`), réflexion adaptive. Effort « medium » pour l'orchestrateur et ses agents, « low » pour le chat clientes (plus rapide).

### Sécurité
- Les clientes ne parlent **jamais** à l'orchestrateur : elles n'ont accès ni aux ventes ni aux autres commandes.
- Le suivi de commande exige le **numéro ET l'e-mail** (vérifié par Shopify, pas seulement par l'IA). Les caractères spéciaux sont filtrés pour empêcher les injections.
- Aucun agent ne peut modifier la boutique (prix, remboursements, annulations, codes promo) : ils proposent, tu décides.
- Le bot Telegram ne répond qu'à ton identifiant Telegram.

## Installation (une seule fois)

### 1. Ce qu'il te faut
| Quoi | Où |
|---|---|
| Compte n8n | n8n.io (n8n Cloud) |
| Clé API Anthropic | console.anthropic.com → API Keys (ajoute du crédit) |
| Bot Telegram | Dans Telegram, écris à **@BotFather** → `/newbot` → copie le token |
| Ton ID Telegram | Écris à **@userinfobot** → copie le nombre « Id » |
| Accès Shopify | Une app Shopify avec les accès `read_orders`, `read_products`, `read_customers` (+ `read_all_orders` pour les commandes de plus de 60 jours) : token d'accès Admin API + clé secrète de l'app |

### 2. Importer
Dans n8n : **Create workflow** → menu **⋯** → **Import from file** → `naylia-multi-agents.json`.

### 3. Créer les identifiants (Credentials)
- **Anthropic** : ta clé API. À choisir dans les nœuds « Claude réfléchi » et « Claude rapide ».
- **Shopify Access Token API** : Shop Subdomain = `ac3ttu-kg`, Access Token, APP Secret Key. À choisir dans tous les nœuds Shopify et dans « Chercher la commande ».
- **Telegram** : le token de @BotFather. À choisir dans les 3 nœuds Telegram.

Un nœud avec un triangle rouge = identifiant à choisir.

### 4. Mettre ton ID Telegram
Remplace `REMPLACE_PAR_TON_CHAT_ID_TELEGRAM` par ton ID dans ces 3 nœuds :
« Message Telegram » (champ User IDs), « Répondre sur Telegram » et « Alerter la propriétaire ».

### 5. Publier
Bouton **Publish** en haut à droite. Écris « bonjour » à ton bot Telegram pour tester.

### 6. Mettre le chat sur la boutique
Ouvre le nœud « Chat du site », copie l'URL du chat, puis ajoute avant `</body>` dans le thème Shopify (`theme.liquid`) :

```html
<link href="https://cdn.jsdelivr.net/npm/@n8n/chat/dist/style.css" rel="stylesheet" />
<script type="module">
  import { createChat } from 'https://cdn.jsdelivr.net/npm/@n8n/chat/dist/chat.bundle.es.js';
  createChat({
    webhookUrl: 'COLLE_ICI_L_URL_DU_CHAT',
    initialMessages: ['Bonjour 👋 Je suis l\'assistante Naylia. Une question sur un produit ou une commande ?'],
    i18n: { en: { title: 'Naylia', subtitle: 'Réponse immédiate, 7j/7', inputPlaceholder: 'Écrivez votre question…', getStarted: 'Nouvelle conversation', footer: '' } },
  });
</script>
```

## Exemples
- Telegram : « Combien de ventes cette semaine ? », « Quelles commandes ne sont pas expédiées ? », « Écris une description pour l'épilateur IPL », « Idées pour le Black Friday ».
- Automatique : notification à chaque commande + rapport chaque matin à 8 h.
- Site : « Où est ma commande 1052 ? », « L'épilateur marche-t-il sur peau mate ? »

## Bon à savoir
- **Coût** : chaque message consomme des tokens Claude (Opus 5.5 : 4 $ / 20 $ par million de tokens en entrée / sortie). Pour réduire le coût, remplace le modèle par `claude-haiku-5-5` dans « Claude rapide ».
- **Mémoire** : la mémoire simple s'efface si n8n redémarre. Pour une mémoire permanente, remplace les nœuds « Mémoire … » par « Postgres Chat Memory » (même clé de session).
- **Modifier les agents** : les instructions de chaque agent sont dans `generer_workflow.py`. Relance `python3 agents/generer_workflow.py` pour régénérer le fichier.

## Tests effectués
Testé sur n8n 2.35 avec un faux serveur Claude et un faux Shopify (aucun appel réel) :
- tous les paramètres de nœuds vérifiés contre les définitions officielles de n8n ;
- chat cliente → Agent Service client → sous-agent Suivi → recherche Shopify, aller-retour complet ;
- tentative d'injection dans l'e-mail neutralisée ; mémoire conservée entre messages ;
- modèle `claude-opus-5-5`, réflexion adaptive, effort transmis, aucune `temperature` envoyée.

Non testé en conditions réelles (nécessite tes identifiants) : Telegram, webhook Shopify, réponses du vrai Claude.
