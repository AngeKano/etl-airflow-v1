"""
DAG Airflow pour le pipeline ETL Grand Livre Comptes
Pipeline simple: détection fichier -> transformation -> génération outputs
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.filesystem import FileSensor
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import shutil
import json

# Ajouter le dossier scripts au path pour importer notre script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from transform_excel import transform_file

# Configuration des chemins
INPUT_DIR = "/opt/airflow/data/input"
OUTPUT_DIR = "/opt/airflow/data/output"
PROCESSED_DIR = "/opt/airflow/data/input/processed"
LOG_DIR = "/opt/airflow/data/input/log"

# Arguments par défaut du DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}


def create_error_report(file_path, error_message, traceback_info=None):
    """
    Crée un rapport d'erreur détaillé en JSON
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = Path(file_path).stem
    
    error_report = {
        "fichier": Path(file_path).name,
        "date_traitement": datetime.now().isoformat(),
        "statut": "ERREUR",
        "erreur": {
            "message": str(error_message),
            "type": type(error_message).__name__,
            "traceback": traceback_info
        },
        "chemin_original": str(file_path),
        "timestamp": timestamp
    }
    
    # Créer le dossier log s'il n'existe pas
    log_path = Path(LOG_DIR)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder le rapport d'erreur
    log_file = log_path / f"resm_{file_name}_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(error_report, f, ensure_ascii=False, indent=2)
    
    return str(log_file)


def move_to_processed(file_path, success=True):
    """
    Déplace un fichier vers le dossier processed
    Ajoute un suffixe _error si le traitement a échoué
    """
    processed_path = Path(PROCESSED_DIR)
    processed_path.mkdir(parents=True, exist_ok=True)
    
    source = Path(file_path)
    
    # Vérifier que le fichier source existe
    if not source.exists():
        raise FileNotFoundError(f"Le fichier source n'existe plus: {source}")
    
    # Ajouter suffixe si erreur
    if not success:
        new_name = f"{source.stem}_error{source.suffix}"
    else:
        new_name = source.name
    
    destination = processed_path / new_name
    
    # Gérer les doublons en ajoutant un numéro
    counter = 1
    while destination.exists():
        if not success:
            new_name = f"{source.stem}_error_{counter}{source.suffix}"
        else:
            new_name = f"{source.stem}_{counter}{source.suffix}"
        destination = processed_path / new_name
        counter += 1
    
    # Déplacer le fichier
    shutil.move(str(source), str(destination))
    
    return str(destination)


def check_and_process_files(**context):
    """
    Vérifie les fichiers Excel dans le dossier input et les traite
    """
    input_path = Path(INPUT_DIR)
    
    # Lister tous les fichiers Excel
    excel_files = list(input_path.glob("*.xlsx")) + list(input_path.glob("*.xls"))
    
    if not excel_files:
        print("ℹ️  Aucun fichier Excel trouvé dans le dossier input")
        return {
            "total_files": 0,
            "success": 0,
            "errors": 0,
            "details": []
        }
    
    print(f"📁 {len(excel_files)} fichier(s) Excel trouvé(s)")
    
    # Statistiques du traitement
    stats = {
        "total_files": len(excel_files),
        "success": 0,
        "errors": 0,
        "details": []
    }
    
    # Traiter chaque fichier
    for excel_file in excel_files:
        print(f"\n{'='*60}")
        print(f"Traitement de: {excel_file.name}")
        print(f"{'='*60}")
        
        file_result = {
            "filename": excel_file.name,
            "status": None,
            "error": None,
            "output_files": [],
            "moved_to": None,
            "log_file": None
        }
        
        # Sauvegarder le chemin original avant traitement
        original_path = str(excel_file)
        file_still_exists = True
        
        try:
            # Vérifier que le fichier existe avant traitement
            if not excel_file.exists():
                raise FileNotFoundError(f"Le fichier {excel_file.name} n'existe pas")
            
            # Transformer le fichier
            json_file, excel_output, log_file = transform_file(original_path, OUTPUT_DIR)
            
            file_result["status"] = "SUCCESS"
            file_result["output_files"] = [json_file, excel_output]
            file_result["log_file"] = log_file
            
            stats["success"] += 1
            print(f"✅ Fichier traité avec succès")
            print(f"   📄 JSON: {json_file}")
            print(f"   📊 Excel: {excel_output}")
            print(f"   📋 Log: {log_file}")
            
        except Exception as e:
            import traceback
            
            file_result["status"] = "ERROR"
            file_result["error"] = str(e)
            
            # Créer un rapport d'erreur détaillé
            traceback_str = traceback.format_exc()
            error_log = create_error_report(original_path, e, traceback_str)
            file_result["log_file"] = error_log
            
            stats["errors"] += 1
            print(f"❌ Erreur lors du traitement: {str(e)}")
            print(f"   📋 Rapport d'erreur: {error_log}")
            print(f"   📝 Traceback sauvegardé dans le rapport")
        
        # DÉPLACEMENT DU FICHIER - Toujours à la fin, succès ou erreur
        try:
            # Vérifier si le fichier existe encore (il peut avoir été déplacé par transform_file)
            if Path(original_path).exists():
                moved_location = move_to_processed(
                    original_path, 
                    success=(file_result["status"] == "SUCCESS")
                )
                file_result["moved_to"] = moved_location
                print(f"📦 Fichier déplacé vers: {moved_location}")
            else:
                # Le fichier a déjà été déplacé ailleurs (par transform_file par exemple)
                file_result["moved_to"] = "ALREADY_MOVED"
                print(f"ℹ️  Fichier déjà déplacé ailleurs")
                
        except Exception as move_error:
            print(f"⚠️  Impossible de déplacer le fichier: {move_error}")
            file_result["moved_to"] = f"MOVE_FAILED: {str(move_error)}"
            
            # Si le fichier existe encore mais n'a pas pu être déplacé, créer un log
            if Path(original_path).exists():
                print(f"⚠️  Le fichier est toujours dans input/: {original_path}")
        
        stats["details"].append(file_result)
        
        # Continuer avec le fichier suivant
        if file_result["status"] == "ERROR":
            print(f"\n⚠️  Erreur capturée, passage au fichier suivant...\n")
    
    # Sauvegarder les statistiques globales
    context['task_instance'].xcom_push(key='processing_stats', value=stats)
    
    return stats


def print_summary(**context):
    """
    Affiche un résumé détaillé des fichiers générés et du traitement
    """
    # Récupérer les statistiques du traitement
    ti = context['task_instance']
    stats = ti.xcom_pull(task_ids='detect_and_process_files', key='processing_stats')
    
    if not stats:
        print("ℹ️  Aucune statistique disponible")
        return
    
    output_path = Path(OUTPUT_DIR)
    log_path = Path(LOG_DIR)
    processed_path = Path(PROCESSED_DIR)
    
    # Compter les fichiers générés
    json_files = list(output_path.glob("*.json"))
    excel_files = list(output_path.glob("*.xlsx"))
    log_files = list(log_path.glob("resm_*.json"))
    processed_files = list(processed_path.glob("*.*")) if processed_path.exists() else []
    
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DÉTAILLÉ DU TRAITEMENT")
    print("="*70)
    
    # Statistiques globales
    print(f"\n📈 STATISTIQUES GLOBALES:")
    print(f"   Total de fichiers traités: {stats['total_files']}")
    print(f"   ✅ Succès: {stats['success']}")
    print(f"   ❌ Erreurs: {stats['errors']}")
    
    if stats['total_files'] > 0:
        success_rate = (stats['success'] / stats['total_files']) * 100
        print(f"   📊 Taux de succès: {success_rate:.1f}%")
    
    # Détails par fichier
    print(f"\n📋 DÉTAILS PAR FICHIER:")
    for detail in stats['details']:
        status_icon = "✅" if detail['status'] == "SUCCESS" else "❌"
        print(f"\n   {status_icon} {detail['filename']}")
        print(f"      Statut: {detail['status']}")
        
        if detail['status'] == "SUCCESS":
            print(f"      Sorties générées: {len(detail['output_files'])}")
        else:
            error_msg = detail['error'][:100]
            print(f"      Erreur: {error_msg}{'...' if len(detail['error']) > 100 else ''}")
        
        if detail['log_file']:
            print(f"      Log: {Path(detail['log_file']).name}")
        
        if detail['moved_to']:
            if detail['moved_to'] == "ALREADY_MOVED":
                print(f"      ℹ️  Fichier déjà déplacé")
            elif detail['moved_to'].startswith("MOVE_FAILED"):
                print(f"      ⚠️  Échec déplacement: {detail['moved_to']}")
            else:
                print(f"      Déplacé vers: {Path(detail['moved_to']).name}")
    
    # Fichiers dans output
    print(f"\n📂 FICHIERS GÉNÉRÉS DANS output/ ({len(json_files) + len(excel_files)}):")
    for f in sorted(list(output_path.glob("*.*")))[:10]:  # Limiter à 10 pour lisibilité
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            print(f"   - {f.name} ({size_kb:.1f} KB)")
    if len(json_files) + len(excel_files) > 10:
        print(f"   ... et {len(json_files) + len(excel_files) - 10} autre(s)")
    
    # Fichiers de log
    if log_files:
        print(f"\n📋 RAPPORTS DE TRAITEMENT ({len(log_files)}):")
        for f in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"   - {f.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        if len(log_files) > 5:
            print(f"   ... et {len(log_files) - 5} autre(s)")
    
    # Fichiers traités
    if processed_files:
        print(f"\n📦 FICHIERS DANS processed/ ({len(processed_files)}):")
        error_files = [f for f in processed_files if '_error' in f.name]
        success_files = [f for f in processed_files if '_error' not in f.name]
        
        if success_files:
            print(f"   ✅ Succès: {len(success_files)}")
        if error_files:
            print(f"   ❌ Erreurs: {len(error_files)}")
            for f in sorted(error_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
                print(f"      - {f.name}")
    
    print("\n" + "="*70 + "\n")


# Définition du DAG
with DAG(
    'etl_excel_grand_livre',
    default_args=default_args,
    description='Pipeline ETL pour fichiers Grand Livre Comptes',
    schedule_interval='*/1 * * * *',  # Toutes les 1 minutes
    catchup=False,
    tags=['etl', 'excel', 'comptabilité'],
) as dag:
    
    # Tâche 1: Vérifier la présence de fichiers Excel et les traiter
    detect_files = PythonOperator(
        task_id='detect_and_process_files',
        python_callable=check_and_process_files,
        provide_context=True,
    )
    
    # Tâche 2: Afficher le résumé détaillé
    show_summary = PythonOperator(
        task_id='show_summary',
        python_callable=print_summary,
        provide_context=True,
    )
    
    # Définir l'ordre d'exécution
    detect_files >> show_summary