import pandas as pd

try:

    cuentas = pd.read_csv('CLASIFICACION-CUENTAS.csv', 
                         sep=";", 
                         encoding="latin1", 
                         skiprows=5, 
                         header=None)

   
    print("--- Procesando Cuentas Contables ---")

    for index, fila in cuentas.iterrows():
    
        nombre_cuenta = str(fila[1]).strip()

        if nombre_cuenta == 'nan' or nombre_cuenta == '':
            continue

        tipo = "Desconocido"
    
        if pd.notna(fila[6]):
            tipo = "Activo"
        elif pd.notna(fila[7]):
            tipo = "Pasivo"
        elif len(fila) > 8 and pd.notna(fila[8]): # Verificamos si existe la col 8
            tipo = "Capital"
        elif pd.notna(fila[4]):
            tipo = "Pérdida"
        elif pd.notna(fila[5]):
            tipo = "Ganancia"

        print(f"Cuenta: {nombre_cuenta} -> Clasificación: {tipo}")

except Exception as e:
    print(f"Error: {e}")