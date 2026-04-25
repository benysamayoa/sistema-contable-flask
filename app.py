from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib
from database import crear_base_datos, guardar_jornalizacion, obtener_jornalizacion

app = Flask(__name__)
app.secret_key = "clave_super_segura_123"

# ------------------------
# Crear base de datos usuarios
# ------------------------
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
    conn.commit()
    conn.close()

init_db()
crear_base_datos()

# ------------------------
# Encriptar contraseña
# ------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------------
# Login
# ------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hash_password(request.form["password"])

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Credenciales incorrectas"

    return render_template("login.html")

# ------------------------
# Registro
# ------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = hash_password(request.form["password"])

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect("/")
        except:
            conn.close()
            return "Usuario ya existe"

    return render_template("register.html")

# ------------------------
# Dashboard
# ------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html", user=session["user"])

# ------------------------
# JORNALIZACIÓN REAL 
# ------------------------
@app.route("/jornalizacion", methods=["GET", "POST"])
def jornalizacion():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        fecha = request.form["fecha"]
        descripcion = request.form["descripcion"]

        cuenta_debe = request.form["cuenta_debe"]
        cuenta_haber = request.form["cuenta_haber"]

        debe = float(request.form["debe"] or 0)
        haber = float(request.form["haber"] or 0)

        if debe != haber:
            return "❌ Error: Debe y Haber deben ser iguales"

        # guardar ambas líneas
        guardar_jornalizacion(fecha, cuenta_debe, debe, 0, descripcion)
        guardar_jornalizacion(fecha, cuenta_haber, 0, haber, descripcion)

        return redirect("/jornalizacion")

    datos = obtener_jornalizacion()
    return render_template("jornalizacion.html", datos=datos)

# ------------------------
# Logout
# ------------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# ------------------------
# Ejecutar
# ------------------------
if __name__ == "__main__":
    app.run(debug=True)