# 📊 Guide Visuel du Pipeline ETL

## 🎯 Vue d'ensemble en 1 image

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE ETL AIRFLOW                     │
└─────────────────────────────────────────────────────────────┘

   1️⃣ DÉPÔT                 2️⃣ DÉTECTION              3️⃣ TRANSFORMATION
   ─────────                ──────────────            ─────────────────
                                                      
   📂 data/input/           🔍 Airflow DAG            ⚙️  Python Script
   │                        (toutes les 5 min)       │
   └─ fichier.xlsx  ───────────────────────────────> │ Lecture Excel
                                                      │ Parse comptes
                                                      │ Parse transactions
                                                      │ Structure données
                                                      ▼
   4️⃣ GÉNÉRATION            5️⃣ ARCHIVAGE
   ─────────────            ──────────────
   
   📥 data/output/          📦 data/input/processed/
   │                        │
   ├─ fichier.json          └─ fichier.xlsx (original)
   └─ fichier.xlsx          
      (transformé)
```

## 🏗️ Architecture technique

```
┌──────────────────────────────────────────────────────────────┐
│                        DOCKER                                │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │   PostgreSQL   │  │   Airflow      │  │   Airflow     │ │
│  │   (Base de     │◄─┤   Webserver    │◄─┤   Scheduler   │ │
│  │   données)     │  │   (Interface)  │  │   (Exécution) │ │
│  └────────────────┘  └────────────────┘  └───────────────┘ │
│         │                     │                    │        │
│         │                     │                    │        │
│         └─────────────────────┴────────────────────┘        │
│                               │                             │
│                               ▼                             │
│                    ┌─────────────────────┐                  │
│                    │   Votre Machine     │                  │
│                    │                     │                  │
│                    │  📂 dags/           │                  │
│                    │  📂 scripts/        │                  │
│                    │  📂 data/           │                  │
│                    └─────────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
         Port 8080                   Volumes partagés
```

## 📁 Flux des données

```
FICHIER EXCEL SOURCE
┌──────────────────────────────────────────────────┐
│ Entité                                           │
│ Période du: 01/01/2024 au: 31/12/2024          │
│                                                  │
│ 512000         Banque                           │
│ 010124  BQ  001     ...     1000.00      1000.00│
│ 020124  BQ  002     ...      500.00      1500.00│
│                                                  │
│ 601000         Achats                           │
│ 030124  AC  003     ...      200.00       200.00│
└──────────────────────────────────────────────────┘
                    │
                    │ TRANSFORMATION
                    ▼
┌──────────────────────────────────────────────────┐
│ JSON STRUCTURÉ                                   │
├──────────────────────────────────────────────────┤
│ [                                                │
│   {                                              │
│     "Numero_Compte": "512000",                   │
│     "Libelle_Compte": "Banque",                  │
│     "Periode": "202412",                         │
│     "Transactions": [                            │
│       {                                          │
│         "Date": "01/01/2024",                    │
│         "Debit": 1000.0,                         │
│         "Credit": 0.0,                           │
│         "Solde": 1000.0                          │
│       }                                          │
│     ]                                            │
│   }                                              │
│ ]                                                │
└──────────────────────────────────────────────────┘
                    +
┌──────────────────────────────────────────────────┐
│ EXCEL PLAT                                       │
├──────┬─────────┬────────┬──────┬────────┬────────┤
│ Compte│ Libellé │ Date   │Débit │ Crédit │ Solde │
├──────┼─────────┼────────┼──────┼────────┼────────┤
│512000│ Banque  │01/01/24│ 1000 │    0   │ 1000  │
│512000│ Banque  │02/01/24│  500 │    0   │ 1500  │
│601000│ Achats  │03/01/24│  200 │    0   │  200  │
└──────┴─────────┴────────┴──────┴────────┴────────┘
```

## 🔄 Cycle de vie dans Airflow

```
┌─────────────────────────────────────────────────────┐
│              INTERFACE AIRFLOW                      │
│           http://localhost:8080                     │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │    etl_excel_grand_livre  │ ◄─── Votre DAG
        │         (DAG)             │
        └──────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌──────────────────┐      ┌──────────────────┐
│  detect_and_     │      │  show_summary    │
│  process_files   │─────▶│                  │
│  (Task 1)        │      │  (Task 2)        │
└──────────────────┘      └──────────────────┘
        │                           │
        ▼                           ▼
   📂 Traitement              ✅ Résumé affiché
      des fichiers               dans les logs
```

## ⏱️ Timeline d'exécution

```
Minute 0    ─────────────────────────────────────
              ↓
              Airflow détecte un nouveau fichier
              ↓
Minute 0+5s ─────────────────────────────────────
              ↓
              Task 1: detect_and_process_files
              - Lit le fichier Excel
              - Parse les données
              - Génère JSON + Excel
              ↓
Minute 1    ─────────────────────────────────────
              ↓
              Task 2: show_summary
              - Compte les fichiers générés
              - Affiche le résumé
              ↓
Minute 1+10s ─────────────────────────────────────
              ↓
              ✅ Pipeline terminé avec succès
              ↓
Minute 5    ─────────────────────────────────────
              ↓
              Nouveau cycle démarre
              (vérifie s'il y a de nouveaux fichiers)
```

## 🎨 États du DAG dans Airflow

```
⚪ None         → Pas encore exécuté
🟡 Queued      → En attente dans la queue
🔵 Running     → En cours d'exécution
🟢 Success     → Terminé avec succès
🔴 Failed      → Échec (erreur)
🟠 Skipped     → Sauté (condition non remplie)
🟣 Upstream    → En attente d'une tâche précédente
```

## 📊 Exemple concret de transformation

### Avant (Excel source)
```
┌────────┬──────┬──────────┬─────────┬──────────┬──────────┬──────────┐
│ Col 0  │ Col 1│  Col 2   │  Col 5  │  Col 11  │  Col 14  │  Col 17  │
├────────┼──────┼──────────┼─────────┼──────────┼──────────┼──────────┤
│ 512000 │ null │  Banque  │         │          │          │          │ ← Ligne compte
│ 010124 │  BQ  │   001    │ Virement│  1000.00 │          │  1000.00 │ ← Transaction 1
│ 020124 │  BQ  │   002    │ Dépôt   │   500.00 │          │  1500.00 │ ← Transaction 2
│ 030124 │  BQ  │   003    │ Retrait │          │   200.00 │  1300.00 │ ← Transaction 3
└────────┴──────┴──────────┴─────────┴──────────┴──────────┴──────────┘
```

### Après (JSON structuré)
```json
{
  "Numero_Compte": "512000",
  "Libelle_Compte": "Banque",
  "Periode": "202412",
  "Transactions": [
    {
      "Date": "01/01/2024",
      "Code_Journal": "BQ",
      "Numero_Piece": "001",
      "Libelle_Ecriture": "Virement",
      "Debit": 1000.0,
      "Credit": 0.0,
      "Solde": 1000.0
    },
    {
      "Date": "02/01/2024",
      "Code_Journal": "BQ",
      "Numero_Piece": "002",
      "Libelle_Ecriture": "Dépôt",
      "Debit": 500.0,
      "Credit": 0.0,
      "Solde": 1500.0
    },
    {
      "Date": "03/01/2024",
      "Code_Journal": "BQ",
      "Numero_Piece": "003",
      "Libelle_Ecriture": "Retrait",
      "Debit": 0.0,
      "Credit": 200.0,
      "Solde": 1300.0
    }
  ]
}
```

## 🗂️ Organisation des fichiers

```
📦 data/
│
├── 📂 input/                    ← Vous déposez ici
│   ├── grand_livre_jan.xlsx    ← Nouveau fichier
│   ├── grand_livre_fev.xlsx    ← Nouveau fichier
│   │
│   └── 📂 processed/            ← Archive automatique
│       ├── grand_livre_jan.xlsx
│       └── grand_livre_fev.xlsx
│
└── 📂 output/                   ← Résultats ici
    ├── grand_livre_jan_20251008.json
    ├── grand_livre_jan_20251008.xlsx
    ├── grand_livre_fev_20251008.json
    └── grand_livre_fev_20251008.xlsx
```

## 🔍 Comment lire les logs Airflow

```
Interface Airflow → Cliquez sur le DAG → Cliquez sur une Task → Onglet "Log"

Exemple de log réussi:
───────────────────────────────────────────────────────────
[2025-10-08, 14:30:00] {taskinstance.py:1234} INFO - Starting
[2025-10-08, 14:30:01] {transform_excel.py:150} INFO - 
🔄 Transformation de: /opt/airflow/data/input/grand_livre.xlsx
[2025-10-08, 14:30:05] {transform_excel.py:220} INFO - 
✅ Fichiers générés:
   - JSON: /opt/airflow/data/output/grand_livre_20251008.json
   - Excel: /opt/airflow/data/output/grand_livre_20251008.xlsx
   - 15 comptes traités
   - 247 transactions extraites
[2025-10-08, 14:30:06] {taskinstance.py:1456} INFO - 
Task completed successfully
───────────────────────────────────────────────────────────
```

## ⚡ Commandes essentielles

```bash
# Démarrer le projet
./start.sh

# Voir les logs en direct
docker-compose logs -f airflow-scheduler

# Arrêter le projet
docker-compose down

# Redémarrer un service
docker-compose restart airflow-scheduler

# Voir l'état des conteneurs
docker-compose ps

# Nettoyer complètement (attention: supprime tout!)
docker-compose down -v
rm -rf logs/* data/input/* data/output/*
```

## 🎯 Points clés de détection

Le script détecte un **compte** quand:
```
✅ Colonne 0 = 6 chiffres (ex: 512000)
✅ Colonne 1 = null/vide
✅ Colonne 2 = texte (libellé)
```

Le script détecte une **transaction** quand:
```
✅ Colonne 0 = 6 chiffres (date DDMMYY)
✅ Colonne 1 = texte (code journal)
✅ Colonne 11 = débit (nombre ou vide)
✅ Colonne 14 = crédit (nombre ou vide)
✅ Colonne 17 = solde (nombre)
```

## 🚦 Statuts possibles

```
Fichier déposé → ✅ Traité → Archivé dans processed/
                 ❌ Erreur → Reste dans input/ + log d'erreur
```

## 📈 Monitoring simple

### Dans le terminal
```bash
# Voir combien de fichiers en attente
ls -1 data/input/*.xlsx 2>/dev/null | wc -l

# Voir combien de fichiers traités
ls -1 data/output/*.json 2>/dev/null | wc -l

# Taille des fichiers de sortie
du -sh data/output/
```

### Dans Airflow (http://localhost:8080)
```
Dashboard → Voir tous les DAGs
Graph → Visualiser le workflow
Calendar → Voir l'historique des exécutions
```

## 🎨 Interface Airflow en images (description)

```
┌─────────────────────────────────────────────────────┐
│  Apache Airflow                          airflow ▾  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  DAGs        etl_excel_grand_livre    [Toggle ON]  │
│              ────────────────────────               │
│              📊 Graph  📅 Calendar  📄 Code         │
│                                                     │
│  ┌──────────────────┐      ┌──────────────────┐   │
│  │ detect_and_      │────▶ │ show_summary     │   │
│  │ process_files    │      │                  │   │
│  │   🟢 Success     │      │   🟢 Success     │   │
│  └──────────────────┘      └──────────────────┘   │
│                                                     │
│  Last run: 2 minutes ago                           │
│  Next run: in 3 minutes                            │
│  Duration: 45 seconds                              │
└─────────────────────────────────────────────────────┘
```

## 🔄 Cas d'usage typiques

### Cas 1: Traitement unique
```
Besoin: Transformer 1 fichier immédiatement

1. Déposer le fichier dans data/input/
2. Aller dans Airflow
3. Cliquer sur "Trigger DAG" ▶️
4. Attendre 30-60 secondes
5. Récupérer les résultats dans data/output/
```

### Cas 2: Traitement batch
```
Besoin: Traiter 10 fichiers d'un coup

1. Copier tous les fichiers dans data/input/
2. Le DAG les traite automatiquement un par un
3. Surveiller la progression dans Airflow
4. Tous les résultats dans data/output/
```

### Cas 3: Surveillance continue
```
Besoin: Traiter automatiquement les nouveaux fichiers

1. Laisser le DAG activé (toutes les 5 min)
2. Déposer des fichiers quand nécessaire
3. Le système les traite automatiquement
4. Pas besoin d'intervention manuelle
```

## 💡 Astuces rapides

### Voir rapidement le résultat
```bash
# Compter les comptes traités
cat data/output/*.json | grep "Numero_Compte" | wc -l

# Compter les transactions
cat data/output/*.json | grep "Date_GL" | wc -l

# Voir la structure d'un fichier JSON
cat data/output/*.json | head -50
```

### Tester sans Airflow
```bash
# Lancer directement le script de transformation
python scripts/transform_excel.py \
  data/input/mon_fichier.xlsx \
  data/output/

# Pratique pour débugger!
```

## 🆘 Dépannage visuel

```
Problème                          Solution
────────                          ────────
❌ DAG invisible                  → Attendre 2 min + F5
❌ Task bloquée "running"         → docker-compose restart airflow-scheduler
❌ Fichier non traité             → Vérifier format Excel (colonnes 11,14,17)
❌ Erreur "permission denied"     → rm .env && ./start.sh
❌ Container crash                → docker-compose logs [service-name]
❌ Port 8080 occupé               → Changer port dans docker-compose.yml
```

## 🎓 Prochaines étapes

Une fois le projet fonctionnel:

1. **Tester** avec vos vrais fichiers Grand Livre
2. **Ajuster** la fréquence d'exécution si besoin
3. **Personnaliser** le format de sortie
4. **Automatiser** le dépôt des fichiers
5. **Monitorer** les performances

Vous avez maintenant un pipeline ETL professionnel et simple! 🚀