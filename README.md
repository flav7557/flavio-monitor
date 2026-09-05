# Flavio Monitor

Application Streamlit tout-en-un, thème clair minimaliste.

## Navigation

- **Data Online** (page d'accueil) — vue synthétique de la performance des indices
- **Regime Matrix** — matrice de régime de marché (commodités) pilotée par le feed LSE

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

## Regime Matrix

Matrice de régime de marché de qualité institutionnelle. Elle évalue en continu
si chaque groupe d'actifs est *Strong Bearish → Strong Bullish* à partir de
règles systématiques sur les prix, de façon entièrement traçable
(instrument → cluster → secteur → complexe global).

Architecture (package `regime/`, moteur découplé de l'UI et testé) :

```
regime/
  config.py              # tous les paramètres (poids, seuils, taxonomie, clusters)
  data/                  # acquisition des données (isolée du moteur)
    provider.py          # interface + normalisation des chandeliers
    lse_provider.py      # London Strategic Edge (primaire, catalog + candles)
    yf_provider.py       # Yahoo Finance (repli / dev)
  engine/                # moteur déterministe et testable
    indicators.py normalization.py instrument_scorer.py
    classification.py breadth.py aggregation.py
    confidence.py persistence.py explain.py pipeline.py models.py
  ui/dashboard.py        # rendu Streamlit uniquement
  service.py             # sélection du provider + exécution du pipeline
tests/test_engine.py     # 19 tests (scoring, breadth, invariants, persistance)
```

Score par instrument (−100 baissier … +100 haussier) :
`0.35·Trend + 0.30·Momentum + 0.20·Intraday + 0.15·Breakout`
(les composantes indisponibles sont retirées et les poids renormalisés — une
donnée manquante n'est jamais un signal). Momentum en Z-score de volatilité, pas
en % bruts comparés entre matières premières. La *breadth* compte les clusters
(pas les instruments corrélés), et l'agrégation secteur/cluster utilise un centre
robuste (médiane à partir de 4 enfants) pour qu'un seul outlier ne fasse pas
basculer un groupe. Persistance + hystérésis évitent le clignotement du régime.

Source de données : **London Strategic Edge** via `LSE_API_KEY` (voir plus bas).
Pilotage Live et Regime Matrix utilisent uniquement LSE.

Tests :

```powershell
python -m pytest tests/test_engine.py -q
```

## Installation locale

```powershell
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

## Secret LSE

Pilotage Live et Regime Matrix utilisent le flux de données LSE. En local,
créer un fichier non versionné :

```text
.streamlit/secrets.toml
```

avec :

```toml
LSE_API_KEY = "TA_CLE"
```

Sur la plateforme, ajouter la même clé dans les secrets de l'application.

## Sécurité

La clé LSE est lue côté serveur depuis `LSE_API_KEY` ou `st.secrets`.
Le navigateur reçoit seulement les prix et les bougies nécessaires aux
graphiques, jamais la clé API.
