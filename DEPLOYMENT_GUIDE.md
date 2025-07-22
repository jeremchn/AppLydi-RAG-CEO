# Guide de déploiement RAG CEO sur GCP

## 🚀 Déploiement en 5 étapes

### Étape 1: Prérequis
1. **Compte Google Cloud Platform**
   - Créer un compte sur https://console.cloud.google.com
   - Activer la facturation
   - Créer un nouveau projet

2. **Clé API OpenAI**
   - Créer un compte sur https://platform.openai.com
   - Générer une clé API
   - Garder la clé secrète et sécurisée

3. **Outils locaux**
   - Installer Google Cloud SDK: https://cloud.google.com/sdk/docs/install
   - Git (pour cloner le projet)

### Étape 2: Configuration initiale GCP

1. **Ouvrir un terminal PowerShell en tant qu'administrateur**

2. **Authentification**
   ```powershell
   gcloud auth login
   ```

3. **Lister vos projets**
   ```powershell
   gcloud projects list
   ```

4. **Noter votre PROJECT_ID** (ex: `rag-ceo-123456`)

### Étape 3: Configuration automatique

1. **Naviguez vers le dossier du projet**
   ```powershell
   cd "C:\Users\jerem\Desktop\Rag_CEO"
   ```

2. **Rendez les scripts exécutables et exécutez la configuration**
   ```powershell
   # Sur Windows, utilisez Git Bash ou WSL
   bash scripts/setup-gcp.sh
   ```

   Le script va vous demander:
   - Votre PROJECT_ID GCP
   - Votre clé API OpenAI

### Étape 4: Déploiement

1. **Exécuter le déploiement**
   ```powershell
   bash scripts/deploy.sh
   ```

2. **Attendre la fin du déploiement** (5-10 minutes)

### Étape 5: Test de l'application

1. **Le script affichera les URLs**
   - Frontend: `https://rag-frontend-xxx.run.app`
   - Backend: `https://rag-backend-xxx.run.app`

2. **Tester l'application**
   - Ouvrir l'URL du frontend
   - Créer un compte
   - Télécharger un document PDF
   - Poser une question

## 🔧 Commandes PowerShell équivalentes

Si vous préférez faire étape par étape sous Windows :

### Configuration GCP
```powershell
# Authentification
gcloud auth login

# Configuration du projet (remplacez YOUR_PROJECT_ID)
gcloud config set project YOUR_PROJECT_ID
gcloud config set compute/region europe-west1

# Activation des APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Création des secrets
echo "YOUR_OPENAI_API_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
gcloud secrets create JWT_SECRET_KEY --data-file=<(openssl rand -hex 32)

# Création de la base de données
gcloud sql instances create rag-ceo-db --database-version=POSTGRES_15 --cpu=1 --memory=3840MB --region=europe-west1 --root-password=admin123 --authorized-networks=0.0.0.0/0
gcloud sql databases create ragdb --instance=rag-ceo-db
gcloud sql users create raguser --instance=rag-ceo-db --password=ragpassword
```

### Déploiement
```powershell
# Déploiement avec Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Obtenir les URLs
gcloud run services list --platform managed --region europe-west1
```

## 🎯 Après le déploiement

### Vérifications
1. **Backend API** : `https://votre-backend-url/docs`
2. **Frontend** : `https://votre-frontend-url`
3. **Logs** : Console GCP > Cloud Run > Logs

### Première utilisation
1. **Créer un compte utilisateur**
2. **Télécharger un document PDF de test**
3. **Poser une question sur le document**

### Monitoring
- **Console GCP** : https://console.cloud.google.com/run
- **Logs** : Surveillance des erreurs et performances
- **Métriques** : Utilisation et coûts

## 💰 Coûts estimés

### Coûts mensuels (usage faible)
- **Cloud Run** : 10-20€/mois
- **Cloud SQL** : 40-60€/mois
- **Stockage** : 1-5€/mois
- **OpenAI API** : Variable selon usage

### Optimisation des coûts
- Utiliser des instances partagées pour débuter
- Monitorer l'usage OpenAI
- Configurer des alertes de facturation

## 🔧 Dépannage

### Problèmes fréquents

1. **Erreur "Project not found"**
   ```powershell
   gcloud config set project YOUR_CORRECT_PROJECT_ID
   ```

2. **Erreur "API not enabled"**
   ```powershell
   gcloud services enable [SERVICE_NAME]
   ```

3. **Erreur de déploiement**
   - Vérifier les logs : Console GCP > Cloud Build > Historique
   - Vérifier les quotas : Console GCP > IAM > Quotas

4. **Application ne répond pas**
   - Vérifier les logs : Console GCP > Cloud Run > Logs
   - Vérifier les variables d'environnement

### Support
- **Documentation GCP** : https://cloud.google.com/docs
- **Status GCP** : https://status.cloud.google.com
- **Issues GitHub** : (votre repository)

## 🎉 Félicitations !

Votre application RAG CEO est maintenant déployée et accessible en ligne !

Prochaines étapes :
1. Personnaliser l'interface
2. Ajouter des fonctionnalités
3. Configurer la facturation
4. Préparer le marketing
