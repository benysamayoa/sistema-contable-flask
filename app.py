from flask import Flask, render_template, request, redirect, session, flash, jsonify, send_file
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import os
from io import BytesIO

app = Flask(__name__)
app.secret_key = "clave_super_segura_123"

MESES_ESPANOL = {
    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
}

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
        descripcion TEXT,
        numero_partida INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_db()

def obtener_balance_saldos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cuenta, SUM(debe), SUM(haber)
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
        datos.append({"cuenta": cuenta, "debe": debe, "haber": haber, "saldo": saldo})
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

        try:
            dt_obj = datetime.strptime(fecha, "%Y-%m-%d")
            prefijo_mes = f"{dt_obj.year}-{dt_obj.month:02d}%"
        except:
            prefijo_mes = datetime.now().strftime("%Y-%m-%d")[:7] + "%"

        conn = conectar()
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(numero_partida) FROM jornalizacion WHERE fecha LIKE ?", (prefijo_mes,))
        ultimo_numero = cursor.fetchone()[0]
        nuevo_numero_partida = 1 if ultimo_numero is None else ultimo_numero + 1

        for mov in movimientos:
            cuenta = mov.get("cuenta")
            debe = float(mov.get("debe") or 0)
            haber = float(mov.get("haber") or 0)

            cursor.execute("""
            INSERT INTO jornalizacion (fecha, cuenta, debe, haber, descripcion, numero_partida)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (fecha, cuenta, debe, haber, descripcion, nuevo_numero_partida))

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Ok"})

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jornalizacion ORDER BY fecha ASC, numero_partida ASC, id ASC")
    filas_raw = cursor.fetchall()
    conn.close()

    cronologia = {}

    for fila in filas_raw:
        id_reg = fila[0]
        fecha = fila[1] or datetime.now().strftime("%Y-%m-%d")
        cuenta = fila[2] or ""
        debe = fila[3]
        haber = fila[4]
        descripcion = fila[5] or ""
        num_partida = fila[6] or 1

        try:
            dt = datetime.strptime(fecha, "%Y-%m-%d")
            anio = str(dt.year)
            mes_cod = f"{dt.month:02d}"
        except:
            anio = datetime.now().strftime("%Y")
            mes_cod = datetime.now().strftime("%m")

        mes_nombre = MESES_ESPANOL.get(mes_cod, "Desconocido")

        try: cuenta_limpia = cuenta.encode('latin1').decode('utf-8')
        except: cuenta_limpia = cuenta

        try: desc_limpia = descripcion.encode('latin1').decode('utf-8')
        except: desc_limpia = descripcion

        if anio not in cronologia:
            cronologia[anio] = {}
        if mes_cod not in cronologia[anio]:
            cronologia[anio][mes_cod] = {"nombre": mes_nombre, "partidas": {}}
        if num_partida not in cronologia[anio][mes_cod]["partidas"]:
            cronologia[anio][mes_cod]["partidas"][num_partida] = {
                "fecha": fecha,
                "descripcion": desc_limpia,
                "movimientos": []
            }

        cronologia[anio][mes_cod]["partidas"][num_partida]["movimientos"].append({
            "id": id_reg,
            "cuenta": cuenta_limpia,
            "debe": debe,
            "haber": haber
        })

    cuentas_para_lista = obtener_datos_csv()
    nombres_cuentas = [c['nombre'] for c in cuentas_para_lista] if cuentas_para_lista else []

    return render_template("jornalizacion.html", cronologia=cronologia, lista_nombres=nombres_cuentas)

@app.route("/exportar_excel")
def exportar_excel():
    if "user" not in session: return redirect("/")
    anio = request.args.get("anio")
    mes = request.args.get("mes")

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT numero_partida, fecha, cuenta, debe, haber, descripcion 
        FROM jornalizacion 
        WHERE fecha LIKE ? 
        ORDER BY numero_partida ASC, id ASC
    """, (f"{anio}-{mes}%",))
    filas = cursor.fetchall()
    conn.close()

    if not filas: return "No hay transacciones registradas", 404

    registros = []
    for f in filas:
        registros.append({
            "No. Partida": f[0], "Fecha": f[1], "Cuenta Contable": f[2],
            "Debe (Q)": f[3], "Haber (Q)": f[4], "Descripción": f[5]
        })

    df = pd.DataFrame(registros)
    nombre_mes = MESES_ESPANOL.get(mes, mes)
    
    # SOLUCIÓN EXCEL: Forzar el cierre y vaciado del buffer de forma segura
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name="Libro Diario")
    writer.close()
    output.seek(0)

    return send_file(
        output, download_name=f"Libro_Diario_{nombre_mes}_{anio}.xlsx",
        as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

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
        UPDATE jornalizacion SET cuenta=?, debe=?, haber=?, descripcion=? WHERE id=?
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

@app.route("/eliminar_partida/<anio>/<mes>/<int:num_partida>")
def eliminar_partida(anio, mes, num_partida):
    if "user" not in session: return redirect("/")
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM jornalizacion WHERE fecha LIKE ? AND numero_partida = ?
    """, (f"{anio}-{mes}%", num_partida))
    conn.commit()
    conn.close()
    return redirect("/jornalizacion")

# SOLUCIÓN INTERACTIVA: Libro Mayor General Dinámico
@app.route("/diario_mayor")
def diario_mayor():
    if "user" not in session: return redirect("/")
    
    anio_sel = request.args.get("anio")
    mes_sel = request.args.get("mes")
    cuenta_sel = request.args.get("cuenta")

    conn = conectar()
    cursor = conn.cursor()
    
    # Obtener lista de cuentas únicas existentes en el sistema para el buscador
    cursor.execute("SELECT DISTINCT cuenta FROM jornalizacion ORDER BY cuenta ASC")
    cuentas_existentes = [f[0] for f in cursor.fetchall()]

    movimientos = []
    total_debe = 0.0
    total_haber = 0.0
    saldo = 0.0

    if anio_sel and mes_sel and cuenta_sel:
        # Filtrado inteligente por Periodo y Cuenta especificada
        cursor.execute("""
            SELECT id, fecha, cuenta, debe, haber, descripcion, numero_partida
            FROM jornalizacion
            WHERE fecha LIKE ? AND cuenta = ?
            ORDER BY fecha ASC, id ASC
        """, (f"{anio_sel}-{mes_sel}%", cuenta_sel))
        filas = cursor.fetchall()
        
        for f in filas:
            t_debe = f[3] or 0
            t_haber = f[4] or 0
            total_debe += t_debe
            total_haber += t_haber
            
            movimientos.append({
                "id": f[0], "fecha": f[1], "cuenta": f[2],
                "debe": t_debe, "haber": t_haber, "descripcion": f[5], "partida": f[6]
            })
        saldo = total_debe - total_haber

    conn.close()
    return render_template(
        "diario_mayor.html", 
        cuentas=cuentas_existentes, 
        movimientos=movimientos,
        total_debe=total_debe, 
        total_haber=total_haber, 
        saldo=saldo,
        anio_sel=anio_sel, 
        mes_sel=mes_sel, 
        cuenta_sel=cuenta_sel,
        meses_map=MESES_ESPANOL
    )

@app.route("/balance")
def vista_balance_saldos():
    if "user" not in session: return redirect("/")
    datos = obtener_balance_saldos()
    return render_template("balance_saldos.html", datos=datos)

@app.route("/estado_resultados")
def estado_resultados():
    if "user" not in session: return redirect("/")
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
    if "user" not in session: return redirect("/")
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