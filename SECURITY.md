# Sécurité

La vraie clé LSE ne doit jamais être stockée dans Git.

Le fichier autorisé dans le dépôt est :

```text
.streamlit/secrets.toml.example
```

Le fichier suivant est ignoré :

```text
.streamlit/secrets.toml
```

Le flux live LSE est consommé par un composant JavaScript côté navigateur.
Même chargée depuis `st.secrets`, la clé est envoyée au navigateur afin
d'authentifier le WebSocket.

Le déploiement doit donc rester privé ou protégé. Pour une application publique,
il faut ajouter un proxy backend sécurisé et une authentification.
