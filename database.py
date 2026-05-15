import sqlite3

DB_NAME = "database.db"

# =========================
# CREAR BASE DE DATOS
# =========================

def crear_base_datos():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jornalizacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        cuenta TEXT,
        debe REAL,
        haber REAL,
        descripcion TEXT
    )
    """)

    conn.commit()
    conn.close()

# =========================
# GUARDAR JORNALIZACION
# =========================

def guardar_jornalizacion(fecha, cuenta, debe, haber, descripcion):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO jornalizacion
    (fecha, cuenta, debe, haber, descripcion)
    VALUES (?, ?, ?, ?, ?)
    """, (
        fecha,
        cuenta,
        debe,
        haber,
        descripcion
    ))

    conn.commit()
    conn.close()

# =========================
# OBTENER LIBRO DIARIO
# =========================

def obtener_jornalizacion():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, fecha, cuenta, debe, haber, descripcion
    FROM jornalizacion
    """)

    datos = cursor.fetchall()

    conn.close()

    return datos

# =========================
# OBTENER LIBRO MAYOR
# =========================

def obtener_mayor():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        cuenta,
        SUM(debe) as total_debe,
        SUM(haber) as total_haber
    FROM jornalizacion
    GROUP BY cuenta
    """)

    datos = cursor.fetchall()

    conn.close()

    return datos

