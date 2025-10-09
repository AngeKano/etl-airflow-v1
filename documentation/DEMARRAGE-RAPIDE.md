# 🚀 Démarrage Rapide

## En 3 commandes

### 1. Créer le projet

```bash
# Créer la structure
mkdir etl-airflow-project && cd etl-airflow-project
mkdir -p dags scripts data/input data/output logs plugins
```

### 2. Copier les fichiers

Placez ces fichiers dans le projet :

```
etl-airflow-project/
├── dags/etl_excel_pipeline.py
├── scripts/transform_excel.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── start.sh
```

### 3. Lancer

```bash
# Rendre le script exécutable
chmod +x start.sh

# Démarrer tout
./start.sh
```

**C'est tout !** 🎉

---

## Utilisation

### Accéder à Airflow
Ouvrez http://localhost:8080
- Username: `airflow`
- Password: `airflow`

### Traiter un fichier
```bash
# Copier votre fichier Excel
cp mon_fichier.xlsx data/input/

# Attendre 5 minutes (ou lancer manuellement dans Airflow)
# Les résultats apparaissent dans data/output/
```

### Voir ce qui se passe
```bash
# Logs en direct
docker-compose logs -f airflow-scheduler
```

### Arrêter
```bash
docker-compose down
```

---

## Fichiers générés

Pour chaque fichier Excel traité, vous obtenez dans `data/output/` :

- ✅ **`fichier_20251008.json`** → Structure complète des comptes et transactions
- ✅ **`fichier_20251008.xlsx`** → Tableau Excel avec toutes les transactions

---

## Si ça ne marche pas

### Docker n'est pas démarré
```bash
# Lancer Docker Desktop (sur Mac/Windows)
# Ou Docker daemon (sur Linux)
sudo systemctl start docker
```

### Le DAG n'apparaît pas
```bash
# Attendre 1-2 minutes
# Puis vérifier les logs
docker-compose logs airflow-scheduler
```

### Permissions refusées
```bash
# Recréer l'environnement
docker-compose down -v
rm .env
./start.sh
```

---

## Pour aller plus loin

Consultez **README.md** pour :
- Modifier la fréquence d'exécution
- Comprendre le fonctionnement détaillé
- Dépannage avancé

Consultez **PRESENTATION.md** pour :
- Architecture complète
- Format des données
- Évolutions possibles