from flask import Flask, render_template, request, redirect, session, flash, jsonify
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import os
from collections import defaultdict


app = Flask(__name__)
app.secret_key = "clave_super_segura_123"


def conectar():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


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

def obtener_balance_saldos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cuenta,
               SUM(debe),
               SUM(haber)
        FROM jornalizacion
        GROUP BY cuenta
        ORDER BY cuenta
    """)

    filas = cursor.fetchall()
    conn.close()

    datos = []

    for fila in filas:
        cuenta = fila[0]
        debe = fila[1] or 0
        haber = fila[2] or 0
        saldo = debe - haber

        datos.append({
            "cuenta": cuenta,
            "debe": debe,
            "haber": haber,
            "saldo": saldo
        })

    return datos


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def obtener_datos_csv():
    try:
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        ruta_csv = os.path.join(ruta_base, "CLASIFICACION-CUENTAS.csv")

        df = pd.read_csv(ruta_csv, sep=";", encoding="utf-8", header=None)
    except:
        try:
            ruta_base = os.path.dirname(os.path.abspath(__file__))
            ruta_csv = os.path.join(ruta_base, "CLASIFICACION-CUENTAS.csv")
            df = pd.read_csv(ruta_csv, sep=";", encoding="latin1", header=None)
        except:
            return []

    lista_cuentas = []
    for index, fila in df.iterrows():
        if len(fila) < 2: continue
        nombre = str(fila[1]).strip()
        if nombre == "nan" or nombre == "" or "CUENTA" in nombre.upper() or nombre.replace(".", "").isdigit(): 
            continue

        tipo = "Otro"
        num_columnas = len(fila)
        if num_columnas > 6 and pd.notna(fila[6]): tipo = "Activo"
        elif num_columnas > 7 and pd.notna(fila[7]): tipo = "Pasivo"
        elif num_columnas > 8 and pd.notna(fila[8]): tipo = "Capital"
        elif num_columnas > 4 and pd.notna(fila[4]): tipo = "Perdida"
        elif num_columnas > 5 and pd.notna(fila[5]): tipo = "Ganancia"
        
        lista_cuentas.append({"nombre": nombre, "tipo": tipo})
    return lista_cuentas


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = hash_password(request.form.get("password") or "")
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session["user"] = username
            return redirect("/dashboard")
        flash("Usuario o contrasena incorrectos", "danger")
    return render_template("login.html")


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
            flash("El usuario ya existe", "danger")
            return redirect("/register")
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect("/")
    return render_template("dashboard.html", user=session["user"])


@app.route("/sugerir_tipo")
def sugerir_tipo():
    nombre_buscado = request.args.get("nombre", "").strip().lower()
    if not nombre_buscado: return jsonify({"tipo_sugerido": "No encontrada"})
    for cuenta in obtener_datos_csv():
        if str(cuenta["nombre"]).strip().lower() == nombre_buscado:
            return jsonify({"tipo_sugerido": cuenta["tipo"]})
    return jsonify({"tipo_sugerido": "No encontrada"})




@app.route("/jornalizacion", methods=["GET", "POST"])
def jornalizacion():
    if "user" not in session: return redirect("/")

    if request.method == "POST":
        datos_json = request.get_json()
        fecha = datos_json.get("fecha") or datetime.now().strftime("%Y-%m-%d")
        descripcion = datos_json.get("descripcion", "")
        movimientos = datos_json.get("movimientos", [])

        if not movimientos:
            return jsonify({"status": "error", "message": "No hay cuentas"}), 400

        conn = conectar()
        cursor = conn.cursor()
        nuevos_registros = []

        for mov in movimientos:
            cuenta = mov.get("cuenta")
            debe = float(mov.get("debe") or 0)
            haber = float(mov.get("haber") or 0)

            cursor.execute("""
            INSERT INTO jornalizacion (fecha, cuenta, debe, haber, descripcion)
            VALUES (?, ?, ?, ?, ?)
            """, (fecha, cuenta, debe, haber, descripcion))
            
            nuevos_registros.append({
                "Fecha": fecha,
                "Cuenta": cuenta,
                "Debe": debe,
                "Haber": haber,
                "Descripcion": descripcion
            })

        conn.commit()
        conn.close()

        archivo_excel = "Libro_Diario.xlsx"
        try:
            if os.path.exists(archivo_excel):
                df_existente = pd.read_excel(archivo_excel)
                df_nuevo = pd.DataFrame(nuevos_registros)
                df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
            else:
                df_final = pd.DataFrame(nuevos_registros)
            
            df_final.to_excel(archivo_excel, index=False)
        except Exception as e:
            print(f"Error: {e}")

        return jsonify({"status": "success", "message": "Ok"})


    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jornalizacion ORDER BY id DESC")
    filas_raw = cursor.fetchall()
    conn.close()

    datos = []
    for fila in filas_raw:
        id_reg = fila[0]
        fecha = fila[1]
        cuenta = fila[2] or ""
        debe = fila[3]
        haber = fila[4]
        descripcion = fila[5] or ""
        
        try:
            cuenta_limpia = cuenta.encode('latin1').decode('utf-8')
        except:
            try:
                cuenta_limpia = cuenta.encode('raw_unicode_escape').decode('utf-8')
            except:
                cuenta_limpia = cuenta

        try:
            desc_limpia = descripcion.encode('latin1').decode('utf-8')
        except:
            try:
                desc_limpia = descripcion.encode('raw_unicode_escape').decode('utf-8')
            except:
                desc_limpia = descripcion

        datos.append([id_reg, fecha, cuenta_limpia, debe, haber, desc_limpia])

    cuentas_para_lista = obtener_datos_csv()
    nombres_cuentas = [c['nombre'] for c in cuentas_para_lista] if cuentas_para_lista else []

    return render_template("jornalizacion.html", datos=datos, lista_nombres=nombres_cuentas)


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        cuenta = request.form["cuenta"]
        try: debe = float(request.form["debe"] or 0)
        except: debe = 0
        try: haber = float(request.form["haber"] or 0)
        except: haber = 0
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


@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jornalizacion WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/jornalizacion")


@app.route("/ver_jornalizacion")
def ver_jornalizacion():
    if "user" not in session:
        return redirect("/")

    fecha = request.args.get("fecha")
    semana = request.args.get("semana")
    mes = request.args.get("mes")
    anio = request.args.get("anio")

    conn = conectar()
    cursor = conn.cursor()

    query = "SELECT * FROM jornalizacion WHERE 1=1"
    params = []

    # 📅 FILTRO POR DÍA
    if fecha:
        query += " AND fecha = ?"
        params.append(fecha)

    # 📆 FILTRO POR MES
    if mes:
        query += " AND fecha LIKE ?"
        params.append(f"{mes}%")

    # 🗓 FILTRO POR AÑO
    if anio:
        query += " AND fecha LIKE ?"
        params.append(f"{anio}%")

    # 📊 FILTRO POR SEMANA (simple)
    if semana:
        query += " AND strftime('%W', fecha) = ? AND strftime('%Y', fecha) = ?"
        params.append(semana.split("-W")[1])
        params.append(semana.split("-W")[0])

    query += " ORDER BY fecha DESC, id DESC"

    cursor.execute(query, params)
    filas = cursor.fetchall()
    conn.close()

    datos = []
    for fila in filas:
        datos.append({
            "id": fila[0],
            "fecha": fila[1],
            "cuenta": fila[2],
            "debe": fila[3],
            "haber": fila[4],
            "descripcion": fila[5]
        })

    return render_template("ver_jornalizacion.html", datos=datos)



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

@app.route("/balance")
def vista_balance_saldos():

    if "user" not in session:
        return redirect("/")

    datos = obtener_balance_saldos()

    return render_template(
        "balance_saldos.html",
        datos=datos
    )




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


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
