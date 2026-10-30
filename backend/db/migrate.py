"""Apply db/init.sql to DATABASE_URL. Idempotent; the API runs it on start on Render.

    DATABASE_URL=postgresql://... python db/migrate.py
"""
import os
import pathlib

import psycopg

SQL = (pathlib.Path(__file__).resolve().parent / "init.sql").read_text()

if __name__ == "__main__":
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conn.execute(SQL)
    print("schema up to date")
