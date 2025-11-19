"""
Script de transformation du fichier Code Journal
Extraction des codes journaux depuis Excel vers format structuré
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path


def safe_str(value):
    """Convertit une valeur en string de manière sûre"""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def parse_code_journal(file_path):
    """
    Parse un fichier Excel Code Journal
    Retourne: dict avec métadonnées et codes journaux
    """

    # Log de traitement
    traitement_log = {
        "fichier": Path(file_path).name,
        "date_traitement": datetime.now().isoformat(),
        "lignes_totales": 0,
        "codes_detectes": 0,
        "lignes_ignorees": [],
        "erreurs": []
    }

    try:
        df = pd.read_excel(
            file_path,
            sheet_name=0,
            header=None,
            dtype=str,
            keep_default_na=False,
            na_filter=False
        )
        df = df.replace({np.nan: None})
        data = df.values.tolist()

        traitement_log["lignes_totales"] = len(data)

    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier: {e}")
        traitement_log["erreurs"].append({
            "type": "LECTURE_FICHIER",
            "message": str(e)
        })
        raise

    codes_journaux = []
    entite = ""
    date_extraction = ""

    # Extraction des métadonnées (10 premières lignes)
    for i in range(min(10, len(data))):
        row = data[i]
        if not row:
            continue

        # Recherche entité
        if not entite and row[0]:
            first_cell = safe_str(row[0])
            if (first_cell and
                not first_cell.startswith("©") and
                "Code" not in first_cell and
                len(first_cell) < 50):
                entite = first_cell

        # Recherche date extraction
        for j in range(len(row)):
            if "Date de tirage" in safe_str(row[j]):
                if j + 2 < len(row) and row[j + 2]:
                    date_extraction = safe_str(row[j + 2])
                break

    # Valeurs par défaut
    if not entite:
        entite = "ENVOL"
        traitement_log["erreurs"].append({
            "type": "ENTITE_PAR_DEFAUT",
            "message": "Entité non trouvée, utilisation de 'ENVOL' par défaut"
        })
    if not date_extraction:
        date_extraction = datetime.now().strftime("%d/%m/%Y")
        traitement_log["erreurs"].append({
            "type": "DATE_PAR_DEFAUT",
            "message": "Date d'extraction non trouvée, utilisation de la date actuelle"
        })

    traitement_log["entite"] = entite
    traitement_log["date_extraction"] = date_extraction

    # Recherche ligne d'en-tête (contient "Code")
    header_row_index = -1
    for i in range(min(15, len(data))):
        row = data[i]
        if row and row[0] == "Code":
            header_row_index = i
            break

    if header_row_index == -1:
        error_msg = "Impossible de trouver la ligne d'en-tête avec 'Code'"
        traitement_log["erreurs"].append({
            "type": "ENTETE_INTROUVABLE",
            "message": error_msg
        })
        raise ValueError(error_msg)

    traitement_log["header_row_index"] = header_row_index

    # Extraction des codes journaux (commence 3 lignes après l'en-tête)
    for i in range(header_row_index + 3, len(data)):
        row = data[i]
        if not row or not row[0]:
            continue

        code = safe_str(row[0])

        # Ignorer lignes de légende et lignes invalides
        if (code.startswith("=") or
            "C.L" in code or
            "Som" in code or
            "Rap" in code or
            len(code) > 10 or
            code == ""):

            if code:  # Logger seulement si non vide
                traitement_log["lignes_ignorees"].append({
                    "ligne": i,
                    "code": code,
                    "raison": "Ligne de légende ou invalide"
                })
            continue

        intitule = safe_str(row[1]) if len(row) > 1 else ""
        type_journal = safe_str(row[6]) if len(row) > 6 else safe_str(row[7]) if len(row) > 7 else ""
        compte_tresorerie = safe_str(row[8]) if len(row) > 8 else safe_str(row[9]) if len(row) > 9 else ""

        # Ajouter seulement si code et intitulé présents
        if code and intitule:
            codes_journaux.append({
                "Code_journal": code,
                "Intitule_journal": intitule,
                "Type": type_journal,
                "Compte_tresorerie": compte_tresorerie
            })
        else:
            traitement_log["lignes_ignorees"].append({
                "ligne": i,
                "code": code,
                "intitule": intitule,
                "raison": "Code ou intitulé manquant"
            })

    traitement_log["codes_detectes"] = len(codes_journaux)
    traitement_log["statistiques"] = {
        "total_codes": len(codes_journaux),
        "lignes_ignorees_count": len(traitement_log["lignes_ignorees"]),
        "erreurs_count": len(traitement_log["erreurs"])
    }

    meta_data = {
        "Entite": entite,
        "DateExtraction": date_extraction,
        "NombreJournaux": len(codes_journaux)
    }

    return {
        "meta": meta_data,
        "codes_journaux": codes_journaux,
        "traitementLog": traitement_log
    }


def save_outputs(result, output_dir, base_filename):
    """
    Sauvegarde les résultats en JSON et Excel
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Créer le dossier log
    log_path = output_path / "log"
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")

    # 1. JSON complet
    json_file = output_path / f"{base_filename}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            "meta": result["meta"],
            "codes_journaux": result["codes_journaux"]
        }, f, ensure_ascii=False, indent=2)

    # 2. Excel
    excel_file = None

    if result["codes_journaux"]:
        df = pd.DataFrame(result["codes_journaux"])
        excel_file = output_path / f"{base_filename}_{timestamp}.xlsx"
        df.to_excel(excel_file, index=False, engine='openpyxl')

    # 3. Log de traitement
    log_file = log_path / f"recap_{base_filename}_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(result["traitementLog"], f, ensure_ascii=False, indent=2)

    return str(json_file), str(excel_file) if excel_file else None, str(log_file)


def transform_file(input_file, output_dir):
    """
    Fonction principale de transformation
    """
    print(f"🔄 Transformation Code Journal: {input_file}")

    result = parse_code_journal(input_file)
    base_filename = Path(input_file).stem
    json_file, excel_file, log_file = save_outputs(result, output_dir, base_filename)

    print(f"✅ Fichiers générés:")
    print(f"   - JSON: {json_file}")
    if excel_file:
        print(f"   - Excel: {excel_file}")
    print(f"   - Log: {log_file}")

    stats = result["traitementLog"]["statistiques"]
    print(f"\n📊 Statistiques:")
    print(f"   - Codes extraits: {stats['total_codes']}")
    print(f"   - Lignes ignorées: {stats['lignes_ignorees_count']}")
    print(f"   - Erreurs: {stats['erreurs_count']}")

    return json_file, excel_file, log_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python transform_code_journal.py <input_file> <output_dir>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    transform_file(input_file, output_dir)