# Changelog — V2 Shadow Trader

## V2.1 — Correctifs Shadow Trader

Patch chirurgical. Les pages Workspace, Bureau Larbou et Kalman Lab ne sont pas
touchées, `main.py` reste l'unique entrypoint.

### 1. Les seuils en σ n'étaient pas des σ — le moteur ne tradait pas

`slopeZ` divisait la pente par l'écart-type des différences tick-à-tick, une
grandeur sans rapport avec l'échelle de la pente. Écart-type réel mesuré de
`slopeZ` : environ 0.25 au lieu de 1. Le seuil d'entrée par défaut de 0.65 « σ »
se situait donc à ~2.6 σ dans la queue. En simulation : 22 entrées sur
19 500 ticks avec les réglages par défaut, et **zéro entrée** à confiance = 3.
`innovationZ` souffrait du même défaut, mais son échelle dépendait entièrement
du curseur de confiance (sd de 0.14 à 8.29) : le seuil de choc à 2.75 ne se
déclenchait jamais à confiance basse et déclenchait 74 % du temps à confiance
haute, d'où un RISK OFF permanent.

Correctif : la pente et l'innovation sont normalisées par leur propre RMS
roulant. Écart-type mesuré désormais entre 1.00 et 1.06 pour les neuf
combinaisons réactivité × confiance testées.

Les émissions du HMM supposaient `slopeZ ~ N(±0.9, 0.72)` face à un `slopeZ`
observé en `N(0, 0.25)` : l'état NOISE gagnait toujours et la probabilité de
hausse n'atteignait jamais le seuil de 0.70. Émissions recalibrées sur la
nouvelle échelle.

### 2. Commissions et kill switch

La commission était appliquée par unité. Sur EUR/USD, un sizing de
185 185 unités produisait 92 592 € de frais d'entrée, contre 5 € sur le Nasdaq
pour le même notionnel. La commission est désormais exprimée en points de base
du notionnel exécuté, avec plancher optionnel. Coût par trade mesuré après
correctif : 29.99 € sur le Nasdaq et 30.00 € sur EUR/USD, à notionnel égal.

Le kill switch de session était enfermé derrière `if(!portfolio.trade)return` :
inatteignable à plat. Une perte réalisée dépassant la limite ne verrouillait
jamais la session, qui rouvrait des positions jusqu'au plafond de trades. Le
contrôle de session est sorti de cette garde. Vérification : verrouillage après
11 trades à −330 € pour une limite de 300 €.

### 3. Les modèles pair ne mesuraient pas ce qu'ils annonçaient

Pour le Relative Value, le résiduel utilisé comme spread était l'innovation de
la régression. Avec `qA = résiduel × 5e-3`, l'intercept avait une mémoire de
~14 ticks : il ramenait le spread à zéro en permanence, donc un spread ne
pouvait jamais paraître étiré. Sur une paire cointégrée simulée dont le vrai
spread est connu, la corrélation entre le z-score et le vrai spread valait 0.04.

Correctifs : `x` est centré sur sa moyenne de warm-up (avec `x = log(prix) ≈ 8.5`,
intercept et pente étaient quasi colinéaires et la covariance initiale de beta,
`0.1`, impliquait un sd de 0.32 sur un beta vrai de ~0.7) ; la covariance
initiale est la covariance OLS exacte ; l'intercept du RV est ralenti d'un
facteur 5000. Corrélation mesurée après correctif : 0.55. Le RV passe de 0 à
142 trades sur la même série.

Le momentum résiduel lisait le résiduel brut de la régression de rendements,
c'est-à-dire du bruit blanc. Il lit désormais la dérive résiduelle cumulée sur
la fenêtre, normalisée par son propre RMS roulant — la standardisation par
`sd(résiduel)·√W` supposait des résidus iid alors qu'ils sont autocorrélés, et
donnait un sd réel de 0.48. Sd mesuré après correctif : 1.01.

### 4. Graphiques et terminal ne tenaient pas ensemble

Le contenu s'empilait verticalement pour ~1 260 px dans une iframe déclarée à
1 380 px, et le bouton FULLSCREEN échoue silencieusement depuis une iframe
Streamlit. Le cockpit remplit désormais exactement la hauteur de l'iframe, en
grille 2×2 — modèle, P&L, terminal, blotter visibles ensemble — avec un
sélecteur COCKPIT / CHARTS / TERMINAL / BLOTTER, un `ResizeObserver` relié à
Plotly et un rendu des graphiques limité à ~7 Hz.

### 5. Les curseurs coupaient la session

Toute modification d'un réglage régénérait le `srcdoc` de l'iframe, coupait le
WebSocket et remettait la session à zéro. Les réglages ne sont appliqués qu'au
clic sur **Appliquer & (re)lancer le cockpit**.

### Défauts modifiés

- seuil de pente d'entrée : 0.65 → 1.25 σ ; sortie : 0.15 → 0.35 σ ;
- commission : 0.50 par unité → 0.75 bps du notionnel par côté ;
- fenêtre de normalisation : nouveau réglage, 750 observations ;
- warm-up de la régression pair : 30 → 240 observations pour le RV, 60 sinon ;
- hauteur du cockpit : nouveau réglage, 820 px.

## Nouvelle page

Ajout de **Shadow Trader** à l'application tout-en-un.

## Ajouts fonctionnels

- quatre stratégies de paper trading distinctes ;
- sizing par capital et levier brut cible ;
- modèles single asset et pair ;
- hedge ratio dynamique ;
- exécution paper au bid/ask ;
- fallback au dernier prix ;
- slippage et commissions ;
- valeur du point, tick size et conversion FX ;
- P&L réalisé, latent et net ;
- P&L en basis points ;
- ticks équivalents Y ;
- drawdown ;
- stops et kill switch ;
- terminal brut de décisions ;
- trade blotter ;
- exports CSV ;
- replay utilisé comme warm-up ou comme session simulée ;
- boutons START, STOP & FLATTEN, RESET et FULLSCREEN.
