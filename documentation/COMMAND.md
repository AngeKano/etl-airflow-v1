# 📝 Commandes Utiles

## 🚀 Démarrage et Arrêt

### Première installation
```bash
# Rendre les scripts exécutables
chmod +x start.sh test.sh

# Lancer le projet
./start.sh
```

### Démarrage normal
```bash
# Démarrer tous les   services
docker-compose up -d

# Démarrer en mode verbose (voir les logs)
docker-compose up
```

### Arrêt
```bash
# Arrêter tous les services
docker-compose down

# Arrêter ET supprimer les volumes (⚠️ supprime les données!)
docker-compose down -v
```

### Redémarrage
```bash
# Redémarrer tous les services
docker-compose restart

# Redémarrer un service spécifique
docker-compose restart airflow-scheduler
docker-compose restart airflow-webserver
```

## 🔍 Monitoring et Logs

### Voir les logs
```bash
# Logs de tous les services
docker-compose logs

# Logs en temps réel
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs airflow-scheduler
docker-compose logs -f airflow-webserver

# Logs des 50 dernières lignes
docker-compose logs --tail=50 airflow-scheduler
```

### État des conteneurs
```bash
# Voir tous les conteneurs
docker-compose ps

# Voir les ressources utilisées
docker stats
```

## 📊 Gestion des fichiers

### Dépôt de fichiers
```bash
# Copier un fichier dans input
cp /chemin/vers/fichier.xlsx data/input/

# Copier plusieurs fichiers
cp /chemin/vers/*.xlsx data/input/

# Créer un lien symbolique (pour gros fichiers)
ln -s /chemin/vers/fichier.xlsx data/input/fichier.xlsx
```

### Vérification des fichiers
```bash
# Lister les fichiers en attente
ls -lh data/input/*.xlsx

# Lister les fichiers traités
ls -lh data/output/

# Compter les fichiers
ls -1 data/input/*.xlsx 2>/dev/null | wc -l
ls -1 data/output/*.json 2>/dev/null | wc -l

# Voir la taille totale
du -sh data/input/
du -sh data/output/
```

### Nettoyage
```bash
# Nettoyer les fichiers de sortie
rm data/output/*

# Nettoyer les fichiers traités
rm data/input/processed/*

# Nettoyer les logs
rm -rf logs/*
```

## 🧪 Tests et Débogage

### Lancer le test
```bash
# Exécuter le script de test
./test.sh
```

### Tester le script sans Airflow
```bash
# Tester directement la transformation
python scripts/transform_excel.py \
  data/input/mon_fichier.xlsx \
  data/output/
```

### Entrer dans un conteneur
```bash
# Shell dans le webserver
docker-compose exec airflow-webserver bash

# Shell dans le scheduler
docker-compose exec airflow-scheduler bash

# Une fois dans le conteneur:
cd /opt/airflow
ls -la dags/
python scripts/transform_excel.py --help
```

### Vérifier les erreurs Python
```bash
# Vérifier la syntaxe du DAG
docker-compose exec airflow-webserver python /opt/airflow/dags/etl_excel_pipeline.py

# Vérifier la syntaxe du script
docker-compose exec airflow-webserver python /opt/airflow/scripts/transform_excel.py
```

## 🔧 Maintenance

### Reconstruire l'image
```bash
# Après modification du Dockerfile ou requirements.txt
docker-compose build

# Forcer la reconstruction (sans cache)
docker-compose build --no-cache

# Rebuild et redémarrer
docker-compose up -d --build
```

### Réinitialiser complètement
```bash
# Tout supprimer
docker-compose down -v
rm -rf logs/*
rm .env

# Relancer
./start.sh
```

### Mettre à jour les dépendances
```bash
# Modifier requirements.txt puis:
docker-compose build
docker-compose up -d
```

## 📂 Airflow CLI

### Lister les DAGs
```bash
docker-compose exec airflow-webserver airflow dags list
```

### Tester un DAG
```bash
# Tester le DAG sans l'exécuter
docker-compose exec airflow-webserver airflow dags test etl_excel_grand_livre 2025-10-08
```

### Lister les tâches
```bash
docker-compose exec airflow-webserver airflow tasks list etl_excel_grand_livre
```

### Exécuter une tâche manuellement
```bash
docker-compose exec airflow-webserver airflow tasks test \
  etl_excel_grand_livre \
  detect_and_process_files \
  2025-10-08
```

### Pause/Unpause un DAG
```bash
# Mettre en pause
docker-compose exec airflow-webserver airflow dags pause etl_excel_grand_livre

# Réactiver
docker-compose exec airflow-webserver airflow dags unpause etl_excel_grand_livre
```

## 🗄️ Base de données

### Accéder à PostgreSQL
```bash
# Shell PostgreSQL
docker-compose exec postgres psql -U airflow

# Une fois dans psql:
\l                          # Lister les bases
\c airflow                  # Se connecter à la base airflow
\dt                         # Lister les tables
SELECT * FROM dag LIMIT 5;  # Voir les DAGs
\q                          # Quitter
```

### Réinitialiser la base
```bash
docker-compose down -v
docker-compose up airflow-init
docker-compose up -d
```

## 🔐 Sécurité

### Changer le mot de passe admin
```bash
# Créer un nouveau fichier .env
echo "_AIRFLOW_WWW_USER_USERNAME=admin" >> .env
echo "_AIRFLOW_WWW_USER_PASSWORD=nouveau_mot_de_passe" >> .env

# Redémarrer
docker-compose down
docker-compose up airflow-init
docker-compose up -d
```

### Créer un nouvel utilisateur
```bash
docker-compose exec airflow-webserver airflow users create \
  --username nouvel_user \
  --firstname John \
  --lastname Doe \
  --role Admin \
  --email john.doe@example.com \
  --password mot_de_passe
```

## 📊 Analyse des résultats

### Examiner un fichier JSON
```bash
# Afficher joliment
cat data/output/fichier.json | python -m json.tool | less

# Compter les comptes
cat data/output/fichier.json | grep '"Numero_Compte"' | wc -l

# Extraire les numéros de compte
cat data/output/fichier.json | grep '"Numero_Compte"' | cut -d'"' -f4
```

### Statistiques rapides
```bash
# Total des débits (approximatif)
cat data/output/*.json | grep '"Debit"' | grep -v '0.0' | wc -l

# Taille moyenne des fichiers de sortie
du -sh data/output/* | awk '{sum+=$1; count++} END {print sum/count}'
```

## 🌐 Réseau et Ports

### Changer le port Airflow
```bash
# Modifier docker-compose.yml:
# ports:
#   - "9090:8080"  # au lieu de "8080:8080"

docker-compose down
docker-compose up -d
# Airflow accessible sur http://localhost:9090
```

### Vérifier les ports utilisés
```bash
# Voir tous les ports exposés
docker-compose ps --format "table {{.Name}}\t{{.Ports}}"

# Vérifier si le port 8080 est occupé
lsof -i :8080  # Mac/Linux
netstat -ano | findstr :8080  # Windows
```

## 💾 Backup et Restauration

### Sauvegarder les données
```bash
# Sauvegarder tout le dossier data
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# Sauvegarder uniquement output
tar -czf output_backup_$(date +%Y%m%d).tar.gz data/output/
```

### Restaurer
```bash
# Restaurer depuis un backup
tar -xzf backup_20251008.tar.gz
```

## 📈 Performance

### Voir l'utilisation des ressources
```bash
# CPU et mémoire par conteneur
docker stats --no-stream

# Espace disque utilisé
docker system df

# Nettoyer l'espace Docker
docker system prune -a
```

### Optimiser
```bash
# Limiter la mémoire dans docker-compose.yml:
# services:
#   airflow-webserver:
#     mem_limit: 2g
#     cpus: 1.0
```

## 🆘 Commandes de dépannage

### Problèmes courants
```bash
# Problème de permissions
sudo chown -R $(id -u):$(id -g) data/ logs/

# Nettoyer les conteneurs orphelins
docker-compose down --remove-orphans

# Forcer la recréation des conteneurs
docker-compose up -d --force-recreate

# Voir les erreurs détaillées
docker-compose logs --tail=100 | grep -i error

# Réinitialisation totale
docker-compose down -v
docker system prune -a -f
./start.sh
```

## 🎓 Commandes avancées

### Export de la configuration
```bash
# Exporter la config Airflow
docker-compose exec airflow-webserver airflow config list > airflow_config.txt
```

### Modifier la config à la volée
```bash
# Variables d'environnement
docker-compose exec airflow-webserver printenv | grep AIRFLOW
```

### Monitoring avancé
```bash
# Installer ctop (Docker top interactif)
# Puis lancer:
ctop
```

---

## 📚 Références rapides

| Action | Commande |
|--------|----------|
| Démarrer | `./start.sh` ou `docker-compose up -d` |
| Arrêter | `docker-compose down` |
| Logs | `docker-compose logs -f airflow-scheduler` |
| Test | `./test.sh` |
| Reset | `docker-compose down -v && ./start.sh` |
| Interface | http://localhost:8080 |
| Status | `docker-compose ps` |
| Shell | `docker-compose exec airflow-webserver bash` |

---

💡 **Astuce**: Créez des alias dans votre `.bashrc` ou `.zshrc`:

```bash
alias air-start='docker-compose up -d'
alias air-stop='docker-compose down'
alias air-logs='docker-compose logs -f airflow-scheduler'
alias air-test='./test.sh'
alias air-reset='docker-compose down -v && ./start.sh'
```