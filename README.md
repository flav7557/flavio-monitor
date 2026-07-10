# Flavio Monitor V2 — Shadow Trader

Application Streamlit tout-en-un.

## Navigation

- Workspace
- Bureau Larbou
- Kalman Lab
- Shadow Trader

## Shadow Trader

Le module exécute uniquement des ordres simulés. Il ne se connecte à aucun
broker et n'envoie aucun ordre réel.

### Stratégies

1. **Kalman Trend**
   - suit la pente latente du filtre ;
   - entre après plusieurs confirmations ;
   - sort quand la pente disparaît ou quand l'innovation devient un choc.

2. **Kalman + HMM Directional**
   - long lorsque le régime haussier est suffisamment probable ;
   - short lorsque le régime baissier est suffisamment probable ;
   - flat en bruit/range ou choc.

3. **Dynamic Beta Residual Momentum**
   - position à deux jambes Y/X ;
   - hedge ratio fondé sur le bêta Kalman ;
   - cherche la continuation d'un résiduel anormal.

4. **Relative Value Mean Reversion**
   - position à deux jambes Y/X ;
   - hedge ratio dynamique ;
   - cherche le retour à la moyenne d'un spread extrême.

### Simulation d'exécution

Le moteur utilise :

- l'ask pour acheter et le bid pour vendre, lorsqu'ils existent ;
- sinon le dernier prix ;
- un slippage supplémentaire configurable ;
- une commission par unité et par côté ;
- une valeur du point et un tick size configurables ;
- un facteur de conversion FX vers la devise du compte ;
- un levier brut cible ;
- un sizing automatique ;
- deux jambes pour les modèles pair.

### Suivi de session

- BUY / SHORT / HOLD / EXIT ;
- position et quantités ;
- P&L réalisé ;
- P&L latent à la liquidation ;
- P&L net ;
- basis points sur le capital ;
- ticks équivalents de la jambe Y ;
- coûts ;
- win rate ;
- profit factor ;
- max drawdown ;
- stop par trade ;
- kill switch de session ;
- limite de durée ;
- limite de nombre de trades ;
- cooldown après sortie ;
- trade blotter ;
- decision log ;
- exports CSV.

## Installation locale

```powershell
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

## Secret LSE

En local, créer un fichier non versionné :

```text
.streamlit/secrets.toml
```

avec :

```toml
LSE_API_KEY = "TA_CLE"
```

Sur la plateforme, ajouter la même clé dans les secrets de l'application.

## Limite importante du P&L

Le résultat est un **paper P&L simulé**, pas un P&L de courtier.

Pour obtenir une approximation pertinente, il faut renseigner les caractéristiques
du produit réellement tradable :

- valeur monétaire du point ;
- tick size ;
- devise ;
- conversion FX ;
- commissions ;
- slippage ;
- produit cash, CFD, future ou ETF réellement exécuté.

Le symbole de données LSE peut représenter un indice ou un proxy et ne garantit
pas qu'un produit exécutable possède exactement le même prix ou la même
microstructure.

## Sécurité

Le WebSocket LSE est ouvert dans le navigateur. La clé peut donc être inspectée
par les utilisateurs ayant accès au site. Le déploiement doit rester privé ou
protégé par authentification.
