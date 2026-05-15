import pandas as pd

nombres_columnas = [
    'No', 'Cuenta', 'Costo_Debe', 'Costo_Haber', 
    'Perdida', 'Ganancia', 'Activo', 'Pasivo'
]

df_cuentas = pd.read_csv('CLASIFICACION-CUENTAS.csv', skiprows=4 names=nombres_columnas,sep=";", encoding="latin1")

catalogo = {}

for index, fila in df_cuentas.iterrows():
    nombre_cuenta = str(fila['Cuenta']).strip()
    
    if pd.isna(nombre_cuenta) or nombre_cuenta == 'nan':
        continue
        
    tipo = "Desconocido"
    if pd.notna(fila['Activo']):
        tipo = "Activo"
    elif pd.notna(fila['Pasivo']):
        tipo = "Pasivo"
    elif pd.notna(fila['Perdida']):
        tipo = "Pérdida (Estado de Resultados)"
    elif pd.notna(fila['Ganancia']):
        tipo = "Ganancia (Estado de Resultados)"
    elif pd.notna(fila['Costo_Debe']) or pd.notna(fila['Costo_Haber']):
        tipo = "Costo de Producción"
        
    catalogo[nombre_cuenta] = tipo

def sugerir_cuentas(texto):
    """Devuelve una lista de cuentas que coincidan con el texto ingresado"""
    sugerencias = []
    for cuenta in catalogo.keys():
        if texto.lower() in cuenta.lower():
            sugerencias.append(cuenta)
    return sugerencias

def procesar_cuenta(cuenta_ingresada):
    """Valida si la cuenta existe y dice qué tipo es"""
    if cuenta_ingresada in catalogo:
        tipo = catalogo[cuenta_ingresada]
        print(f"✅ Éxito: Seleccionaste '{cuenta_ingresada}'. Es una cuenta de {tipo}.")
    else:
        print(f"❌ Error: La cuenta '{cuenta_ingresada}' no es válida.")


print("--- PRUEBA DE SUGERENCIAS ---")

print("Si escribo 'acreedor', me sugiere:")
print(sugerir_cuentas("acreedor"))

print("\n--- PRUEBA DE VALIDACIÓN ---")
# Usamos cuentas que se ven en tu foto
procesar_cuenta("Acciones por suscribir") 
procesar_cuenta("Acreedores a Largo Plazo") 
procesar_cuenta("Cuenta Inventada")