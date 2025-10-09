# 📋 Liste complète des fichiers à créer

## Structure finale du projet

```
etl-airflow-project/
│
├── dags/
│   └── etl_excel_pipeline.py          ← Copier le code du DAG
│
├── scripts/
│   └── transform_excel.py              ← Copier le code de transformation
│
├── data/
│   ├── input/                          ← Créer ce dossier (vide)
│   └── output/                         ← Créer ce dossier (vide)
│
├── logs/                               ← Créer ce dossier (vide)
├── plugins/                            ← Créer ce dossier (vide)
│
├── docker-compose.yml                  ← Copier la config Docker Compose
├── Dockerfile                          ← Copier le Dockerfile
├── requirements.txt                    ← Copier les dépendances
├── start.sh                            ← Copier le script de démarrage
│
├── DEMARRAGE-RAPIDE.md                 ← Guide rapide (optionnel)
├── README.md                           ← Guide détaillé (optionnel)
└── PRESENTATION.md                     ← Documentation projet (optionnel)
```

## ✅ Checklist de création

### Étape 1 : Créer les dossiers
```bash
mkdir etl-airflow-project
cd etl-airflow-project
mkdir -p dags scripts data/input data/output logs plugins
```

### Étape 2 : Créer les fichiers obligatoires

- [ ] **dags/etl_excel_pipeline.py**
  - Copier le code du DAG Airflow
  - C'est le workflow principal

- [ ] **scripts/transform_excel.py**
  - Copier le code de transformation
  - C'est la logique métier

- [ ] **docker-compose.yml**
  - Copier la configuration Docker
  - Définit tous les services

- [ ] **Dockerfile**
  - Copier le Dockerfile
  - Build l'image avec les dépendances

- [ ] **requirements.txt**
  - Copier les 3 lignes de dépendances
  - Apache Airflow, Pandas, Openpyxl

- [ ] **start.sh**
  - Copier le script de démarrage
  - Facilite le lancement

### Étape 3 : Fichiers de documentation (optionnels mais recommandés)

- [ ] **DEMARRAGE-RAPIDE.md**
  - Guide ultra-simple pour commencer

- [ ] **README.md**
  - Guide complet et détaillé

- [ ] **PRESENTATION.md**
  - Documentation technique du projet

## 🎯 Ordre de création recommandé

1. **Créer la structure** (dossiers)
2. **Fichiers techniques** (Dockerfile, docker-compose, requirements)
3. **Code Python** (scripts/transform_excel.py)
4. **DAG Airflow** (dags/etl_excel_pipeline.py)
5. **Script démarrage** (start.sh)
6. **Documentation** (les 3 fichiers .md)

## 💾 Taille approximative des fichiers

| Fichier | Lignes | Taille |
|---------|--------|--------|
| etl_excel_pipeline.py | 120 | ~4 KB |
| transform_excel.py | 210 | ~7 KB |
| docker-compose.yml | 90 | ~3 KB |
| Dockerfile | 6 | ~0.2 KB |
| requirements.txt | 3 | ~0.1 KB |
| start.sh | 30 | ~1 KB |
| Documentation (3 fichiers) | 600+ | ~20 KB |

**Total : ~35 KB** (très léger !)

## ⚡ Démarrage après création

```bash
# Rendre le script exécutable
chmod +x start.sh

# Lancer
./start.sh
```

## 🧪 Test rapide

Après le démarrage, testez avec :

```bash
# 1. Créer un fichier Excel de test (ou utilisez le vôtre)
cp /chemin/vers/votre_grand_livre.xlsx data/input/

# 2. Ouvrir Airflow
# http://localhost:8080 (airflow/airflow)

# 3. Activer le DAG "etl_excel_grand_livre"

# 4. Attendre 5 minutes ou lancer manuellement

# 5. Vérifier les résultats
ls -lh data/output/
```

Si vous voyez 2 fichiers (.json et .xlsx), **c'est bon !** ✅