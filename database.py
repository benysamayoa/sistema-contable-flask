import sqlite3

def crear_base_datos():
    conexion = sqlite3.connect("Jornalizacion.db")
    cursor = conexion.cursor()

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

    conexion.commit()
    conexion.close()


def guardar_jornalizacion(fecha, cuenta, debe, haber, descripcion):
    conexion = sqlite3.connect("Jornalizacion.db")
    cursor = conexion.cursor()

    cursor.execute("""
    INSERT INTO jornalizacion (fecha, cuenta, debe, haber, descripcion)
    VALUES (?, ?, ?, ?, ?)
    """, (fecha, cuenta, debe, haber, descripcion))

    conexion.commit()
    conexion.close()


def obtener_jornalizacion():
    conexion = sqlite3.connect("Jornalizacion.db")
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM jornalizacion")
    datos = cursor.fetchall()

    conexion.close()
    return datos