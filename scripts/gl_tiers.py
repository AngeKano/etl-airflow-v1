"""
Script de transformation du Grand Livre Tiers avec Plan Tiers
Nécessite 2 fichiers: Grand Livre Tiers (Excel SAGE) + Plan Tiers (Excel)
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


def parse_amount(value):
    """Parse un montant en float - logique identique au TypeScript"""
    if pd.isna(value) or value is None or value == '':
        return 0.0
    
    str_value = str(value).strip()
    
    if not str_value or str_value == "-" or str_value == "":
        return 0.0

    try:
        # Nettoyer: supprimer espaces, remplacer . par rien, , par .
        cleaned = str_value.replace(' ', '').replace('.', '').replace(',', '.')
        parsed = float(cleaned)
        return 0.0 if pd.isna(parsed) else parsed
    except (ValueError, AttributeError):
        return 0.0


def format_date(date_str):
    """Formate une date DDMMYY en DD/MM/YYYY - logique identique au TypeScript"""
    if not date_str:
        return ""

    # Supprimer tous les caractères non-numériques
    cleaned = re.sub(r'\D', '', str(date_str))
    
    if len(cleaned) == 6:
        day = cleaned[0:2]
        month = cleaned[2:4]
        year = cleaned[4:6]
        full_year = f"19{year}" if int(year) > 50 else f"20{year}"
        return f"{day}/{month}/{full_year}"

    return date_str


def parse_plan_tiers(file_path):
    """
    Parse le fichier Excel Plan Tiers
    Retourne un dict {compte_tiers: infos}
    
    Colonnes attendues: Compte tiers | Type | Intitulé du tiers | Centralisateur | Periode
    """
    try:
        df = pd.read_excel(file_path)

        plan_tiers_map = {}
        for _, row in df.iterrows():
            compte = safe_str(row.get('Compte tiers', ''))
            if compte:
                plan_tiers_map[compte] = {
                    'Type': safe_str(row.get('Type', '')),
                    'Intitule_du_tiers': safe_str(row.get('Intitulé du tiers', '')),
                    'Centralisateur': safe_str(row.get('Centralisateur', '')),
                    'Periode': safe_str(row.get('Periode', ''))
                }

        return plan_tiers_map

    except Exception as e:
        print(f"❌ Erreur lecture Plan Tiers: {e}")
        raise


def parse_grand_livre_tiers(file_path, plan_tiers_map):
    """
    Parse le Grand Livre Tiers avec enrichissement depuis Plan Tiers
    Logique identique au code TypeScript
    """
    traitement_log = {
        "fichier": Path(file_path).name,
        "date_traitement": datetime.now().isoformat(),
        "lignes_totales": 0,
        "tiers_detectes": 0,
        "transactions_totales": 0,
        "plan_tiers_count": len(plan_tiers_map),
        "erreurs": []
    }

    try:
        # Lecture identique au TypeScript: header=None, raw=False
        # IMPORTANT: Ne pas convertir les dates en strings automatiquement
        df = pd.read_excel(
            file_path,
            sheet_name=0,
            header=None,
            keep_default_na=False
        )

        # Convertir en liste de listes (comme le fait sheet_to_json avec header: 1)
        data = df.values.tolist()
        traitement_log["lignes_totales"] = len(data)

    except Exception as e:
        print(f"❌ Erreur lecture fichier: {e}")
        traitement_log["erreurs"].append({
            "type": "LECTURE_FICHIER",
            "message": str(e)
        })
        raise

    parsed_tiers = []
    parsed_transactions = []

    # === Extraction métadonnées (lignes 0-9) ===
    entite = ""
    date_gl = ""
    periode = ""

    for i in range(min(10, len(data))):
        row = data[i]

        # Chercher l'entité dans la première cellule
        if not entite and row[0]:
            first_cell = str(row[0]).strip()
            if (first_cell and
                "Date" not in first_cell and
                "Impression" not in first_cell and
                "©" not in first_cell):
                entite = first_cell

        # Chercher "Période du"
        if any("Période du" in str(cell) for cell in row if cell):
            idx = next((j for j, cell in enumerate(row) if cell and "Période du" in str(cell)), None)
            if idx is not None:
                # La date est dans la cellule suivante de la ligne suivante
                if i + 1 < len(data) and idx + 1 < len(data[i + 1]):
                    date_fin_val = data[i + 1][idx + 1]

                    # Gérer les datetime Python
                    if isinstance(date_fin_val, datetime):
                        date_gl = date_fin_val.strftime("%d/%m/%Y")
                        periode = date_fin_val.strftime("%Y%m")
                    else:
                        date_fin = str(date_fin_val or "").strip()
                        match = re.search(r'(\d{2})/(\d{2})/(\d{2,4})', date_fin)
                        if match:
                            year = match.group(3)
                            if len(year) == 2:
                                year = f"20{year}"
                            periode = f"{year}{match.group(2)}"
                            date_gl = date_fin

    # Valeurs par défaut
    if not entite:
        entite = "ENVOL"
    if not periode:
        periode = "202412"
    if not date_gl:
        date_gl = "31/12/2024"

    traitement_log["entite"] = entite
    traitement_log["periode"] = periode
    traitement_log["date_gl"] = date_gl

    # === Parser les tiers et transactions ===
    i = 0
    while i < len(data):
        row = data[i]

        if not row or len(row) == 0:
            i += 1
            continue

        col0 = row[0]
        col1 = row[1] if len(row) > 1 else None
        col2 = row[2] if len(row) > 2 else None
        col3 = row[3] if len(row) > 3 else None

        # Convertir col0 en string seulement si ce n'est pas un datetime
        col0_str = str(col0).strip() if col0 is not None and not isinstance(col0, datetime) else ""
        col2_str = str(col2).strip() if col2 is not None else ""
        col3_str = str(col3).strip() if col3 is not None else ""

        # Détection tiers: col0 = compte alphanum, col1 vide/None, col2 = libellé, pas de "Total"
        # IMPORTANT: col1 peut être pd.NA, None, nan, ou "" selon pandas
        is_col1_empty = col1 is None or pd.isna(col1) or str(col1).strip() == ""

        is_tiers = (
            col0_str and
            re.match(r'^[0-9A-Z]+$', col0_str) and
            is_col1_empty and
            col2_str and
            "Total" not in col2_str
        )

        if is_tiers:
            # Récupérer infos du Plan Tiers
            tiers_info = plan_tiers_map.get(col0_str)

            tiers = {
                "Compte_tiers": col0_str,
                "Type": tiers_info['Type'] if tiers_info else "Non défini",
                "Intitule_du_tiers": tiers_info['Intitule_du_tiers'] if tiers_info else col2_str,
                "Centralisateur": tiers_info['Centralisateur'] if tiers_info else col3_str,
                "Periode": tiers_info['Periode'] if tiers_info else periode,
                "Transactions": []
            }

            # Parcourir les transactions suivantes
            j = i + 1
            while j < len(data):
                trans_row = data[j]

                if not trans_row or len(trans_row) == 0:
                    j += 1
                    continue

                trans_col0 = trans_row[0] if len(trans_row) > 0 else None
                trans_col1 = trans_row[1] if len(trans_row) > 1 else None
                trans_col3 = trans_row[3] if len(trans_row) > 3 else None

                trans_col3_str = str(trans_col3).strip() if trans_col3 is not None else ""

                # Stop si "Total" dans col3
                if "Total" in trans_col3_str:
                    break

                # Stop si nouveau tiers détecté (col0 alphanum + col1 vide)
                trans_col0_str = str(trans_col0).strip() if trans_col0 is not None and not isinstance(trans_col0, datetime) else ""
                is_trans_col1_empty = trans_col1 is None or pd.isna(trans_col1) or str(trans_col1).strip() == ""

                if trans_col0_str and re.match(r'^[0-9A-Z]+$', trans_col0_str) and is_trans_col1_empty:
                    break

                # Transaction = datetime Python OU date 6 chiffres
                is_transaction = False
                transaction_date = ""

                if isinstance(trans_col0, datetime):
                    # C'est un datetime Python
                    is_transaction = True
                    transaction_date = trans_col0.strftime("%d/%m/%Y")
                elif trans_col0_str and re.match(r'^\d{6}$', trans_col0_str):
                    # C'est une date format DDMMYY
                    is_transaction = True
                    transaction_date = format_date(trans_col0_str)

                if is_transaction:
                    try:
                        code_journal = str(trans_row[1] or "").strip() if len(trans_row) > 1 else ""
                        numero_piece = str(trans_row[2] or "").strip() if len(trans_row) > 2 else ""
                        libelle = str(trans_row[4] or "").strip() if len(trans_row) > 4 else ""

                        debit = parse_amount(trans_row[9]) if len(trans_row) > 9 else 0.0
                        credit = parse_amount(trans_row[11]) if len(trans_row) > 11 else 0.0
                        solde = parse_amount(trans_row[14]) if len(trans_row) > 14 else 0.0

                        transaction = {
                            "Date_GL": date_gl,
                            "Entite": entite,
                            "Compte": tiers["Compte_tiers"],
                            "Date": transaction_date,
                            "Code_Journal": code_journal,
                            "Numero_Piece": numero_piece,
                            "Libelle_Ecriture": libelle,
                            "Debit": debit,
                            "Credit": credit,
                            "Solde": solde
                        }

                        tiers["Transactions"].append(transaction)
                        parsed_transactions.append(transaction)

                    except Exception as e:
                        traitement_log["erreurs"].append({
                            "ligne": j,
                            "erreur": str(e)
                        })

                j += 1

            # Ajouter le tiers seulement s'il a des transactions
            if len(tiers["Transactions"]) > 0:
                parsed_tiers.append(tiers)

            i = j
        else:
            i += 1

    traitement_log["tiers_detectes"] = len(parsed_tiers)
    traitement_log["transactions_totales"] = len(parsed_transactions)

    return {
        "tiersData": parsed_tiers,
        "allTransactions": parsed_transactions,
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

    # 1. JSON structuré (identique au downloadJSON du TypeScript)
    json_file = output_path / f"{base_filename}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result["tiersData"], f, ensure_ascii=False, indent=2)

    # 2. Excel complet (identique au downloadExcelComplete du TypeScript)
    excel_file = None
    flat_data = []
    for tiers in result["tiersData"]:
        for trans in tiers["Transactions"]:
            flat_data.append({
                "Compte_tiers": tiers["Compte_tiers"],
                "Type": tiers["Type"],
                "Intitule_du_tiers": tiers["Intitule_du_tiers"],
                "Centralisateur": tiers["Centralisateur"],
                "Periode": tiers["Periode"],
                **trans
            })

    if flat_data:
        df = pd.DataFrame(flat_data)
        excel_file = output_path / f"{base_filename}_{timestamp}.xlsx"
        df.to_excel(excel_file, index=False, engine='openpyxl')

    # 3. Log de traitement
    log_file = log_path / f"recap_{base_filename}_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(result["traitementLog"], f, ensure_ascii=False, indent=2)

    return str(json_file), str(excel_file) if excel_file else None, str(log_file)


def transform_file(grand_livre_path, plan_tiers_path, output_dir):
    """
    Fonction principale - nécessite 2 fichiers
    """
    print(f"🔄 Transformation Grand Livre Tiers")
    print(f"   - Grand Livre: {grand_livre_path}")
    print(f"   - Plan Tiers: {plan_tiers_path}")

    # 1. Charger Plan Tiers
    plan_tiers_map = parse_plan_tiers(plan_tiers_path)
    print(f"   📋 {len(plan_tiers_map)} tiers dans le plan")

    # 2. Parser Grand Livre avec enrichissement
    result = parse_grand_livre_tiers(grand_livre_path, plan_tiers_map)

    # 3. Sauvegarder les outputs
    base_filename = Path(grand_livre_path).stem
    json_file, excel_file, log_file = save_outputs(result, output_dir, base_filename)

    print(f"✅ Fichiers générés:")
    print(f"   - JSON: {json_file}")
    if excel_file:
        print(f"   - Excel: {excel_file}")
    print(f"   - Log: {log_file}")

    log = result["traitementLog"]
    print(f"\n📊 Statistiques:")
    print(f"   - Tiers: {log['tiers_detectes']}")
    print(f"   - Transactions: {log['transactions_totales']}")
    print(f"   - Erreurs: {len(log['erreurs'])}")

    return json_file, excel_file, log_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python gl_tiers.py <grand_livre.xlsx> <plan_tiers.xlsx> <output_dir>")
        sys.exit(1)

    grand_livre = sys.argv[1]
    plan_tiers = sys.argv[2]
    output_dir = sys.argv[3]

    transform_file(grand_livre, plan_tiers, output_dir)