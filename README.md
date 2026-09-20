# DataLab Enedis Live

Frontend Streamlit public (sécurisé par sas d'authentification) pour le projet **DataLab Enedis**.

Ce portail agit exclusivement comme un client léger consommant les endpoints de l'API privée **DataLab-Enedis** via des requêtes HTTP effectuées côté serveur.

---

## 1. Architecture de sécurité

```
Navigateur utilisateur
       │
       │ (HTTPS / WebSocket Streamlit)
       ▼
┌────────────────────────────────────────────────────────┐
│ Streamlit Live Portal (Public Safe)                    │
│                                                        │
│  [ SAS D'AUTHENTIFICATION ]                            │
│  - Demande Username + Password                         │
│  - Vérification par PBKDF2-HMAC-SHA256 (salé, 600k it) │
│  - Comparaison en temps constant (hmac.compare_digest) │
│  - Aucun mot de passe en clair toléré                  │
│  - Session authentifiée + Déconnexion                  │
│  - Fail-closed si credentials non configurés          │
│                                                        │
│  [ CLIENT HTTP SERVEUR ]                               │
│  - Émet les requêtes côté serveur Python               │
│  - Transmet X-DataLab-Token au backend                 │
│  - Le token n'est JAMAIS envoyé au navigateur          │
└────────────────────────────────────────────────────────┘
       │
       │ (HTTPS + X-DataLab-Token côté serveur)
       ▼
┌────────────────────────────────────────────────────────┐
│ Backend DataLab-Enedis (Privé)                         │
│  - Valide X-DataLab-Token (temps constant, fail-closed)│
│  - Surface réduite (/docs, /redoc, /openapi désactivés)│
│  - Moteur analytique (Bench, Radar, Watch)             │
│  - Accès aux fichiers Parquet et DuckDB                │
└────────────────────────────────────────────────────────┘
```

### Garanties de sécurité :
1. **Public-Safe** : Le présent dossier ne contient aucun algorithme métier propriétaire, aucun calcul d'ajustement sectoriel, aucun fichier DuckDB ou Parquet, et aucun secret.
2. **Sas d'authentification obligatoire** : Aucun appel réseau vers le backend n'est émis tant que l'utilisateur n'a pas validé son identifiant et son mot de passe.
3. **Dérivation forte de mot de passe** : Utilisation exclusive de PBKDF2-HMAC-SHA256 avec 600 000 itérations et sel aléatoire de 16 octets. Aucun mot de passe en clair n'est accepté.
4. **Isolation des secrets** : `DATALAB_API_TOKEN` est manipulé uniquement côté serveur par le client Python Streamlit. Le client Web ne peut pas extraire le jeton ni court-circuiter l'authentification.
5. **Fail-Closed** : Si les identifiants ou le token d'API sont absents ou mal formés, l'application bloque immédiatement l'accès.

---

## 2. Secrets et configuration

Quatre variables sont nécessaires pour exécuter l'application :

| Variable | Description | Exemple |
|---|---|---|
| `LIVE_USERNAME` | Identifiant autorisé | `admin` |
| `LIVE_PASSWORD_HASH` | Empreinte PBKDF2-HMAC-SHA256 | `pbkdf2_sha256$600000$4a8e...$9f2c...` |
| `DATALAB_API_URL` | URL racine du backend privé | `https://datalab-api.up.railway.app` |
| `DATALAB_API_TOKEN` | Jeton secret partagé avec le backend | `secret-token-value` |

### Génération du hash PBKDF2-HMAC-SHA256

Pour générer le hash sans jamais écrire le mot de passe en clair dans un fichier Git :

**Méthode 1 (invite interactive) :**
```bash
python auth.py
```

**Méthode 2 (one-liner Python standard) :**
```bash
python -c "import hashlib, secrets, getpass; s = secrets.token_bytes(16); it = 600000; p = getpass.getpass('Mot de passe : '); dk = hashlib.pbkdf2_hmac('sha256', p.encode(), s, it).hex(); print(f'pbkdf2_sha256${it}${s.hex()}${dk}')"
```

---

## 3. Lancement local

1. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

2. Configurer les secrets locaux :
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Renseignez vos identifiants et les coordonnées de l'API dans `.streamlit/secrets.toml`.

3. Lancer l'application :
   ```bash
   streamlit run app.py
   ```

---

## 4. Déploiement sur Streamlit Community Cloud

1. Déposer le contenu de ce dossier dans un repo public GitHub distinct : `cdurand42/DataLab-Live`.
2. Connecter l'application sur [Streamlit Community Cloud](https://share.streamlit.io/) :
   - **Repository** : `cdurand42/DataLab-Live`
   - **Branch** : `main`
   - **Main file path** : `app.py`
3. Dans les **Advanced Settings** > **Secrets** de Streamlit Cloud, renseigner :
   ```toml
   LIVE_USERNAME = "votre_identifiant"
   LIVE_PASSWORD_HASH = "pbkdf2_sha256$600000$..."
   DATALAB_API_URL = "https://votre-backend-datalab.up.railway.app"
   DATALAB_API_TOKEN = "votre_token_secret"
   ```
4. Déployer l'application.
