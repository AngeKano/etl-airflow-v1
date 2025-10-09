#!/bin/bash

echo "🚀 Démarrage du pipeline ETL Airflow..."
echo ""

# Créer le fichier .env avec l'UID
echo "📝 Configuration de l'environnement..."
echo "AIRFLOW_UID=$(id -u)" > .env

# Construire l'image Docker
echo ""
echo "🔨 Construction de l'image Docker..."
docker-compose build

# Initialiser Airflow
echo ""
echo "🔧 Initialisation d'Airflow..."
docker-compose up airflow-init

# Démarrer tous les services
echo ""
echo "▶️  Démarrage des services..."
docker-compose up -d

echo ""
echo "✅ Pipeline ETL démarré avec succès!"
echo ""
echo "📊 Interface Airflow: http://localhost:8080"
echo "   Username: airflow"
echo "   Password: airflow"
echo ""
echo "📂 Déposez vos fichiers Excel dans: ./data/input/"
echo "📥 Récupérez les résultats dans: ./data/output/"
echo ""
echo "Pour voir les logs: docker-compose logs -f airflow-scheduler"
echo "Pour arrêter: docker-compose down"