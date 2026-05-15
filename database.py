import sqlite3

def init_db():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jornalizacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        cuenta TEXT NOT NULL,
        descripcion TEXT,
        debe REAL DEFAULT 0,
        haber REAL DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


