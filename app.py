from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "clave_super_segura_123"

# =====================================================
# CONEXION
# =====================================================

def conectar():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# =====================================================
# CREAR TABLAS
# =====================================================

def init_db():
    conn = conectar()
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
        fecha TEXT,
        cuenta TEXT,
        debe REAL DEFAULT 0,
        haber REAL DEFAULT 0,
        descripcion TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =====================================================
# HASH PASSWORD
# =====================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# =====================================================
# LECTURA DEL CATÁLOGO DESDE EL CSV CON PANDAS
# =====================================================

def obtener_datos_csv():
    try:
        # Leemos el archivo completo sin saltar líneas para asegurar que encuentre los datos
        df = pd.read_csv("CLASIFICACION-CUENTAS.csv",
                         sep=";",
                         encoding="latin1",
                         header=None)
        
        lista_cuentas = []
        
        for index, fila in df.iterrows():
            if len(fila) < 2: 
                continue
                
            # Intentamos obtener el nombre de la cuenta (columna 1)
            nombre = str(fila[1]).strip()
            
            # Filtramos valores vacíos, títulos del documento o códigos numéricos
            if nombre == "nan" or nombre == "" or "CUENTA" in nombre.upper() or nombre.replace(".", "").isdigit(): 
                continue
            
            tipo = "Otro"
            num_columnas = len(fila)

            # Clasificación por columnas
            if num_columnas > 6 and pd.notna(fila[6]): tipo = "Activo"
            elif num_columnas > 7 and pd.notna(fila[7]): tipo = "Pasivo"
            elif num_columnas > 8 and pd.notna(fila[8]): tipo = "Capital"
            elif num_columnas > 4 and pd.notna(fila[4]): tipo = "Pérdida"
            elif num_columnas > 5 and pd.notna(fila[5]): tipo = "Ganancia"
            
            lista_cuentas.append({"nombre": nombre, "tipo": tipo})
            
        return lista_cuentas
        
    except Exception as e:
        print(f"--- ERROR CRÍTICO AL LEER CSV: {e} ---")
        return []

# =====================================================
# RUTA PARA LA SUGERENCIA EN TIEMPO REAL (AJAX)
# =====================================================

@app.route("/sugerir_tipo")
def sugerir_tipo():
    nombre_buscado = request.args.get("nombre", "").strip().lower()
    if not nombre_buscado:
        return {"tipo_sugerido": "No encontrada"}
        
    todas_las_cuentas = obtener_datos_csv()
    for cuenta in todas_las_cuentas:
        if str(cuenta["nombre"]).strip().lower() == nombre_buscado:
            return {"tipo_sugerido": cuenta["tipo"]}
            
    return {"tipo_sugerido": "No encontrada"}

# =====================================================
# LOGIN
# =====================================================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = hash_password(request.form.get("password"))

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Usuario o contraseña incorrectos"

    return render_template("login.html")

# =====================================================
# REGISTER
# =====================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = hash_password(request.form["password"])

        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect("/")
        except:
            conn.close()
            return "❌ Usuario ya existe"

    return render_template("register.html")

# =====================================================
# DASHBOARD
# =====================================================

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html", user=session["user"])

# =====================================================
# JORNALIZACION (ÚNICA Y CORREGIDA)
# =====================================================

@app.route("/jornalizacion", methods=["GET", "POST"])
def jornalizacion():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        # Si viene fecha del formulario la usa, si no, usa la hora del sistema
        fecha_form = request.form.get("fecha")
        fecha = fecha_form if fecha_form else datetime.now().strftime("%Y-%m-%d %H:%M")

        descripcion = request.form.get("descripcion", "")
        iva_opcion = request.form.get("iva", "no")
        cuenta_debe = request.form.get("cuenta_debe", "")
        cuenta_haber = request.form.get("cuenta_haber", "")

        try:
            debe = float(request.form.get("debe") or 0)
        except:
            debe = 0

        try:
            haber = float(request.form.get("haber") or 0)
        except:
            haber = 0

        if iva_opcion == "si":
            debe = round(debe * 1.12, 2)
            haber = round(haber * 1.12, 2)

        conn = conectar()
        cursor = conn.cursor()

        if cuenta_debe != "":
            cursor.execute("""
            INSERT INTO jornalizacion (fecha, cuenta, debe, haber, descripcion)
            VALUES (?, ?, ?, ?, ?)
            """, (fecha, cuenta_debe, debe, 0, descripcion))

        if cuenta_haber != "":
            cursor.execute("""
            INSERT INTO jornalizacion (fecha, cuenta, debe, haber, descripcion)
            VALUES (?, ?, ?, ?, ?)
            """, (fecha, cuenta_haber, 0, haber, descripcion))

        conn.commit()
        conn.close()
        return redirect("/jornalizacion")

    # MÉTODO GET
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jornalizacion ORDER BY id DESC")
    datos = cursor.fetchall()
    conn.close()

    # Buscamos cuentas para el catálogo de autocompletado
    nombres_cuentas = []
    cuentas_para_lista = obtener_datos_csv()
    if cuentas_para_lista:
        nombres_cuentas = [cuenta['nombre'] for cuenta in cuentas_para_lista]

    return render_template("jornalizacion.html", datos=datos, lista_nombres=nombres_cuentas)

# =====================================================
# EDITAR
# =====================================================

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        cuenta = request.form["cuenta"]
        try:
            debe = float(request.form["debe"] or 0)
        except:
            debe = 0
        try:
            haber = float(request.form["haber"] or 0)
        except:
            haber = 0
        descripcion = request.form["descripcion"]

        cursor.execute("""
        UPDATE jornalizacion
        SET cuenta=?, debe=?, haber=?, descripcion=?
        WHERE id=?
        """, (cuenta, debe, haber, descripcion, id))
        conn.commit()
        conn.close()
        return redirect("/jornalizacion")

    cursor.execute("SELECT * FROM jornalizacion WHERE id=?", (id,))
    dato = cursor.fetchone()
    conn.close()
    return render_template("editar.html", dato=dato)

# =====================================================
# ELIMINAR
# =====================================================

@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jornalizacion WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/jornalizacion")

# =====================================================
# DIARIO MAYOR
# =====================================================

@app.route("/diario_mayor")
def diario_mayor():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, fecha, cuenta, debe, haber, descripcion FROM jornalizacion ORDER BY id DESC")
    diario = cursor.fetchall()

    cursor.execute("""
    SELECT cuenta, SUM(debe) as total_debe, SUM(haber) as total_haber, SUM(debe - haber) as saldo
    FROM jornalizacion GROUP BY cuenta
    """)
    mayor = cursor.fetchall()
    conn.close()
    return render_template("diario_mayor.html", diario=diario, mayor=mayor)

# =====================================================
# BALANCE SALDOS
# =====================================================

@app.route("/balance_saldos")
def balance_saldos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT cuenta, SUM(debe) as total_debe, SUM(haber) as total_haber, SUM(debe - haber) as saldo
    FROM jornalizacion GROUP BY cuenta
    """)
    balances = cursor.fetchall()
    conn.close()
    return render_template("balance_saldos.html", balances=balances)

# =====================================================
# ESTADO RESULTADOS
# =====================================================

@app.route("/estado_resultados")
def estado_resultados():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(haber) FROM jornalizacion")
    ingresos = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(debe) FROM jornalizacion")
    gastos = cursor.fetchone()[0] or 0

    utilidad = ingresos - gastos
    conn.close()
    return render_template("estado_resultados.html", ingresos=ingresos, gastos=gastos, utilidad=utilidad)

# =====================================================
# BALANCE GENERAL
# =====================================================

@app.route("/balance_general")
def balance_general():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(debe) FROM jornalizacion")
    activos = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(haber) FROM jornalizacion")
    pasivos = cursor.fetchone()[0] or 0

    capital = activos - pasivos
    conn.close()
    return render_template("balance_general.html", activos=activos, pasivos=pasivos, capital=capital)

# =====================================================
# ESTADOS FINANCIEROS
# =====================================================

@app.route("/estados_financieros")
def estados_financieros():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(debe) FROM jornalizacion")
    total_debe = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(haber) FROM jornalizacion")
    total_haber = cursor.fetchone()[0] or 0
    conn.close()
    return render_template("estados_financieros.html", total_debe=total_debe, total_haber=total_haber)

# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# =====================================================
# EJECUTAR
# =====================================================

if __name__ == "__main__":
    app.run(debug=True)