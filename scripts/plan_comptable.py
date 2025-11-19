"""
Script de transformation du Plan Comptable
Nécessite 1 fichier: Plan Comptable (Excel SAGE/CEGID/EBP)
Logique identique au code TypeScript
"""

import pandas as pd
import numpy as np
import json
import re
from datetime import datetime
from pathlib import Path


def safe_str(value):
    """Convertit une valeur en string de manière sûre"""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def get_classe_compte(numero_compte):
    """
    Déduction de la classe du compte à partir de son premier chiffre (PCG français)
    """
    if not numero_compte:
        return "Autre"

    first_digit = numero_compte[0] if numero_compte else ""

    classe_map = {
        "1": "Classe 1 - Capitaux",
        "2": "Classe 2 - Immobilisations",
        "3": "Classe 3 - Stocks",
        "4": "Classe 4 - Tiers",
        "5": "Classe 5 - Trésorerie",
        "6": "Classe 6 - Charges",
        "7": "Classe 7 - Produits",
        "8": "Classe 8 - Comptes spéciaux",
        "9": "Classe 9 - Analytique"
    }

    return classe_map.get(first_digit, "Autre")


def parse_plan_compte(file_path):
    """
    Parse le fichier Excel Plan Comptable
    - Repère dynamiquement la ligne d'en-tête dans les 15 premières lignes
    - Extrait les comptes à partir de la 3ème ligne suivant l'en-tête
    - Extrait entité et date situées en début de feuille
    - Calcule des statistiques
    """
    traitement_log = {
        "fichier": Path(file_path).name,
        "date_traitement": datetime.now().isoformat(),
        "lignes_totales": 0,
        "comptes_detectes": 0,
        "comptes_detail": 0,
        "comptes_total": 0,
        "erreurs": []
    }

    try:
        # Lecture sans header pour analyse structure
        df = pd.read_excel(
            file_path,
            sheet_name=0,
            header=None,
            keep_default_na=False
        )

        data = df.values.tolist()
        traitement_log["lignes_totales"] = len(data)

    except Exception as e:
        print(f"❌ Erreur lecture fichier: {e}")
        traitement_log["erreurs"].append({
            "type": "LECTURE_FICHIER",
            "message": str(e)
        })
        raise

    parsed_comptes = []

    # === Extraction métadonnées (entité, date) dans les 10 premières lignes ===
    entite = ""
    date_extraction = ""

    for i in range(min(10, len(data))):
        row = data[i]
        if not row:
            continue

        # Recherche de l'entité
        if not entite and row[0]:
            first_cell = str(row[0]).strip()
            if (first_cell and
                    "©" not in first_cell and
                    "Type" not in first_cell and
                    len(first_cell) < 50):
                entite = first_cell

        # Recherche de la date d'extraction
        for j in range(len(row)):
            cell_value = str(row[j] or "")
            if "Date de tirage" in cell_value:
                # La date est généralement 2 colonnes après
                if j + 2 < len(row) and row[j + 2]:
                    date_val = row[j + 2]
                    if isinstance(date_val, datetime):
                        date_extraction = date_val.strftime("%d/%m/%Y")
                    else:
                        date_extraction = str(date_val).strip()
                break

    # Valeurs par défaut
    if not entite:
        entite = "ENVOL"
    if not date_extraction:
        date_extraction = datetime.now().strftime("%d/%m/%Y")

    traitement_log["entite"] = entite
    traitement_log["date_extraction"] = date_extraction

    # === Recherche de la ligne d'en-tête ("Type" et "compte") ===
    header_row_index = -1
    for i in range(min(15, len(data))):
        row = data[i]
        if row and row[0] == "Type" and "compte" in str(row[1] or "").lower():
            header_row_index = i
            break

    if header_row_index == -1:
        raise ValueError("Impossible de trouver la ligne d'en-tête du plan comptable")

    traitement_log["header_row_index"] = header_row_index

    # === Lecture des comptes à partir de la 3e ligne après l'en-tête ===
    comptes_detail = 0
    comptes_total = 0

    for i in range(header_row_index + 3, len(data)):
        row = data[i]
        if not row or len(row) < 2:
            continue

        # Col[1] = numéro de compte
        numero_compte = str(row[1] or "").strip()

        # Ignorer les lignes vides ou non valides
        if not numero_compte or len(numero_compte) < 3:
            continue

        # Col[0] = type compte (Détail/Total)
        type_compte = str(row[0] or "").strip()

        # Compter les types
        if type_compte == "Détail":
            comptes_detail += 1
        if type_compte == "Total":
            comptes_total += 1

        # Col[4] = intitulé, Col[14] = nature
        intitule = str(row[4] or "").strip() if len(row) > 4 else ""
        nature = str(row[14] or "").strip() if len(row) > 14 else "Aucune"

        compte = {
            "Compte": numero_compte,
            "Type": type_compte or "Détail",
            "Intitule_compte": intitule,
            "Nature_compte": nature if nature else "Aucune"
        }

        parsed_comptes.append(compte)

    traitement_log["comptes_detectes"] = len(parsed_comptes)
    traitement_log["comptes_detail"] = comptes_detail
    traitement_log["comptes_total"] = comptes_total

    # === Calcul des statistiques ===
    statistics = {
        "par_nature": {},
        "par_classe": {},
        "par_type": {}
    }

    for compte in parsed_comptes:
        # Stat par nature
        nature = compte["Nature_compte"]
        statistics["par_nature"][nature] = statistics["par_nature"].get(nature, 0) + 1

        # Stat par classe
        classe = get_classe_compte(compte["Compte"])
        statistics["par_classe"][classe] = statistics["par_classe"].get(classe, 0) + 1

        # Stat par type
        type_compte = compte["Type"]
        statistics["par_type"][type_compte] = statistics["par_type"].get(type_compte, 0) + 1

    metadata = {
        "Entite": entite,
        "DateExtraction": date_extraction,
        "NombreComptes": len(parsed_comptes),
        "NombreComptesDetail": comptes_detail,
        "NombreComptesTotal": comptes_total
    }

    return {
        "comptes": parsed_comptes,
        "metadata": metadata,
        "statistics": statistics,
        "traitementLog": traitement_log
    }


def save_outputs(result, output_dir, base_filename):
    """
    Sauvegarde les résultats
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    log_path = output_path / "log"
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")

    # 1. JSON structuré complet (meta + comptes + stats)
    json_file = output_path / f"{base_filename}_{timestamp}.json"
    export_data = {
        "meta": result["metadata"],
        "comptes": result["comptes"],
        "statistiques": result["statistics"]
    }
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    # 2. Excel avec la liste des comptes
    excel_file = None
    if result["comptes"]:
        df = pd.DataFrame(result["comptes"])
        excel_file = output_path / f"{base_filename}_{timestamp}.xlsx"
        df.to_excel(excel_file, index=False, engine='openpyxl', sheet_name='Plan Comptable')

    # 3. Log de traitement
    log_file = log_path / f"recap_{base_filename}_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(result["traitementLog"], f, ensure_ascii=False, indent=2)

    return str(json_file), str(excel_file) if excel_file else None, str(log_file)


def transform_file(file_path, output_dir):
    """
    Fonction principale - nécessite 1 fichier
    """
    print(f"🔄 Transformation Plan Comptable")
    print(f"   - Fichier: {file_path}")

    # 1. Parser le Plan Comptable
    result = parse_plan_compte(file_path)

    # 2. Sauvegarder les outputs
    base_filename = Path(file_path).stem
    json_file, excel_file, log_file = save_outputs(result, output_dir, base_filename)

    print(f"✅ Fichiers générés:")
    print(f"   - JSON: {json_file}")
    if excel_file:
        print(f"   - Excel: {excel_file}")
    print(f"   - Log: {log_file}")

    log = result["traitementLog"]
    print(f"\n📊 Statistiques:")
    print(f"   - Comptes: {log['comptes_detectes']}")
    print(f"   - Détail: {log['comptes_detail']}")
    print(f"   - Total: {log['comptes_total']}")
    print(f"   - Erreurs: {len(log['erreurs'])}")

    # Afficher quelques stats
    stats = result["statistics"]
    print(f"\n📈 Répartition par classe:")
    for classe, count in sorted(stats["par_classe"].items()):
        print(f"   - {classe}: {count}")

    return json_file, excel_file, log_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python plan_compte.py <fichier.xlsx> <output_dir>")
        sys.exit(1)

    file_path = sys.argv[1]
    output_dir = sys.argv[2]

    transform_file(file_path, output_dir)