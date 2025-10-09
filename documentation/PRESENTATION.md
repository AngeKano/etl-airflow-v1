# Pipeline ETL Grand Livre Comptes

## 🎯 Objectif du projet

Automatiser la transformation de fichiers Excel "Grand Livre Comptes" en fichiers structurés (JSON + Excel) prêts à l'emploi.

## 🔄 Fonctionnement général

```
📂 Fichier Excel déposé
         ↓
   🔍 Détection automatique (Airflow)
         ↓
   ⚙️ Transformation des données
         ↓
   💾 Génération JSON + Excel
         ↓
   ✅ Fichiers prêts dans output/
```

## 📦 Architecture du projet

### 1️⃣ **Airflow (Orchestrateur)**
- **Rôle** : Surveille, planifie et exécute le pipeline
- **Quand** : Toutes les 5 minutes (configurable)
- **Où** : http://localhost:8080

### 2️⃣ **DAG (Workflow)**
- **Rôle** : Définit les étapes du pipeline
- **Fichier** : `dags/etl_excel_pipeline.py`
- **Étapes** :
  1. Détecter les fichiers Excel
  2. Transformer les données
  3. Afficher le résumé

### 3️⃣ **Script de transformation**
- **Rôle** : Lit l'Excel et extrait les données comptables
- **Fichier** : `scripts/transform_excel.py`
- **Actions** :
  - Parse le format Grand Livre
  - Extrait les comptes et transactions
  - Génère JSON + Excel

### 4️⃣ **Dossiers de données**
- **`data/input/`** : Dépôt des fichiers Excel à traiter
- **`data/output/`** : Fichiers transformés (JSON + Excel)
- **`data/input/processed/`** : Archive des fichiers traités

## 📋 Détail des fichiers

### `dags/etl_excel_pipeline.py`
**Le cerveau du pipeline**

```python
# Définit 2 tâches principales:
# 1. Détecter et traiter les fichiers
# 2. Afficher le résumé
```

**Paramètres importants :**
- `schedule_interval='*/5 * * * *'` → Fréquence d'exécution (5 min)
- `INPUT_DIR` → Chemin du dossier d'entrée
- `OUTPUT_DIR` → Chemin du dossier de sortie

### `scripts/transform_excel.py`
**Le moteur de transformation**

**Fonctions principales :**

1. **`parse_grand_livre_comptes()`**
   - Lit le fichier Excel
   - Détecte l'entité, la période
   - Extrait les comptes (numéro à 6 chiffres + libellé)
   - Extrait les transactions (date + journal + montants)

2. **`save_outputs()`**
   - Génère le fichier JSON structuré
   - Génère le fichier Excel plat

3. **`transform_file()`**
   - Fonction principale qui orchestre tout

**Format d'entrée attendu :**
```
Ligne avec: [Numéro compte 6 chiffres] [null] [Libellé compte]
  Transactions:
    [Date DDMMYY] [Code Journal] [N° Pièce] ... [Débit col 11] [Crédit col 14] [Solde col 17]
```

### `docker-compose.yml`
**Configuration de l'environnement**

**Services lancés :**
- `postgres` : Base de données pour Airflow
- `airflow-webserver` : Interface web (port 8080)
- `airflow-scheduler` : Exécuteur des tâches
- `airflow-init` : Initialisation (première fois)

**Volumes montés :**
- `./dags` → `/opt/airflow/dags` (vos DAGs)
- `./scripts` → `/opt/airflow/scripts` (vos scripts)
- `./data` → `/opt/airflow/data` (vos données)

### `requirements.txt`
**Dépendances Python**

- `apache-airflow` : Orchestrateur
- `pandas` : Manipulation de données
- `openpyxl` : Lecture/écriture Excel

## 🎬 Cycle de vie d'un fichier

### 1. Dépôt
```bash
cp mon_grand_livre.xlsx data/input/
```

### 2. Détection (toutes les 5 min)
Airflow vérifie `data/input/` et détecte `mon_grand_livre.xlsx`

### 3. Transformation
```
mon_grand_livre.xlsx
  ↓ Lecture avec openpyxl
  ↓ Extraction métadonnées (entité, période)
  ↓ Parsing comptes (6 chiffres + libellé)
  ↓ Parsing transactions (date + montants)
  ↓ Structure des données
```

### 4. Génération
Crée 2 fichiers dans `data/output/` :
- `mon_grand_livre_20251008.json`
- `mon_grand_livre_20251008.xlsx`

### 5. Archivage
Le fichier original est déplacé vers `data/input/processed/`

## 📊 Format des fichiers de sortie

### JSON (structure hiérarchique)
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
        "Libelle_Ecriture": "Virement client",
        "Debit": 1000.0,
        "Credit": 0.0,
        "Solde": 1000.0
      }
    ]
  }
]
```

### Excel (tableau plat)
Chaque ligne = 1 transaction avec toutes les infos :

| Numero_Compte | Libelle_Compte | Periode | Date | Debit | Credit | Solde |
|---------------|----------------|---------|------|-------|--------|-------|
| 512000 | Banque | 202412 | 01/12/2024 | 1000 | 0 | 1000 |

## ⚙️ Configuration

### Modifier la fréquence d'exécution

Dans `dags/etl_excel_pipeline.py` :

```python
# Toutes les 5 minutes (défaut)
schedule_interval='*/5 * * * *'

# Toutes les 15 minutes
schedule_interval='*/15 * * * *'

# Toutes les heures
schedule_interval='0 * * * *'

# Une fois par jour à 9h
schedule_interval='0 9 * * *'

# Désactiver l'auto (manuel uniquement)
schedule_interval=None
```

### Modifier les chemins

Dans `dags/etl_excel_pipeline.py` :

```python
INPUT_DIR = "/opt/airflow/data/input"   # Chemin dans Docker
OUTPUT_DIR = "/opt/airflow/data/output"

# Ces chemins correspondent à:
# ./data/input/  sur votre machine
# ./data/output/ sur votre machine
```

## 🔍 Monitoring

### Via l'interface Airflow (http://localhost:8080)

1. **Vue d'ensemble** : Liste de tous les DAGs
2. **Graph View** : Visualisation du workflow
3. **Logs** : Détails d'exécution de chaque tâche
4. **Runs** : Historique des exécutions

### Via les logs Docker

```bash
# Logs en temps réel du scheduler
docker-compose logs -f airflow-scheduler

# Logs d'une tâche spécifique
# (disponibles aussi dans l'interface web)
```

## 🚨 Gestion des erreurs

### Si un fichier échoue
- Le fichier reste dans `data/input/`
- L'erreur est visible dans les logs Airflow
- Les autres fichiers continuent d'être traités

### Si le format est incorrect
- Message d'erreur dans les logs
- Vérifiez que le fichier respecte le format attendu
- Colonnes débit (11), crédit (14), solde (17)

## 💡 Bonnes pratiques

### ✅ À faire
- Tester avec un petit fichier d'abord
- Consulter les logs en cas de problème
- Sauvegarder les fichiers output importants
- Vider régulièrement `data/input/processed/`

### ❌ À éviter
- Ne pas déposer de fichiers non-Excel dans input/
- Ne pas modifier les fichiers pendant le traitement
- Ne pas arrêter Docker pendant une exécution

## 📈 Évolutions possibles

### Court terme
- Notification email en cas d'erreur
- Dashboard de statistiques
- Validation du format avant traitement

### Moyen terme
- Interface web pour déposer les fichiers
- Export vers base de données
- Génération de rapports automatiques

### Long terme
- Migration vers AWS S3
- API REST pour interroger les données
- Machine Learning sur les transactions

## 🆘 Aide rapide

| Problème | Solution |
|----------|----------|
| DAG non visible | Vérifier `docker-compose logs airflow-scheduler` |
| Fichier non traité | Vérifier que le DAG est activé (ON) |
| Erreur de format | Consulter les logs de la tâche dans Airflow |
| Container qui crash | `docker-compose down && docker-compose up -d` |
| Manque de RAM | Augmenter RAM Docker (4 GB minimum) |

## 📞 Support

Pour toute question :
1. Consultez les logs dans l'interface Airflow
2. Vérifiez ce document
3. Examinez les logs Docker : `docker-compose logs`