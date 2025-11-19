"""
DAG Airflow pour le pipeline ETL multi-fichiers comptables
Pipeline: lecture de sous-dossiers typés → transformation appropriée → génération outputs
Support des traitements à 2 fichiers (gl_tiers nécessite plan_tiers + gl_tiers)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import shutil
import json

# Ajouter le dossier scripts au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Import des fonctions de transformation
from scripts.gl_comptable import transform_file as transform_gl_comptable
from scripts.code_journal import transform_file as transform_code_journal
from scripts.gl_tiers import transform_file as transform_gl_tiers
from scripts.plan_comptable import transform_file as transform_plan_comptable
from scripts.fusion_gl import transform_file as transform_fusion_gl

# Configuration des chemins
INPUT_DIR = "/opt/airflow/data/input"
OUTPUT_DIR = "/opt/airflow/data/output"
PROCESSED_DIR = "/opt/airflow/data/processed"
LOG_DIR = "/opt/airflow/data/log"

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

# Mapping des dossiers vers les fonctions et types
# Type 'single' = 1 fichier suffit
# Type 'paired' = nécessite 2 fichiers (source + référence)
FOLDER_TYPE_MAPPING = {
    'gl_compte': {
        'transform': transform_gl_comptable,
        'type': 'GRAND_LIVRE_COMPTES',
        'mode': 'single'
    },
    'code_journal': {
        'transform': transform_code_journal,
        'type': 'CODE_JOURNAL',
        'mode': 'single'
    },
    'gl_tiers': {
        'transform': transform_gl_tiers,
        'type': 'GRAND_LIVRE_TIERS',
        'mode': 'paired',
        'reference_folder': 'plan_tiers'  # Dossier contenant le fichier de référence
    },
    'plan_comptable': {
        'transform': transform_plan_comptable,
        'type': 'PLAN_COMPTABLE',
        'mode': 'single'
    }
}


def create_error_report(file_path, error_message, file_type, traceback_info=None):
    """
    Crée un rapport d'erreur détaillé en JSON
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = Path(file_path).stem

    error_report = {
        "fichier": Path(file_path).name,
        "type_fichier": file_type,
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

    log_path = Path(LOG_DIR)
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / f"error_{file_type}_{file_name}_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(error_report, f, ensure_ascii=False, indent=2)

    return str(log_file)


def move_to_processed(file_path, file_type, success=True):
    """
    Déplace un fichier vers processed/{type}/
    """
    processed_path = Path(PROCESSED_DIR) / file_type
    processed_path.mkdir(parents=True, exist_ok=True)

    source = Path(file_path)

    if not source.exists():
        raise FileNotFoundError(f"Le fichier source n'existe plus: {source}")

    if not success:
        new_name = f"{source.stem}_error{source.suffix}"
    else:
        new_name = source.name

    destination = processed_path / new_name

    counter = 1
    while destination.exists():
        if not success:
            new_name = f"{source.stem}_error_{counter}{source.suffix}"
        else:
            new_name = f"{source.stem}_{counter}{source.suffix}"
        destination = processed_path / new_name
        counter += 1

    shutil.move(str(source), str(destination))

    return str(destination)


def find_reference_file(reference_folder_path):
    """
    Trouve le fichier de référence (plan_tiers) dans le dossier
    Retourne le premier fichier Excel trouvé
    """
    excel_files = list(reference_folder_path.glob("*.xlsx")) + list(reference_folder_path.glob("*.xls"))

    if not excel_files:
        return None

    # Retourner le premier fichier (ou le plus récent)
    return sorted(excel_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]


def check_and_process_files(**context):
    """
    Parcourt les sous-dossiers typés et traite les fichiers
    Support des traitements 'single' et 'paired'
    """
    input_path = Path(INPUT_DIR)

    stats = {
        "total_files": 0,
        "success": 0,
        "errors": 0,
        "skipped": 0,
        "details": []
    }

    # Parcourir chaque dossier typé
    for folder_name, config in FOLDER_TYPE_MAPPING.items():
        folder_path = input_path / folder_name

        if not folder_path.exists():
            print(f"⚠️  Dossier {folder_name}/ n'existe pas, création...")
            folder_path.mkdir(parents=True, exist_ok=True)
            continue

        file_type = config['type']
        transform_func = config['transform']
        mode = config.get('mode', 'single')

        # Lister les fichiers Excel dans ce dossier
        excel_files = list(folder_path.glob("*.xlsx")) + list(folder_path.glob("*.xls"))

        if not excel_files:
            print(f"ℹ️  Aucun fichier dans {folder_name}/")
            continue

        print(f"\n{'='*70}")
        print(f"📁 DOSSIER: {folder_name}/ ({len(excel_files)} fichier(s)) - Mode: {mode.upper()}")
        print(f"{'='*70}")

        stats["total_files"] += len(excel_files)

        # Si mode 'paired', vérifier le fichier de référence
        reference_file = None
        if mode == 'paired':
            reference_folder = config.get('reference_folder')
            if not reference_folder:
                print(f"❌ Configuration erreur: 'reference_folder' manquant pour {folder_name}")
                continue

            reference_folder_path = input_path / reference_folder

            if not reference_folder_path.exists():
                print(f"⚠️  Dossier de référence {reference_folder}/ n'existe pas")
                print(f"   Les fichiers de {folder_name}/ seront ignorés")
                stats["skipped"] += len(excel_files)
                for excel_file in excel_files:
                    stats["details"].append({
                        "filename": excel_file.name,
                        "folder": folder_name,
                        "file_type": file_type,
                        "status": "SKIPPED",
                        "error": f"Dossier de référence {reference_folder}/ introuvable",
                        "output_files": [],
                        "moved_to": None,
                        "log_file": None
                    })
                continue

            reference_file = find_reference_file(reference_folder_path)

            if not reference_file:
                print(f"⚠️  Aucun fichier de référence dans {reference_folder}/")
                print(f"   Les fichiers de {folder_name}/ seront ignorés")
                stats["skipped"] += len(excel_files)
                for excel_file in excel_files:
                    stats["details"].append({
                        "filename": excel_file.name,
                        "folder": folder_name,
                        "file_type": file_type,
                        "status": "SKIPPED",
                        "error": f"Aucun fichier de référence dans {reference_folder}/",
                        "output_files": [],
                        "moved_to": None,
                        "log_file": None
                    })
                continue

            print(f"📋 Fichier de référence: {reference_file.name}")

        # Traiter chaque fichier
        for excel_file in excel_files:
            print(f"\n{'─'*60}")
            print(f"Traitement: {excel_file.name}")
            print(f"Type: {file_type}")
            if mode == 'paired' and reference_file:
                print(f"Référence: {reference_file.name}")
            print(f"{'─'*60}")

            file_result = {
                "filename": excel_file.name,
                "folder": folder_name,
                "file_type": file_type,
                "mode": mode,
                "reference_file": reference_file.name if reference_file else None,
                "status": None,
                "error": None,
                "output_files": [],
                "moved_to": None,
                "log_file": None
            }

            original_path = str(excel_file)

            try:
                if not excel_file.exists():
                    raise FileNotFoundError(f"Le fichier {excel_file.name} n'existe pas")

                # Appeler la fonction de transformation selon le mode
                if mode == 'single':
                    # Créer le sous-dossier typé dans output
                    typed_output_dir = Path(OUTPUT_DIR) / file_type
                    typed_output_dir.mkdir(parents=True, exist_ok=True)

                    json_file, excel_output, log_file = transform_func(original_path, str(typed_output_dir))
                elif mode == 'paired':
                    # Créer le sous-dossier typé dans output
                    typed_output_dir = Path(OUTPUT_DIR) / file_type
                    typed_output_dir.mkdir(parents=True, exist_ok=True)

                    # Passer 2 fichiers: grand_livre + plan_tiers
                    json_file, excel_output, log_file = transform_func(
                        original_path,      # Grand Livre Tiers
                        str(reference_file), # Plan Tiers
                        str(typed_output_dir)
                    )
                else:
                    raise ValueError(f"Mode inconnu: {mode}")

                file_result["status"] = "SUCCESS"
                file_result["output_files"] = [json_file, excel_output] if excel_output else [json_file]
                file_result["log_file"] = log_file

                stats["success"] += 1
                print(f"✅ Traité avec succès")
                print(f"   📄 JSON: {json_file}")
                if excel_output:
                    print(f"   📊 Excel: {excel_output}")
                print(f"   📋 Log: {log_file}")

            except Exception as e:
                import traceback

                file_result["status"] = "ERROR"
                file_result["error"] = str(e)

                traceback_str = traceback.format_exc()
                error_log = create_error_report(original_path, e, file_type, traceback_str)
                file_result["log_file"] = error_log

                stats["errors"] += 1
                print(f"❌ Erreur: {str(e)}")
                print(f"   📋 Rapport: {error_log}")

            # Déplacer le fichier
            try:
                if Path(original_path).exists():
                    moved_location = move_to_processed(
                        original_path,
                        file_type,
                        success=(file_result["status"] == "SUCCESS")
                    )
                    file_result["moved_to"] = moved_location
                    print(f"📦 Déplacé vers: {moved_location}")
                else:
                    file_result["moved_to"] = "ALREADY_MOVED"

            except Exception as move_error:
                print(f"⚠️  Échec déplacement: {move_error}")
                file_result["moved_to"] = f"MOVE_FAILED: {str(move_error)}"

            stats["details"].append(file_result)

    if stats["total_files"] == 0:
        print("\nℹ️  Aucun fichier à traiter dans tous les dossiers")

    context['task_instance'].xcom_push(key='processing_stats', value=stats)

    return stats


def print_summary(**context):
    """
    Affiche un résumé détaillé par dossier/type
    """
    ti = context['task_instance']
    stats = ti.xcom_pull(task_ids='detect_and_process_files', key='processing_stats')

    if not stats:
        print("ℹ️  Aucune statistique disponible")
        return

    output_path = Path(OUTPUT_DIR)
    log_path = Path(LOG_DIR)

    json_files = list(output_path.glob("*.json"))
    excel_files = list(output_path.glob("*.xlsx"))
    log_files = list(log_path.glob("*.json"))

    print("\n" + "="*70)
    print("📊 RÉSUMÉ DÉTAILLÉ DU TRAITEMENT")
    print("="*70)

    print(f"\n📈 STATISTIQUES GLOBALES:")
    print(f"   Total fichiers: {stats['total_files']}")
    print(f"   ✅ Succès: {stats['success']}")
    print(f"   ❌ Erreurs: {stats['errors']}")
    print(f"   ⏭️  Ignorés: {stats['skipped']}")

    if stats['total_files'] > 0:
        success_rate = (stats['success'] / stats['total_files']) * 100
        print(f"   📊 Taux de succès: {success_rate:.1f}%")

    # Grouper par dossier
    by_folder = {}
    for detail in stats['details']:
        folder = detail.get('folder', 'UNKNOWN')
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(detail)

    print(f"\n📋 DÉTAILS PAR DOSSIER:")
    for folder, files in by_folder.items():
        success_count = sum(1 for f in files if f['status'] == 'SUCCESS')
        error_count = sum(1 for f in files if f['status'] == 'ERROR')
        skipped_count = sum(1 for f in files if f['status'] == 'SKIPPED')

        mode = files[0].get('mode', 'single')
        reference = files[0].get('reference_file', '')

        print(f"\n   📁 {folder}/ ({files[0]['file_type']}) - Mode: {mode.upper()}")
        if mode == 'paired' and reference:
            print(f"      📋 Référence: {reference}")
        print(f"      Total: {len(files)} | ✅ {success_count} | ❌ {error_count} | ⏭️  {skipped_count}")

        for detail in files:
            if detail['status'] == "SUCCESS":
                status_icon = "✅"
            elif detail['status'] == "ERROR":
                status_icon = "❌"
            else:
                status_icon = "⏭️"

            print(f"      {status_icon} {detail['filename']}")
            if detail['status'] in ["ERROR", "SKIPPED"]:
                error_msg = detail.get('error', 'Erreur inconnue')[:60]
                print(f"         {error_msg}...")

    print(f"\n📂 FICHIERS GÉNÉRÉS ({len(json_files) + len(excel_files)}):")
    for f in sorted(list(output_path.glob("*.*")))[:10]:
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            print(f"   - {f.name} ({size_kb:.1f} KB)")
    if len(json_files) + len(excel_files) > 10:
        print(f"   ... +{len(json_files) + len(excel_files) - 10} autre(s)")

    # Processed par type
    processed_path = Path(PROCESSED_DIR)
    if processed_path.exists():
        print(f"\n📦 FICHIERS TRAITÉS (processed/):")
        for folder_name in FOLDER_TYPE_MAPPING.keys():
            type_folder = processed_path / FOLDER_TYPE_MAPPING[folder_name]['type']
            if type_folder.exists():
                files = list(type_folder.glob("*.*"))
                success_files = [f for f in files if '_error' not in f.name]
                error_files = [f for f in files if '_error' in f.name]

                if files:
                    print(f"   {folder_name}/ : ✅ {len(success_files)} | ❌ {len(error_files)}")

    print("\n" + "="*70 + "\n")


def fusion_grand_livres(**context):
    """
    Fusionne les fichiers EXCEL Grand Livre Comptes + Grand Livre Tiers
    Cherche dans les sous-dossiers typés: output/GRAND_LIVRE_COMPTES/ et output/GRAND_LIVRE_TIERS/
    """
    output_path = Path(OUTPUT_DIR)

    print("\n" + "="*70)
    print("🔗 FUSION GRAND LIVRE COMPTES + TIERS")
    print("="*70)

    # Dossiers typés
    gl_comptes_dir = output_path / "GRAND_LIVRE_COMPTES"
    gl_tiers_dir = output_path / "GRAND_LIVRE_TIERS"

    # Chercher les fichiers EXCEL les plus récents dans chaque dossier typé
    gl_comptes_files = []
    if gl_comptes_dir.exists():
        gl_comptes_files = sorted(
            list(gl_comptes_dir.glob("*.xlsx")),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

    gl_tiers_files = []
    if gl_tiers_dir.exists():
        gl_tiers_files = sorted(
            list(gl_tiers_dir.glob("*.xlsx")),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

    if not gl_comptes_files:
        print(f"⚠️  Aucun fichier Excel dans {gl_comptes_dir}")
        print("   La fusion est ignorée")
        return {"status": "SKIPPED", "reason": "Aucun GL Comptes Excel"}

    if not gl_tiers_files:
        print(f"⚠️  Aucun fichier Excel dans {gl_tiers_dir}")
        print("   La fusion est ignorée")
        return {"status": "SKIPPED", "reason": "Aucun GL Tiers Excel"}

    gl_comptes_file = gl_comptes_files[0]
    gl_tiers_file = gl_tiers_files[0]

    print(f"\n📁 Fichiers Excel sélectionnés:")
    print(f"   GL Comptes: {gl_comptes_file.name} (depuis GRAND_LIVRE_COMPTES/)")
    print(f"   GL Tiers:   {gl_tiers_file.name} (depuis GRAND_LIVRE_TIERS/)")

    try:
        # Créer le sous-dossier pour la fusion
        fusion_output_dir = output_path / "FUSION_GRAND_LIVRE"
        fusion_output_dir.mkdir(parents=True, exist_ok=True)

        # Appeler la fonction de fusion avec fichiers Excel
        json_file, excel_file, log_file = transform_fusion_gl(
            str(gl_comptes_file),
            str(gl_tiers_file),
            str(fusion_output_dir)
        )

        print(f"\n✅ Fusion réussie")

        return {
            "status": "SUCCESS",
            "gl_comptes": gl_comptes_file.name,
            "gl_tiers": gl_tiers_file.name,
            "output_json": json_file,
            "output_excel": excel_file,
            "log_file": log_file
        }

    except Exception as e:
        import traceback
        print(f"\n❌ Erreur lors de la fusion: {str(e)}")
        print(traceback.format_exc())

        return {
            "status": "ERROR",
            "error": str(e)
        }


# Définition du DAG
with DAG(
    'etl_excel_comptable_folders',
    default_args=default_args,
    description='Pipeline ETL avec dossiers typés (gl_compte, code_journal, gl_tiers, plan_comptable) + Fusion GL',
    schedule_interval='*/1 * * * *',
    catchup=False,
    tags=['etl', 'excel', 'comptabilité', 'folders', 'fusion'],
) as dag:

    detect_files = PythonOperator(
        task_id='detect_and_process_files',
        python_callable=check_and_process_files,
        provide_context=True,
    )

    show_summary = PythonOperator(
        task_id='show_summary',
        python_callable=print_summary,
        provide_context=True,
    )

    fusion_gl = PythonOperator(
        task_id='fusion_grand_livres',
        python_callable=fusion_grand_livres,
        provide_context=True,
    )

    # Workflow: Traitement fichiers → Résumé → Fusion GL
    detect_files >> show_summary >> fusion_gl