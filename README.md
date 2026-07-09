# Flavio Monitor

Flavio Monitor est une application Streamlit de monitoring de marches financiers. Elle combine un flux live London Strategic Edge avec un contexte historique Yahoo Finance.

## Marches suivis

- CAC 40
- DAX
- Euro Stoxx 50
- Nasdaq 100
- S&P 500
- Gold
- Brent

## Donnees

- Le live utilise le WebSocket LSE.
- La vue historique utilise Yahoo Finance via `yfinance`.
- La cle LSE peut etre saisie manuellement dans la sidebar.
- En local ou sur Streamlit, la cle peut aussi venir de `LSE_API_KEY`.

Pour une application publique, il est plus prudent de saisir la cle dans la sidebar. Une cle injectee automatiquement dans une app publique peut etre visible dans les outils developpeur du navigateur.

## Lancement local

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

## Cle LSE en local

Option recommandee pour tester rapidement : saisir la cle LSE dans la sidebar au lancement de l'application.

Option avec variable d'environnement :

```bash
LSE_API_KEY="ma_cle_lse"
```

Option avec secrets Streamlit locaux : creer un fichier `.streamlit/secrets.toml` non versionne avec :

```toml
LSE_API_KEY = "ma_cle_lse"
```

## Deploiement Streamlit Community Cloud

1. Ouvrir https://share.streamlit.io
2. Cliquer sur **Create app**.
3. Selectionner le depot GitHub `flavio-monitor`.
4. Selectionner la branche `main`.
5. Indiquer `streamlit_app.py` comme fichier principal.
6. Choisir Python 3.12 dans les parametres avances.
7. Cliquer sur **Deploy**.

Si l'application doit rester privee, ajouter eventuellement la cle dans les secrets Streamlit :

```toml
LSE_API_KEY = "ma_cle_lse"
```

Ne jamais mettre une vraie cle LSE dans GitHub.
