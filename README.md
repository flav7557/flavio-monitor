# Flavio Monitor

Application Streamlit tout-en-un, thème clair minimaliste.

## Navigation

- **Data Online** (page d'accueil) — vue synthétique de la performance des indices
- **Bureau Larbou**
- **Kalman Lab**

## Data Online

Page d'accueil minimaliste (fond blanc, texte noir). Elle affiche la
performance des principaux indices sur **3 jours**, **1 semaine** et **1 mois**,
regroupés par zone :

- **Europe** : Euro Stoxx 50, CAC 40, DAX
- **US** : Nasdaq 100, S&P 500
- **Monde** : Nikkei 225, Hang Seng
- **Or & Pétrole** : Or (Gold), Brent

La performance est calculée sur les cours de clôture ajustés fournis par Yahoo
Finance (`yfinance`). Les horizons 3 jours / 1 semaine / 1 mois correspondent à
3 / 5 / 21 jours de bourse. Les données sont mises en cache 10 minutes ; le
bouton **Rafraîchir** force un rechargement.

> Données différées, à titre informatif uniquement.

## Installation locale

```powershell
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

## Secret LSE

Les pages Bureau Larbou et Kalman Lab utilisent le flux de données LSE. En
local, créer un fichier non versionné :

```text
.streamlit/secrets.toml
```

avec :

```toml
LSE_API_KEY = "TA_CLE"
```

Sur la plateforme, ajouter la même clé dans les secrets de l'application.
La page Data Online, elle, ne dépend que de Yahoo Finance et ne nécessite
aucun secret.

## Sécurité

Le WebSocket LSE est ouvert dans le navigateur. La clé peut donc être inspectée
par les utilisateurs ayant accès au site. Le déploiement doit rester privé ou
protégé par authentification.
