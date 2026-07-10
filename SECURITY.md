# Security

- Ne jamais committer `.streamlit/secrets.toml`.
- Ne jamais mettre la clé LSE dans `main.py`, la documentation ou les logs.
- Le WebSocket LSE est consommé dans le navigateur : un utilisateur autorisé
  peut inspecter la clé dans le trafic réseau.
- Garder l'application privée ou authentifiée.
- Pour un site public, utiliser un backend proxy sécurisé.
- Shadow Trader est un moteur de paper trading uniquement.
- Ne pas le connecter à un broker réel sans une architecture séparée :
  authentification, limites de risque, validations d'ordres, surveillance,
  journal d'audit et kill switch serveur.
