"""
Script de fusion Grand Livre Comptes + Grand Livre Tiers
Nécessite 2 fichiers EXCEL: Grand Livre Comptes + Grand Livre Tiers (déjà traités)
Logique identique au code TypeScript
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path


def load_excel_file(file_path):
    """Charge un fichier Excel et le convertit en structure utilisable"""
    try:
        df = pd.read_excel(file_path)
        return df.to_dict('records')
    except Exception as e:
        print(f"❌ Erreur lecture {file_path}: {e}")
        raise


def group_by_compte(data):
    """
    Groupe les transactions par compte
    Structure: { 'Numero_Compte': ..., 'Transactions': [...] }
    """
    comptes_grouped = {}

    for row in data:
        compte = row.get('Numero_Compte') or row.get('Compte')

        if not compte:
            continue

        if compte not in comptes_grouped:
            comptes_grouped[compte] = {
                'Numero_Compte': compte,
                'Libelle_Compte': row.get('Libelle_Compte', ''),
                'Periode': row.get('Periode', ''),
                'Transactions': []
            }

        comptes_grouped[compte]['Transactions'].append({
            'Date_GL': row.get('Date_GL', ''),
            'Entite': row.get('Entite', ''),
            'Compte': row.get('Compte', ''),
            'Date': row.get('Date', ''),
            'Code_Journal': row.get('Code_Journal', ''),
            'Numero_Piece': row.get('Numero_Piece', ''),
            'Libelle_Ecriture': row.get('Libelle_Ecriture', ''),
            'Debit': row.get('Debit', 0),
            'Credit': row.get('Credit', 0),
            'Solde': row.get('Solde', 0)
        })

    return list(comptes_grouped.values())


def group_by_tiers(data):
    """
    Groupe les transactions par tiers
    IMPORTANT: trans.Compte = Centralisateur (pour la jointure)
    """
    tiers_grouped = {}

    for row in data:
        tiers = row.get('Compte_tiers', '')

        if not tiers:
            continue

        if tiers not in tiers_grouped:
            tiers_grouped[tiers] = {
                'Compte_tiers': tiers,
                'Type': row.get('Type', ''),
                'Intitule_du_tiers': row.get('Intitule_du_tiers', ''),
                'Centralisateur': row.get('Centralisateur', ''),
                'Periode': row.get('Periode', ''),
                'Transactions': []
            }

        # ATTENTION: Utiliser Centralisateur comme Compte pour la jointure
        tiers_grouped[tiers]['Transactions'].append({
            'Date_GL': row.get('Date_GL', ''),
            'Entite': row.get('Entite', ''),
            'Compte': row.get('Centralisateur', ''),  # ← ICI: Centralisateur, pas Compte !
            'Date': row.get('Date', ''),
            'Code_Journal': row.get('Code_Journal', ''),
            'Numero_Piece': row.get('Numero_Piece', ''),
            'Libelle_Ecriture': row.get('Libelle_Ecriture', ''),
            'Debit': row.get('Debit', 0),
            'Credit': row.get('Credit', 0),
            'Solde': row.get('Solde', 0)
        })

    return list(tiers_grouped.values())


def fusionner_grand_livres(comptes_data, tiers_data):
    """
    Fusionne les transactions Comptes avec les infos Tiers
    La jointure se fait sur la clé composite: Compte + Date + Code Journal + N° Pièce + Libellé
    """
    # Construction d'un index rapide des transactions du Grand Livre Tiers
    tiers_index = {}

    for tiers in tiers_data:
        compte_tiers = tiers.get("Compte_tiers", "")
        type_tiers = tiers.get("Type", "")
        intitule_tiers = tiers.get("Intitule_du_tiers", "")
        centralisateur = tiers.get("Centralisateur", "")

        for trans in tiers.get("Transactions", []):
            # Clé de jointure composite
            key = (
                f"{trans.get('Compte', '')}|"
                f"{trans.get('Date', '')}|"
                f"{trans.get('Code_Journal', '')}|"
                f"{trans.get('Numero_Piece', '')}|"
                f"{trans.get('Libelle_Ecriture', '')}"
            )

            tiers_index[key] = {
                "Compte_tiers": compte_tiers,
                "Intitule_du_tiers": intitule_tiers,
                "Centralisateur": centralisateur,
                "Type": type_tiers
            }

    # Enrichissement des transactions du Grand Livre Comptes
    enriched_comptes = []
    total_trans = 0
    trans_avec_tiers = 0
    trans_sans_tiers = 0

    for compte in comptes_data:
        enriched_transactions = []

        for trans in compte.get("Transactions", []):
            total_trans += 1

            # Créer la clé de jointure
            key = (
                f"{trans.get('Compte', '')}|"
                f"{trans.get('Date', '')}|"
                f"{trans.get('Code_Journal', '')}|"
                f"{trans.get('Numero_Piece', '')}|"
                f"{trans.get('Libelle_Ecriture', '')}"
            )

            # Chercher dans l'index des tiers
            tiers_info = tiers_index.get(key)

            if tiers_info:
                trans_avec_tiers += 1
                enriched_trans = {
                    **trans,
                    **tiers_info,
                    "Statut_Jointure": "Trouvé"
                }
            else:
                trans_sans_tiers += 1
                enriched_trans = {
                    **trans,
                    "Statut_Jointure": "Non trouvé"
                }

            enriched_transactions.append(enriched_trans)

        enriched_compte = {
            "Numero_Compte": compte.get("Numero_Compte", ""),
            "Libelle_Compte": compte.get("Libelle_Compte", ""),
            "Periode": compte.get("Periode", ""),
            "Transactions": enriched_transactions
        }

        enriched_comptes.append(enriched_compte)

    stats = {
        "totalTransactionsComptes": total_trans,
        "transactionsAvecTiers": trans_avec_tiers,
        "transactionsSansTiers": trans_sans_tiers,
        "comptesTraites": len(comptes_data)
    }

    return {
        "enrichedComptes": enriched_comptes,
        "stats": stats
    }


def save_outputs(result, output_dir, base_filename):
    """
    Sauvegarde les résultats de la fusion
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    log_path = output_path / "log"
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")

    # 1. JSON structuré (comptes enrichis)
    json_file = output_path / f"{base_filename}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result["enrichedComptes"], f, ensure_ascii=False, indent=2)

    # 2. Excel à plat (toutes les transactions enrichies)
    excel_file = None
    flat_data = []

    for compte in result["enrichedComptes"]:
        for trans in compte["Transactions"]:
            flat_data.append({
                "Numero_Compte": compte["Numero_Compte"],
                "Libelle_Compte": compte["Libelle_Compte"],
                "Periode": compte["Periode"],
                "Date_GL": trans.get("Date_GL", ""),
                "Entite": trans.get("Entite", ""),
                "Compte": trans.get("Compte", ""),
                "Compte_tiers": trans.get("Compte_tiers", ""),
                "Intitule_du_tiers": trans.get("Intitule_du_tiers", ""),
                "Type": trans.get("Type", ""),
                "Centralisateur": trans.get("Centralisateur", ""),
                "Date": trans.get("Date", ""),
                "Code_Journal": trans.get("Code_Journal", ""),
                "Numero_Piece": trans.get("Numero_Piece", ""),
                "Libelle_Ecriture": trans.get("Libelle_Ecriture", ""),
                "Debit": trans.get("Debit", 0),
                "Credit": trans.get("Credit", 0),
                "Solde": trans.get("Solde", 0),
                "Statut_Jointure": trans.get("Statut_Jointure", "Non trouvé")
            })

    if flat_data:
        df = pd.DataFrame(flat_data)
        excel_file = output_path / f"{base_filename}_{timestamp}.xlsx"
        df.to_excel(excel_file, index=False, engine='openpyxl', sheet_name='Grand Livre Complet')

    # 3. Log avec statistiques
    log_file = log_path / f"recap_{base_filename}_{timestamp}.json"
    log_data = {
        "fichier": base_filename,
        "date_traitement": datetime.now().isoformat(),
        "statistiques": result["stats"],
        "taux_enrichissement": (
            round((result["stats"]["transactionsAvecTiers"] / result["stats"]["totalTransactionsComptes"]) * 100, 2)
            if result["stats"]["totalTransactionsComptes"] > 0 else 0
        )
    }

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    return str(json_file), str(excel_file) if excel_file else None, str(log_file)


def transform_file(gl_comptes_path, gl_tiers_path, output_dir):
    """
    Fonction principale - nécessite 2 fichiers EXCEL
    """
    print(f"🔄 Fusion Grand Livre Comptes + Grand Livre Tiers")
    print(f"   - GL Comptes: {gl_comptes_path}")
    print(f"   - GL Tiers: {gl_tiers_path}")

    # 1. Charger les deux fichiers Excel
    print(f"\n📥 Chargement des fichiers Excel...")
    comptes_raw = load_excel_file(gl_comptes_path)
    tiers_raw = load_excel_file(gl_tiers_path)

    print(f"   ✅ {len(comptes_raw)} lignes chargées (GL Comptes)")
    print(f"   ✅ {len(tiers_raw)} lignes chargées (GL Tiers)")

    # 2. Grouper les données par compte/tiers
    print(f"\n📊 Regroupement des données...")
    comptes_data = group_by_compte(comptes_raw)
    tiers_data = group_by_tiers(tiers_raw)

    print(f"   📊 {len(comptes_data)} comptes groupés")
    print(f"   📋 {len(tiers_data)} tiers groupés")

    # 3. Fusionner les données
    print(f"\n🔗 Fusion en cours...")
    result = fusionner_grand_livres(comptes_data, tiers_data)

    # 4. Sauvegarder les outputs
    base_filename = "grand_livre_fusionne"
    json_file, excel_file, log_file = save_outputs(result, output_dir, base_filename)

    print(f"\n✅ Fichiers générés:")
    print(f"   - JSON: {json_file}")
    if excel_file:
        print(f"   - Excel: {excel_file}")
    print(f"   - Log: {log_file}")

    stats = result["stats"]
    print(f"\n📊 Statistiques de fusion:")
    print(f"   - Comptes traités: {stats['comptesTraites']}")
    print(f"   - Total transactions: {stats['totalTransactionsComptes']}")
    print(f"   - ✅ Avec tiers: {stats['transactionsAvecTiers']}")
    print(f"   - ❌ Sans tiers: {stats['transactionsSansTiers']}")

    if stats['totalTransactionsComptes'] > 0:
        taux = (stats['transactionsAvecTiers'] / stats['totalTransactionsComptes']) * 100
        print(f"   - 📈 Taux d'enrichissement: {taux:.2f}%")

    return json_file, excel_file, log_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python fusion_gl.py <gl_comptes.xlsx> <gl_tiers.xlsx> <output_dir>")
        sys.exit(1)

    gl_comptes = sys.argv[1]
    gl_tiers = sys.argv[2]
    output_dir = sys.argv[3]

    transform_file(gl_comptes, gl_tiers, output_dir)