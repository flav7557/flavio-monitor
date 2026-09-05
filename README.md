# Flavio Market Terminal

Terminal personnel de visualisation de six marchés. Les données historiques et
live proviennent exclusivement de London Strategic Edge.

```text
London Strategic Edge -> FastAPI -> Next.js
```

La clé API est utilisée uniquement par FastAPI. Elle n'est jamais envoyée au
navigateur.

## Structure

```text
backend/
  main.py                 API HTTP et WebSocket
  config.py               configuration serveur
  lse_client.py           client officiel lse-data
  market_catalog.py       résolution contrôlée des symboles
  market_service.py       historique et flux LSE partagé
  websocket_manager.py    diffusion aux navigateurs
config/
  markets.json            six marchés et symboles modifiables
frontend/
  app/                    application Next.js
  components/             terminal, grille, graphiques, sélecteur
  hooks/                  connexion WebSocket unique
  lib/                    API et agrégation OHLC
scripts/
  find_symbols.py         recherche dans le catalogue LSE
```

## Configuration

Créer `.env` à partir de `.env.example`, puis renseigner :

```dotenv
LSE_API_KEY=your_key_here
```

`.env` est ignoré par Git. Ne jamais placer la clé dans `frontend/`, dans une
variable `NEXT_PUBLIC_*` ou dans le dépôt.

## Vérifier les symboles LSE

Le terminal interroge `client.catalog()` au démarrage et résout les instruments
sans ticker supposé. Pour inspecter les meilleurs résultats avant de fixer un
symbole dans `config/markets.json` :

```powershell
python scripts/find_symbols.py
```

Si `ASX 5` n'existe pas exactement dans le catalogue, il reste indisponible. Il
n'est jamais remplacé silencieusement par un autre indice.

## Lancer le backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Le serveur est disponible sur `http://127.0.0.1:8000`.

## Lancer le frontend

Dans un second terminal :

```powershell
cd frontend
pnpm install
pnpm dev
```

Le terminal est disponible sur `http://localhost:3000`.
Les adresses locales du backend sont déjà les valeurs par défaut. Pour les
changer, créer `frontend/.env.local` à partir de `frontend/.env.example`.

## API

- `GET /api/health`
- `GET /api/markets`
- `GET /api/candles/{symbol}?timeframe=5m&limit=300`
- `WebSocket /ws/markets`

Périodes disponibles : `1m`, `5m`, `15m`, `1h`, `4h`, `1d`.

Le backend maintient une seule connexion WebSocket LSE pour tous les marchés,
puis diffuse les ticks à tous les navigateurs. Le frontend agrège chaque tick
dans la bougie courante et utilise `series.update()` sans recréer le graphique.

## Docker

```powershell
docker compose up --build
```
