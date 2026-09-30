"""
PostgreSQL Database Setup & Verification Utility
Run this script to test your PostgreSQL connection and create the crowd_safety_db database:
    python backend/init_postgres_db.py
"""
import os
import sys
import getpass
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def main():
    print("=" * 65)
    print(" AI Crowd Safety System — PostgreSQL Database Initializer")
    print("=" * 65)
    
    host = input("PostgreSQL Host [localhost]: ").strip() or "localhost"
    port = input("PostgreSQL Port [5432]: ").strip() or "5432"
    user = input("PostgreSQL Username [postgres]: ").strip() or "postgres"
    password = getpass.getpass("PostgreSQL Password: ")
    dbname = input("Target Database Name [crowd_safety_db]: ").strip() or "crowd_safety_db"

    print(f"\nConnecting to PostgreSQL server at {host}:{port} as user '{user}'...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("[OK] Connected to PostgreSQL server.")

        # Check if target database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{dbname}';")
        exists = cursor.fetchone()
        if not exists:
            print(f"Creating database '{dbname}'...")
            cursor.execute(f"CREATE DATABASE {dbname};")
            print(f"[OK] Database '{dbname}' created successfully.")
        else:
            print(f"[OK] Database '{dbname}' already exists.")

        cursor.close()
        conn.close()

        # Update .env file
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        new_db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            content = re.sub(r'DATABASE_URL=.*', f'DATABASE_URL="{new_db_url}"', content)
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[OK] Updated DATABASE_URL in {env_path}")

        print("\nInitialization complete! You can now start the backend with:")
        print("    python backend/app/main.py")

    except Exception as e:
        print(f"\n[ERROR] Failed to initialize PostgreSQL: {e}")
        print("\nTip: If you want to evaluate immediately without PostgreSQL credentials,")
        print("the backend automatically operates seamlessly with SQLite fallback.")

if __name__ == "__main__":
    main()
