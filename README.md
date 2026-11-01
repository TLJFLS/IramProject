# IramProject — Workflows n8n

Environnement de développement [n8n](https://n8n.io) (n8n + Postgres via Docker), avec des workflows versionnés dans Git.

## Démarrage

```bash
cp .env.example .env          # puis édite .env (mots de passe, clé de chiffrement)
openssl rand -hex 32          # → valeur pour N8N_ENCRYPTION_KEY
docker compose up -d
```

Ouvre http://localhost:5678 et crée le compte administrateur.

## Importer les workflows du dépôt

```bash
./scripts/import-workflows.sh
```

## Sauvegarder tes workflows dans Git

Après avoir modifié des workflows dans l'éditeur :

```bash
./scripts/export-workflows.sh
git add workflows && git commit -m "Mise à jour des workflows"
```

> Les credentials (clés API, OAuth) ne sont **pas** exportés : ils restent chiffrés dans la base n8n.
> Ne committe jamais le fichier `.env`.

## Workflow d'exemple : formulaire de contact

`workflows/exemple-formulaire-contact.json` :
**Webhook (POST /contact) → IF email présent ? → Mise en forme → réponse JSON** (ou erreur 400).

Pour le tester sans le publier, ouvre-le dans n8n, clique sur **Execute workflow**, puis :

```bash
curl -X POST http://localhost:5678/webhook-test/contact \
  -H "Content-Type: application/json" \
  -d '{"nom":"Alice","email":"Alice@Example.com","message":"Bonjour"}'
```

Une fois publié (bouton **Publish**, n8n 2.x), l'URL devient `http://localhost:5678/webhook/contact`.

## Structure

```
docker-compose.yml   n8n + Postgres
.env.example         variables à copier dans .env
workflows/           workflows n8n (JSON) versionnés
scripts/             export / import des workflows
```

## Commandes utiles

| Action | Commande |
|---|---|
| Voir les logs | `docker compose logs -f n8n` |
| Arrêter | `docker compose down` |
| Mettre à jour n8n | `docker compose pull && docker compose up -d` |
