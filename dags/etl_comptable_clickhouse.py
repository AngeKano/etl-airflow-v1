from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path
import boto3
import pandas as pd
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from scripts.clickhouse_manager import ClickHouseManager

default_args = {
    'owner': 'envol',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# ====================================
# VALEURS DE TEST (commentées)
# ====================================
# CLIENT_ID_TEST = "cmhyjxmyw0004m9fs00s3tck0"
# BATCH_ID_TEST = "f3b12858-3478-4be1-ae2c-2e46a76d08a3"
# S3_PREFIX_TEST = "NEVO_cmhyjxmyw0004m9fs00s3tck0/declaration/2016/periode-20161227-20251114/"
#
# Pour tester rapidement, décommentez ces lignes dans download_files_from_s3:
# client_id = CLIENT_ID_TEST
# s3_prefix = S3_PREFIX_TEST
# batch_id = BATCH_ID_TEST
# ====================================


def download_files_from_s3(**context):
    """
    Télécharge les 5 fichiers depuis S3 avec la structure:
    {clientId}/declaration/{year}/periode-{start}-{end}/{TYPE}/file.xlsx
    """
    params = context['dag_run'].conf or {}
    
    # Récupérer les paramètres (ou utiliser les valeurs de test)
    client_id = params.get('client_id')
    batch_id = params.get('batch_id')
    s3_prefix = params.get('s3_prefix')
    
    # client_id = "cmhyjxmyw0004m9fs00s3tck0"
    # batch_id = "f3b12858-3478-4be1-ae2c-2e46a76d08a3"
    # s3_prefix = "NEVO_cmhyjxmyw0004m9fs00s3tck0/declaration/2016/periode-20161227-20251114/"

    if not client_id or not s3_prefix:
        raise ValueError("Paramètres manquants: client_id et s3_prefix requis")
    
    print("\n" + "="*70)
    print("📥 TÉLÉCHARGEMENT DEPUIS S3")
    print("="*70)
    print(f"Client ID: {client_id}")
    print(f"Batch ID: {batch_id}")
    print(f"Préfixe S3: {s3_prefix}")
    print("="*70)
    # Initialiser le client S3 boto3
    s3_client = boto3.client('s3')
    bucket = os.getenv('S3_BUCKET_NAME', 'repfi-dev')
    local_dir = f"/tmp/etl_{client_id}_{batch_id or context['run_id']}"
    Path(local_dir).mkdir(parents=True, exist_ok=True)
    
    files = {
        'plan_comptes': None,
        'code_journal': None,
        'plan_tiers': None,
        'grand_livre_comptes': None,
        'grand_livre_tiers': None
    }
    
    # Lister tous les fichiers sous ce préfixe
    print(f"\n🔍 Scan du bucket: s3://{bucket}/{s3_prefix}")
    
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=s3_prefix)
        
        if 'Contents' not in response:
            raise ValueError(f"Aucun fichier trouvé dans s3://{bucket}/{s3_prefix}")
        
        total_files = len(response.get('Contents', []))
        print(f"📦 {total_files} objet(s) trouvé(s) dans S3")
        
    except Exception as e:
        print(f"❌ Erreur lors du listing S3: {e}")
        raise
    
    downloaded_count = 0
    
    for obj in response.get('Contents', []):
        key = obj['Key']
        
        # Ignorer les dossiers (clés se terminant par /)
        if key.endswith('/'):
            continue
        
        filename = key.split('/')[-1]
        
        # Ignorer les fichiers cachés ou système
        if filename.startswith('.'):
            continue
        
        # Identifier le type de fichier en regardant le dossier parent
        key_parts = key.split('/')
        parent_folder = key_parts[-2] if len(key_parts) > 1 else ''
        
        # Créer le chemin local avec sous-dossier typé
        type_local_dir = os.path.join(local_dir, parent_folder)
        Path(type_local_dir).mkdir(parents=True, exist_ok=True)
        
        local_path = os.path.join(type_local_dir, filename)
        
        try:
            print(f"\n📥 Téléchargement: {filename}")
            print(f"   Type: {parent_folder}")
            print(f"   S3: s3://{bucket}/{key}")
            
            s3_client.download_file(bucket, key, local_path)
            
            file_size = os.path.getsize(local_path) / 1024  # KB
            print(f"   ✅ Téléchargé: {file_size:.1f} KB")
            
            downloaded_count += 1
            
            # Mapper le type de fichier
            parent_upper = parent_folder.upper()
            if parent_upper == 'PLAN_COMPTES':
                files['plan_comptes'] = local_path
            elif parent_upper == 'CODE_JOURNAL':
                files['code_journal'] = local_path
            elif parent_upper == 'PLAN_TIERS':
                files['plan_tiers'] = local_path
            elif parent_upper == 'GRAND_LIVRE_COMPTES':
                files['grand_livre_comptes'] = local_path
            elif parent_upper == 'GRAND_LIVRE_TIERS':
                files['grand_livre_tiers'] = local_path
            else:
                print(f"   ⚠️  Type de dossier inconnu: {parent_folder}")
                
        except Exception as e:
            print(f"   ❌ Erreur téléchargement: {e}")
            raise
    
    print(f"\n" + "="*70)
    print(f"✅ TÉLÉCHARGEMENT TERMINÉ: {downloaded_count} fichier(s)")
    print("="*70)
    
    # Vérifier que tous les fichiers sont présents
    missing = [k for k, v in files.items() if v is None]
    if missing:
        print(f"\n⚠️  FICHIERS MANQUANTS: {', '.join(missing)}")
        print("Fichiers trouvés:")
        for k, v in files.items():
            status = "✅" if v else "❌"
            print(f"  {status} {k}: {v or 'NON TROUVÉ'}")
    else:
        print("\n✅ TOUS LES FICHIERS SONT PRÉSENTS")
        for k, v in files.items():
            print(f"  ✅ {k}: {Path(v).name}")
    
    # Stocker dans XCom
    context['ti'].xcom_push(key='files', value=files)
    context['ti'].xcom_push(key='local_dir', value=local_dir)
    context['ti'].xcom_push(key='client_id', value=client_id)
    context['ti'].xcom_push(key='batch_id', value=batch_id)
    
    return files


def process_plan_compte(**context):
    """Traiter Plan Compte → ClickHouse"""
    ti = context['ti']
    client_id = ti.xcom_pull(task_ids='download_files', key='client_id')
    files = ti.xcom_pull(task_ids='download_files', key='files')
    
    file_path = files.get('plan_comptes') if files else None

    if not file_path:
        print("⚠️ Plan Compte non trouvé")
        return
    
    print("\n" + "="*70)
    print("📊 TRAITEMENT PLAN COMPTE")
    print("="*70)
    print(f"Client: {client_id}")
    print(f"Fichier: {Path(file_path).name}")

    try:
        df = pd.read_excel(file_path)
        print(f"Lignes lues: {len(df)}")
    except Exception as e:
        print(f"❌ Erreur de lecture du fichier Plan Compte : {e}")
        raise

    # Adapter à la casse éventuelle des colonnes
    cols = {c.lower(): c for c in df.columns}
    data = []
    for _, row in df.iterrows():
        data.append((
            str(row.get(cols.get('compte', 'Compte'), '')),
            str(row.get(cols.get('type', 'Type'), '')),
            str(row.get(cols.get('intitule_compte', 'Intitule_compte'), '')),
            str(row.get(cols.get('nature_compte', 'Nature_compte'), ''))
        ))

    # Insérer dans ClickHouse
    ch = ClickHouseManager()
    ch.create_client_database(client_id)
    ch.upsert_dimension(client_id, 'plan_compte', data)

    print(f"✅ Plan Compte: {len(data)} lignes insérées dans ClickHouse")


def process_code_journal(**context):
    """Traiter Code Journal → ClickHouse"""
    ti = context['ti']
    client_id = ti.xcom_pull(task_ids='download_files', key='client_id')
    files = ti.xcom_pull(task_ids='download_files', key='files')
    
    file_path = files.get('code_journal') if files else None

    if not file_path:
        print("⚠️ Code Journal non trouvé")
        return
    
    print("\n" + "="*70)
    print("📊 TRAITEMENT CODE JOURNAL")
    print("="*70)
    print(f"Client: {client_id}")
    print(f"Fichier: {Path(file_path).name}")

    try:
        df = pd.read_excel(file_path)
        print(f"Lignes lues: {len(df)}")
    except Exception as e:
        print(f"❌ Erreur de lecture du fichier Code Journal : {e}")
        raise

    cols = {c.lower(): c for c in df.columns}
    data = []
    for _, row in df.iterrows():
        code = row.get(cols.get('code', 'Code'), '') or row.get(cols.get('code_journal', 'Code_Journal'), '')
        data.append((
            str(code),
            str(row.get(cols.get('intitule', 'Intitule'), '')),
            str(row.get(cols.get('type', 'Type'), ''))
        ))

    ch = ClickHouseManager()
    ch.upsert_dimension(client_id, 'code_journal', data)

    print(f"✅ Code Journal: {len(data)} lignes insérées dans ClickHouse")


def process_plan_tiers(**context):
    """Traiter Plan Tiers → ClickHouse"""
    ti = context['ti']
    client_id = ti.xcom_pull(task_ids='download_files', key='client_id')
    files = ti.xcom_pull(task_ids='download_files', key='files')
    
    file_path = files.get('plan_tiers') if files else None

    if not file_path:
        print("⚠️ Plan Tiers non trouvé")
        return
    
    print("\n" + "="*70)
    print("📊 TRAITEMENT PLAN TIERS")
    print("="*70)
    print(f"Client: {client_id}")
    print(f"Fichier: {Path(file_path).name}")

    try:
        df = pd.read_excel(file_path)
        print(f"Lignes lues: {len(df)}")
    except Exception as e:
        print(f"❌ Erreur de lecture du fichier Plan Tiers : {e}")
        raise

    cols = {c.lower(): c for c in df.columns}
    data = []
    for _, row in df.iterrows():
        compte_tiers = row.get(cols.get('compte_tiers', 'Compte_tiers'), '') or row.get(cols.get('compte tiers', 'Compte tiers'), '')
        intitule_tiers = row.get(cols.get('intitule_du_tiers', 'Intitule_du_tiers'), '') or row.get(cols.get('intitulé du tiers', 'Intitulé du tiers'), '')
        data.append((
            str(compte_tiers),
            str(row.get(cols.get('type', 'Type'), '')),
            str(intitule_tiers),
            str(row.get(cols.get('centralisateur', 'Centralisateur'), ''))
        ))

    ch = ClickHouseManager()
    ch.upsert_dimension(client_id, 'plan_tiers', data)

    print(f"✅ Plan Tiers: {len(data)} lignes insérées dans ClickHouse")


def process_grand_livre(**context):
    """Traiter Grand Livre fusionné → ClickHouse"""
    ti = context['ti']
    client_id = ti.xcom_pull(task_ids='download_files', key='client_id')
    batch_id = ti.xcom_pull(task_ids='download_files', key='batch_id')
    files = ti.xcom_pull(task_ids='download_files', key='files')
    local_dir = ti.xcom_pull(task_ids='download_files', key='local_dir')
    
    print("\n" + "="*70)
    print("📊 TRAITEMENT GRAND LIVRE FUSIONNÉ")
    print("="*70)
    print(f"Client: {client_id}")
    print(f"Batch: {batch_id}")

    from scripts.fusion_gl import transform_file

    file_comptes = files.get('grand_livre_comptes') if files else None
    file_tiers = files.get('grand_livre_tiers') if files else None
    
    if not file_comptes or not file_tiers:
        raise ValueError("Fichiers Grand Livre manquants")
    
    print(f"GL Comptes: {Path(file_comptes).name}")
    print(f"GL Tiers: {Path(file_tiers).name}")

    # Fusion des Grand Livres
    gl_fusionne, _, _ = transform_file(
        file_comptes,
        file_tiers,
        local_dir
    )
    
    print(f"✅ Fusion terminée: {Path(gl_fusionne).name}")

    try:
        df = pd.read_excel(gl_fusionne)
        print(f"Lignes fusionnées: {len(df)}")
    except Exception as e:
        print(f"❌ Erreur de lecture du fichier Grand Livre fusionné : {e}")
        raise

    # Extraire la période
    periode = None
    if "Periode" in df.columns:
        periode = df["Periode"].iloc[0]
    elif "periode" in df.columns:
        periode = df["periode"].iloc[0]
    else:
        # Fallback: extraire de s3_prefix ou utiliser date actuelle
        periode = datetime.now().strftime("%Y%m")
    
    print(f"Période détectée: {periode}")

    cols = {c.lower(): c for c in df.columns}

    data = []
    errors = 0
    for idx, row in df.iterrows():
        try:
            date_gl = (
                pd.to_datetime(row.get(cols.get('date_gl', 'Date_GL')), errors='coerce').date()
                if pd.notna(row.get(cols.get('date_gl', 'Date_GL'))) else None
            )
            date_ecr = (
                pd.to_datetime(row.get(cols.get('date', 'Date')), errors='coerce').date()
                if pd.notna(row.get(cols.get('date', 'Date'))) else None
            )
            data.append((
                str(uuid.uuid4()),  # ID unique
                date_gl,
                str(row.get(cols.get('entite', 'Entite'), '')),
                str(row.get(cols.get('compte', 'Compte'), '')),
                date_ecr,
                str(row.get(cols.get('code_journal', 'Code_Journal'), '')),
                str(row.get(cols.get('numero_piece', 'Numero_Piece'), '')),
                str(row.get(cols.get('libelle_ecriture', 'Libelle_Ecriture'), '')),
                float(row.get(cols.get('debit', 'Debit')) or 0),
                float(row.get(cols.get('credit', 'Credit')) or 0),
                float(row.get(cols.get('solde', 'Solde')) or 0),
                periode,
                batch_id
            ))
        except Exception as row_e:
            errors += 1
            if errors <= 5:  # Afficher seulement les 5 premières erreurs
                print(f"⚠️  Erreur ligne {idx}: {row_e}")

    if errors > 0:
        print(f"⚠️  {errors} erreur(s) de parsing sur {len(df)} lignes")

    ch = ClickHouseManager()
    ch.delete_periode_and_insert(client_id, batch_id, periode, data)

    print(f"✅ Grand Livre: {len(data)} transactions insérées dans ClickHouse")
    print("="*70)


with DAG(
    'etl_comptable_clickhouse',
    default_args=default_args,
    description='ETL Multi-tenant avec ClickHouse depuis S3',
    schedule_interval=None,  # Trigger manuel via API
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['etl', 'clickhouse', 'multi-tenant', 's3'],
) as dag:
    
    download = PythonOperator(
        task_id='download_files',
        python_callable=download_files_from_s3
    )

    dim_plan_compte = PythonOperator(
        task_id='process_plan_compte',
        python_callable=process_plan_compte
    )

    dim_code_journal = PythonOperator(
        task_id='process_code_journal',
        python_callable=process_code_journal
    )

    dim_plan_tiers = PythonOperator(
        task_id='process_plan_tiers',
        python_callable=process_plan_tiers
    )

    fact_grand_livre = PythonOperator(
        task_id='process_grand_livre',
        python_callable=process_grand_livre
    )

    # Workflow: Download → Dimensions en parallèle → Fait
    download >> [dim_plan_compte, dim_code_journal, dim_plan_tiers]
    [dim_plan_compte, dim_code_journal, dim_plan_tiers] >> fact_grand_livre