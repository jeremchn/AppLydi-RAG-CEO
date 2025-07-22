# 🚀 DÉPLOYEMENT RAPIDE RAG CEO

## ✅ Prérequis (5 minutes)

### 1. Google Cloud SDK
```bash
# Télécharger et installer depuis :
# https://cloud.google.com/sdk/docs/install

# Vérifier l'installation
gcloud --version
```

### 2. Compte Google Cloud
- Créer un projet sur https://console.cloud.google.com
- Activer la facturation
- Noter votre PROJECT_ID

### 3. Clé OpenAI
- Créer une clé API sur https://platform.openai.com/api-keys
- Garder la clé secrète

## 🚀 Déploiement en 1 commande (10 minutes)

### Pour Windows (PowerShell)
```powershell
# Ouvrir PowerShell en tant qu'administrateur
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Aller dans le dossier du projet
cd "C:\Users\jerem\Desktop\Rag_CEO"

# Exécuter le déploiement
.\scripts\deploy.bat
```

### Pour Windows (Script simplifié)
```batch
# Double-cliquer sur deploy.bat
# Ou exécuter dans cmd :
scripts\deploy.bat
```

## 📋 Étapes du script automatique

Le script va :
1. ✅ Vérifier gcloud CLI
2. 🔐 Vous authentifier sur GCP
3. 📝 Configurer le projet
4. 🔧 Activer les APIs nécessaires
5. 🔐 Créer les secrets (OpenAI, JWT)
6. 🗄️ Créer la base PostgreSQL
7. 🔨 Déployer l'application
8. 🔗 Afficher les URLs

## 🎯 Résultat attendu

À la fin, vous aurez :
- **Frontend** : https://rag-frontend-xxxxx.run.app
- **Backend** : https://rag-backend-xxxxx.run.app
- **API Docs** : https://rag-backend-xxxxx.run.app/docs

## 🔧 Test immédiat

1. Ouvrir l'URL du frontend
2. Créer un compte utilisateur
3. Télécharger un PDF (ex: manuel, rapport)
4. Poser une question sur le document
5. Recevoir une réponse personnalisée

## 💰 Coûts estimés

- **Développement** : ~5€/mois
- **Production légère** : ~75€/mois
- **Production intense** : ~200€/mois

## 🛠️ Dépannage

### Erreur "gcloud not found"
```bash
# Installer Google Cloud SDK
# https://cloud.google.com/sdk/docs/install
```

### Erreur "Project not found"
```bash
# Vérifier le PROJECT_ID
gcloud projects list
```

### Erreur "APIs not enabled"
```bash
# Les scripts activent automatiquement les APIs
# Si erreur, exécuter manuellement :
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
```

## 📞 Support

- **Console GCP** : https://console.cloud.google.com
- **Logs** : Console GCP > Cloud Run > Logs
- **Status GCP** : https://status.cloud.google.com

## 🎉 Prochaines étapes

Après le déploiement :
1. 🎨 Personnaliser l'interface
2. 💳 Configurer la facturation Stripe
3. 📊 Ajouter des analytics
4. 🚀 Préparer le lancement commercial

---

## 📝 INSTRUCTIONS DÉTAILLÉES

### Méthode 1 : Script automatique (RECOMMANDÉ)

1. **Ouvrir PowerShell en tant qu'administrateur**
2. **Naviguer vers le projet**
   ```powershell
   cd "C:\Users\jerem\Desktop\Rag_CEO"
   ```
3. **Exécuter le script**
   ```powershell
   .\scripts\deploy.bat
   ```
4. **Suivre les instructions** (PROJECT_ID, OpenAI Key)
5. **Attendre 10 minutes**
6. **Tester l'application**

### Méthode 2 : Commandes manuelles

Si vous préférez contrôler chaque étape :

```powershell
# 1. Authentification
gcloud auth login

# 2. Configuration (remplacer YOUR_PROJECT_ID)
gcloud config set project YOUR_PROJECT_ID
gcloud config set compute/region europe-west1

# 3. Activation des APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com sql-component.googleapis.com secretmanager.googleapis.com

# 4. Création des secrets
echo "YOUR_OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-

# 5. Base de données
gcloud sql instances create rag-ceo-db --database-version=POSTGRES_15 --cpu=1 --memory=3840MB --region=europe-west1

# 6. Déploiement
gcloud builds submit --config cloudbuild.yaml
```

## 🏆 Votre application est maintenant LIVE !

Félicitations ! Vous avez maintenant une application RAG professionnelle déployée sur Google Cloud Platform, prête à être commercialisée.
