from clickhouse_driver import Client
import os


class ClickHouseManager:
    def __init__(self):
        self.client = Client(
            host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
            port=int(os.getenv('CLICKHOUSE_PORT', '8123')),
            user=os.getenv('CLICKHOUSE_USER', 'default'),
            password=os.getenv('CLICKHOUSE_PASSWORD', 'root')
        )

    def create_client_database(self, client_id):
        db_name = f"envol_client_{client_id}"

        # Créer la base
        self.client.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")

        # Créer les tables
        self._create_dimension_tables(db_name)
        self._create_fact_table(db_name)

        return db_name

    def _create_dimension_tables(self, db_name):
        # Plan Comptable
        self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {db_name}.plan_compte (
                compte String,
                type String,
                intitule_compte String,
                nature_compte String,
                created_at DateTime DEFAULT now(),
                updated_at DateTime DEFAULT now()
            ) ENGINE = ReplacingMergeTree(updated_at)
            ORDER BY (compte)
        """)

        # Code Journal
        self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {db_name}.code_journal (
                code_journal String,
                intitule String,
                type String,
                created_at DateTime DEFAULT now(),
                updated_at DateTime DEFAULT now()
            ) ENGINE = ReplacingMergeTree(updated_at)
            ORDER BY (code_journal)
        """)

        # Plan Tiers
        self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {db_name}.plan_tiers (
                compte_tiers String,
                type String,
                intitule_du_tiers String,
                centralisateur String,
                created_at DateTime DEFAULT now(),
                updated_at DateTime DEFAULT now()
            ) ENGINE = ReplacingMergeTree(updated_at)
            ORDER BY (compte_tiers)
        """)

    def _create_fact_table(self, db_name):
        self.client.execute(f"""
            CREATE TABLE IF NOT EXISTS {db_name}.grand_livre (
                id String,
                date_gl Date,
                entite String,
                compte String,
                date Date,
                code_journal String,
                numero_piece String,
                libelle_ecriture String,
                debit Decimal(18, 2),
                credit Decimal(18, 2),
                solde Decimal(18, 2),
                periode String,
                batch_id String,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(date)
            ORDER BY (batch_id, date, id)
        """)

    def upsert_dimension(self, client_id, table_name, data):
        """Upsert pour tables de dimension (ReplacingMergeTree)"""
        db_name = f"envol_client_{client_id}"

        if not data:
            return

        # Insertion simple, ReplacingMergeTree gère les doublons
        self.client.execute(
            f"INSERT INTO {db_name}.{table_name} VALUES",
            data
        )

    def delete_periode_and_insert(self, client_id, batch_id, periode, data):
        """Supprime la période puis insère les nouvelles données"""
        db_name = f"envol_client_{client_id}"

        # Supprimer l'ancienne période
        self.client.execute(f"""
            ALTER TABLE {db_name}.grand_livre 
            DELETE WHERE periode = '{periode}'
        """)

        # Insérer les nouvelles données
        if data:
            self.client.execute(
                f"INSERT INTO {db_name}.grand_livre VALUES",
                data
            )