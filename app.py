from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib
from datetime import datetime

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

    return hashlib.sha256(
        password.encode()
    ).hexdigest()

# =====================================================
# LOGIN
# =====================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = hash_password(
            request.form["password"]
        )

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM users
        WHERE username=? AND password=?
        """, (
            username,
            password
        ))

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user"] = username

            return redirect("/dashboard")

        else:

            return "❌ Credenciales incorrectas"

    return render_template("login.html")

# =====================================================
# REGISTER
# =====================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]

        password = hash_password(
            request.form["password"]
        )

        conn = conectar()
        cursor = conn.cursor()

        try:

            cursor.execute("""
            INSERT INTO users
            (username, password)
            VALUES (?, ?)
            """, (
                username,
                password
            ))

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

    return render_template(
        "dashboard.html",
        user=session["user"]
    )

# =====================================================
# JORNALIZACION
# =====================================================

@app.route("/jornalizacion", methods=["GET", "POST"])
def jornalizacion():

    if "user" not in session:

        return redirect("/")

    if request.method == "POST":

        fecha = datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        descripcion = request.form.get(
            "descripcion",
            ""
        )

        tipo = request.form.get(
            "tipo",
            "manual"
        )

        iva_opcion = request.form.get(
            "iva",
            "no"
        )

        cuenta_debe = request.form.get(
            "cuenta_debe",
            ""
        )

        cuenta_haber = request.form.get(
            "cuenta_haber",
            ""
        )

        # =========================================
        # OBTENER CIFRAS
        # =========================================

        try:

            debe = float(
                request.form.get("debe") or 0
            )

        except:

            debe = 0

        try:

            haber = float(
                request.form.get("haber") or 0
            )

        except:

            haber = 0

        # =========================================
        # IVA
        # =========================================

        if iva_opcion == "si":

            debe = round(debe * 1.12, 2)
            haber = round(haber * 1.12, 2)

        conn = conectar()
        cursor = conn.cursor()

        # =========================================
        # GUARDAR DEBE
        # =========================================

        if cuenta_debe != "":

            cursor.execute("""
            INSERT INTO jornalizacion
            (fecha, cuenta, debe, haber, descripcion)
            VALUES (?, ?, ?, ?, ?)
            """, (
                fecha,
                cuenta_debe,
                debe,
                0,
                descripcion
            ))

        # =========================================
        # GUARDAR HABER
        # =========================================

        if cuenta_haber != "":

            cursor.execute("""
            INSERT INTO jornalizacion
            (fecha, cuenta, debe, haber, descripcion)
            VALUES (?, ?, ?, ?, ?)
            """, (
                fecha,
                cuenta_haber,
                0,
                haber,
                descripcion
            ))

        conn.commit()
        conn.close()

        return redirect("/jornalizacion")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM jornalizacion
    ORDER BY id DESC
    """)

    datos = cursor.fetchall()

    conn.close()

    return render_template(
        "jornalizacion.html",
        datos=datos
    )

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

            debe = float(
                request.form["debe"] or 0
            )

        except:

            debe = 0

        try:

            haber = float(
                request.form["haber"] or 0
            )

        except:

            haber = 0

        descripcion = request.form["descripcion"]

        cursor.execute("""
        UPDATE jornalizacion
        SET
            cuenta=?,
            debe=?,
            haber=?,
            descripcion=?
        WHERE id=?
        """, (
            cuenta,
            debe,
            haber,
            descripcion,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/jornalizacion")

    cursor.execute("""
    SELECT *
    FROM jornalizacion
    WHERE id=?
    """, (id,))

    dato = cursor.fetchone()

    conn.close()

    return render_template(
        "editar.html",
        dato=dato
    )

# =====================================================
# ELIMINAR
# =====================================================

@app.route("/eliminar/<int:id>")
def eliminar(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM jornalizacion
    WHERE id=?
    """, (id,))

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

    cursor.execute("""
    SELECT
        id,
        fecha,
        cuenta,
        debe,
        haber,
        descripcion
    FROM jornalizacion
    ORDER BY id DESC
    """)

    diario = cursor.fetchall()

    cursor.execute("""
    SELECT
        cuenta,
        SUM(debe) as total_debe,
        SUM(haber) as total_haber,
        SUM(debe - haber) as saldo
    FROM jornalizacion
    GROUP BY cuenta
    """)

    mayor = cursor.fetchall()

    conn.close()

    return render_template(
        "diario_mayor.html",
        diario=diario,
        mayor=mayor
    )

# =====================================================
# BALANCE SALDOS
# =====================================================

@app.route("/balance_saldos")
def balance_saldos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        cuenta,
        SUM(debe) as total_debe,
        SUM(haber) as total_haber,
        SUM(debe - haber) as saldo
    FROM jornalizacion
    GROUP BY cuenta
    """)

    balances = cursor.fetchall()

    conn.close()

    return render_template(
        "balance_saldos.html",
        balances=balances
    )

# =====================================================
# ESTADO RESULTADOS
# =====================================================

@app.route("/estado_resultados")
def estado_resultados():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(haber)
    FROM jornalizacion
    """)

    ingresos = cursor.fetchone()[0] or 0

    cursor.execute("""
    SELECT SUM(debe)
    FROM jornalizacion
    """)

    gastos = cursor.fetchone()[0] or 0

    utilidad = ingresos - gastos

    conn.close()

    return render_template(
        "estado_resultados.html",
        ingresos=ingresos,
        gastos=gastos,
        utilidad=utilidad
    )

# =====================================================
# BALANCE GENERAL
# =====================================================

@app.route("/balance_general")
def balance_general():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(debe)
    FROM jornalizacion
    """)

    activos = cursor.fetchone()[0] or 0

    cursor.execute("""
    SELECT SUM(haber)
    FROM jornalizacion
    """)

    pasivos = cursor.fetchone()[0] or 0

    capital = activos - pasivos

    conn.close()

    return render_template(
        "balance_general.html",
        activos=activos,
        pasivos=pasivos,
        capital=capital
    )

# =====================================================
# ESTADOS FINANCIEROS
# =====================================================

@app.route("/estados_financieros")
def estados_financieros():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(debe)
    FROM jornalizacion
    """)

    total_debe = cursor.fetchone()[0] or 0

    cursor.execute("""
    SELECT SUM(haber)
    FROM jornalizacion
    """)

    total_haber = cursor.fetchone()[0] or 0

    conn.close()

    return render_template(
        "estados_financieros.html",
        total_debe=total_debe,
        total_haber=total_haber
    )

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
