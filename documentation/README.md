# Guide de démarrage - Pipeline ETL Airflow

## 📋 Prérequis

- Docker Desktop installé et lancé
- 4 GB de RAM minimum disponible

## 🚀 Installation en 5 étapes

### Étape 1 : Créer la structure des dossiers

```bash
# Créer le dossier du projet
mkdir etl-airflow-project
cd etl-airflow-project

# Créer tous les sous-dossiers
mkdir -p dags scripts data/input data/output logs plugins
```

### Étape 2 : Créer les fichiers

Créez les fichiers suivants dans leurs dossiers respectifs :

1. **dags/etl_excel_pipeline.py** → Le DAG Airflow
2. **scripts/transform_excel.py** → Le script de transformation
3. **docker-compose.yml** → Configuration Docker
4. **requirements.txt** → Dépendances Python

### Étape 3 : Configurer l'environnement

```bash
# Créer le fichier .env
echo -e "AIRFLOW_UID=$(id -u)" > .env
```

### Étape 4 : Installer les dépendances dans l'image Docker

Créez un fichier `Dockerfile` :

```dockerfile
FROM apache/airflow:2.7.1-python3.11

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
```

Modifiez le `docker-compose.yml` pour utiliser cette image :

```yaml
# Remplacer la ligne "image: apache/airflow:2.7.1-python3.11" par:
build: .
```

### Étape 5 : Démarrer Airflow

```bash
# Construire l'image
docker-compose build

# Initialiser la base de données
docker-compose up airflow-init

# Démarrer tous les services
docker-compose up -d
```

## 🎯 Utilisation

### Accéder à l'interface Airflow

1. Ouvrez votre navigateur : http://localhost:8080
2. Identifiants par défaut :
   - **Username:** airflow
   - **Password:** airflow

### Traiter un fichier Excel

1. Copiez votre fichier Excel dans le dossier `data/input/` :
   ```bash
   cp mon_fichier.xlsx data/input/
   ```

2. Dans l'interface Airflow :
   - Trouvez le DAG `etl_excel_grand_livre`
   - Activez-le (toggle sur ON)
   - Le pipeline se lance automatiquement toutes les 5 minutes

3. Vérifiez les résultats dans `data/output/` :
   - Un fichier `.json` (données structurées)
   - Un fichier `.xlsx` (données en tableau)

### Suivre l'exécution

Dans l'interface Airflow :
- Cliquez sur le DAG `etl_excel_grand_livre`
- Onglet **Graph** : voir le workflow
- Cliquez sur une tâche → **Logs** pour voir les détails

## 📊 Voir les logs en temps réel

```bash
# Logs du scheduler
docker-compose logs -f airflow-scheduler

# Logs du webserver
docker-compose logs -f airflow-webserver
```

## 🛑 Arrêter le projet

```bash
# Arrêter tous les services
docker-compose down

# Arrêter ET supprimer les données (attention!)
docker-compose down -v
```

## 🔧 Dépannage

### Le DAG n'apparaît pas

```bash
# Vérifier les logs du scheduler
docker-compose logs airflow-scheduler

# Vérifier que le fichier DAG est bien présent
ls -la dags/
```

### Erreur de permissions

```bash
# Recréer le fichier .env avec le bon UID
echo -e "AIRFLOW_UID=$(id -u)" > .env
docker-compose down
docker-compose up airflow-init
docker-compose up -d
```

### Le fichier n'est pas traité

1. Vérifiez que le fichier est bien dans `data/input/`
2. Vérifiez que le DAG est activé (toggle ON)
3. Consultez les logs de la tâche dans l'interface Airflow

## 📝 Structure des fichiers de sortie

### Fichier JSON
```json
[
  {
    "Numero_Compte": "512000",
    "Libelle_Compte": "Banque",
    "Periode": "202412",
    "Transactions": [
      {
        "Date_GL": "31/12/2024",
        "Entite": "ENVOL",
        "Compte": "512000",
        "Date": "01/12/2024",
        "Code_Journal": "BQ",
        "Numero_Piece": "001",
        "Libelle_Ecriture": "Virement",
        "Debit": 1000.0,
        "Credit": 0.0,
        "Solde": 1000.0
      }
    ]
  }
]
```

### Fichier Excel
Tableau avec colonnes :
- Numero_Compte
- Libelle_Compte  
- Periode
- Date_GL
- Entite
- Compte
- Date
- Code_Journal
- Numero_Piece
- Libelle_Ecriture
- Debit
- Credit
- Solde

## ⏰ Modifier la fréquence d'exécution

Dans `dags/etl_excel_pipeline.py`, changez `schedule_interval` :

```python
# Toutes les 5 minutes (défaut)
schedule_interval='*/5 * * * *'

# Toutes les heures
schedule_interval='0 * * * *'

# Tous les jours à 9h
schedule_interval='0 9 * * *'

# Manuel uniquement
schedule_interval=None
```

## 🎓 Commandes utiles

```bash
# Redémarrer un service spécifique
docker-compose restart airflow-scheduler

# Voir tous les conteneurs
docker-compose ps

# Entrer dans le conteneur webserver
docker-compose exec airflow-webserver bash

# Nettoyer les logs
rm -rf logs/*
```