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
- une commission en points de base du notionnel exécuté, par côté,
  avec plancher optionnel ;
- une valeur du point et un tick size configurables ;
- un facteur de conversion FX vers la devise du compte ;
- un levier brut cible ;
- un sizing automatique ;
- deux jambes pour les modèles pair.

### Cockpit

Le cockpit occupe une hauteur fixe, réglable dans la sidebar, et se répartit en
quatre panneaux visibles simultanément : modèle, P&L de session, terminal de
décision et blotter. Quatre vues permettent d'en isoler un :

- `COCKPIT` : les quatre panneaux en 2×2 ;
- `CHARTS` : les deux graphiques en pleine hauteur ;
- `TERMINAL` : le terminal seul ;
- `BLOTTER` : le blotter seul.

Le cockpit est une iframe : modifier un réglage la recrée et remet la session à
zéro. Les réglages ne sont donc appliqués qu'au clic sur **Appliquer &
(re)lancer le cockpit**, ce qui permet de déplacer les curseurs sans couper une
session en cours.

### Échelle des seuils

La pente du Kalman, l'innovation, le spread et le momentum résiduel sont
normalisés par leur propre RMS roulant sur une fenêtre configurable. Un seuil
exprimé en σ correspond donc à un vrai σ de la grandeur mesurée, quelle que
soit la réactivité, la confiance dans les ticks ou l'actif.

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
- commissions, en bps du notionnel ;
- slippage ;
- produit cash, CFD, future ou ETF réellement exécuté.

Le symbole de données LSE peut représenter un indice ou un proxy et ne garantit
pas qu'un produit exécutable possède exactement le même prix ou la même
microstructure.

## Sécurité

Le WebSocket LSE est ouvert dans le navigateur. La clé peut donc être inspectée
par les utilisateurs ayant accès au site. Le déploiement doit rester privé ou
protégé par authentification.
