#!/bin/bash

echo "🧪 Script de test du pipeline ETL"
echo "=================================="
echo ""

# Vérifier que Docker est lancé
echo "1️⃣  Vérification de Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker n'est pas démarré. Lancez Docker Desktop."
    exit 1
fi
echo "✅ Docker est actif"
echo ""

# Vérifier que les conteneurs sont lancés
echo "2️⃣  Vérification des conteneurs..."
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Les conteneurs ne sont pas démarrés. Lancez: ./start.sh"
    exit 1
fi
echo "✅ Les conteneurs sont actifs"
echo ""

# Vérifier l'accès à Airflow
echo "3️⃣  Vérification de l'interface Airflow..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health | grep -q "200"; then
    echo "✅ Airflow est accessible sur http://localhost:8080"
else
    echo "⚠️  Airflow ne répond pas encore (normal si vient de démarrer)"
    echo "   Attendez 30 secondes et réessayez"
fi
echo ""

# Vérifier la structure des dossiers
echo "4️⃣  Vérification de la structure..."
if [ -d "dags" ] && [ -d "scripts" ] && [ -d "data/input" ] && [ -d "data/output" ]; then
    echo "✅ Tous les dossiers sont présents"
else
    echo "❌ Il manque des dossiers. Structure attendue:"
    echo "   dags/ scripts/ data/input/ data/output/"
    exit 1
fi
echo ""

# Vérifier les fichiers essentiels
echo "5️⃣  Vérification des fichiers..."
MISSING=0
if [ ! -f "dags/etl_excel_pipeline.py" ]; then
    echo "❌ Manque: dags/etl_excel_pipeline.py"
    MISSING=1
fi
if [ ! -f "scripts/transform_excel.py" ]; then
    echo "❌ Manque: scripts/transform_excel.py"
    MISSING=1
fi
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Manque: docker-compose.yml"
    MISSING=1
fi

if [ $MISSING -eq 0 ]; then
    echo "✅ Tous les fichiers essentiels sont présents"
else
    echo "❌ Il manque des fichiers essentiels"
    exit 1
fi
echo ""

# Compter les fichiers dans input et output
echo "6️⃣  État des dossiers de données..."
INPUT_COUNT=$(ls -1 data/input/*.xlsx 2>/dev/null | wc -l | tr -d ' ')
OUTPUT_JSON_COUNT=$(ls -1 data/output/*.json 2>/dev/null | wc -l | tr -d ' ')
OUTPUT_EXCEL_COUNT=$(ls -1 data/output/*.xlsx 2>/dev/null | wc -l | tr -d ' ')

echo "   📂 Fichiers dans input/: $INPUT_COUNT fichier(s) .xlsx"
echo "   📥 Fichiers dans output/: $OUTPUT_JSON_COUNT .json + $OUTPUT_EXCEL_COUNT .xlsx"
echo ""

# Vérifier les logs du scheduler
echo "7️⃣  Vérification des logs (5 dernières lignes)..."
echo "─────────────────────────────────────────────"
docker-compose logs --tail=5 airflow-scheduler 2>/dev/null | grep -v "^$"
echo "─────────────────────────────────────────────"
echo ""

# Résumé final
echo "══════════════════════════════════════════════"
echo "📊 RÉSUMÉ DES TESTS"
echo "══════════════════════════════════════════════"
echo "✅ Docker: OK"
echo "✅ Conteneurs: OK"
echo "✅ Structure: OK"
echo "✅ Fichiers: OK"
echo ""
echo "🎯 Prochaines étapes:"
echo "   1. Ouvrir http://localhost:8080 (airflow/airflow)"
echo "   2. Activer le DAG 'etl_excel_grand_livre'"
echo "   3. Déposer un fichier Excel dans data/input/"
echo "   4. Attendre 5 minutes (ou lancer manuellement)"
echo "   5. Vérifier les résultats dans data/output/"
echo ""
echo "📚 Aide: cat DEMARRAGE-RAPIDE.md"
echo "══════════════════════════════════════════════"