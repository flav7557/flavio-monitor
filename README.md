# Flavio Monitor — version serveur

Application Streamlit tout-en-un :

- Workspace multi-graphiques LSE / Yahoo
- Bureau Larbou
- Kalman Lab
- Lissage et prévision sur ticks
- Bêta dynamique
- Relative value
- Kalman + HMM avec régimes bruit, hausse, baisse et choc

## Point d'entrée

```text
main.py
```

## Installation locale

```powershell
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

## Secret LSE

Le code recherche la clé dans :

```toml
LSE_API_KEY = "..."
```

### En local

Créer un fichier non versionné :

```text
.streamlit/secrets.toml
```

en copiant le modèle :

```text
.streamlit/secrets.toml.example
```

### Sur Streamlit Community Cloud

Dans les paramètres avancés / Secrets de l'application, ajouter :

```toml
LSE_API_KEY = "TA_CLE_REELLE"
```

Ne jamais committer la vraie clé.

## Déploiement Streamlit Community Cloud

- Dépôt GitHub : racine de ce dossier
- Fichier principal : `main.py`
- Version Python recommandée : 3.11
- Ajouter le secret `LSE_API_KEY`
- Déployer puis consulter les logs de build

## Déploiement Docker

```bash
docker build -t flavio-monitor .
docker run --rm -p 8501:8501 -e LSE_API_KEY="TA_CLE" flavio-monitor
```

## Sécurité importante

Les graphiques LSE utilisent un WebSocket ouvert depuis le navigateur.
La clé LSE est donc transmise au client pour cette architecture et peut être
retrouvée par un utilisateur ayant accès à l'application.

Il faut donc :

- déployer l'application en privé ou derrière une authentification ;
- ne pas publier une clé LSE de production dans une application publique ;
- régénérer toute clé déjà publiée ;
- pour un déploiement public, créer un proxy backend authentifié.

## Vérifications après déploiement

1. Workspace, Bureau Larbou et Kalman Lab sont accessibles.
2. Le catalogue LSE se charge.
3. Les bougies Yahoo s'affichent.
4. Le Kalman reçoit des ticks.
5. Kalman + HMM affiche les probabilités de régimes.
6. Aucun secret n'apparaît dans GitHub ni dans les logs.
