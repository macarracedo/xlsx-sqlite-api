import pandas as pd
import json

def save_json_to_file(json_data, output_path):
    """Save JSON data to a file."""
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4, ensure_ascii=False)
    return output_path

def excel2_to_json(excel_path, max_rows=None):
    """
    Genera un archivo JSON a partir de un archivo XLSX con información de colegios.

    Args:
        archivo_xlsx (str): Ruta al archivo XLSX de entrada.

    Returns:
        str: Un string JSON con el formato especificado.
    """

    try:
        df = pd.read_excel(archivo_xlsx)
    except FileNotFoundError:
        return json.dumps({"error": "Archivo no encontrado"}, indent=4, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Error al leer el archivo: {str(e)}"}, indent=4, ensure_ascii=False)

    # Eliminar filas con valores NaN en la columna 'Unnamed: 0'
    df = df[df['Unnamed: 0'].notna()]

    # Renombrar columnas para facilitar el acceso
    df.rename(columns={'Unnamed: 0': 'CENTRO',
                       'Unnamed: 1': 'CA',
                       'Unnamed: 2': 'Codigo interno_pri',
                       'Unnamed: 3': 'Url_pri',
                       'Unnamed: 5': 'Codigo interno_sec',
                       'Unnamed: 6': 'Url_sec',
                       'Unnamed: 8': 'Codigo interno_pro',
                       'Unnamed: 9': 'Url_pro'}, inplace=True)

    # Filtrar las columnas necesarias
    df = df[['CENTRO', 'CA', 'Codigo interno_pri', 'Url_pri', 'Codigo interno_sec', 'Url_sec', 'Codigo interno_pro', 'Url_pro']]

    # Eliminar filas donde la columna 'CENTRO' es igual a 'CENTRO' (cabecera)
    df = df[df['CENTRO'] != 'CENTRO']

    # Función auxiliar para extraer el sid de la URL
    def extraer_sid(url):
        if pd.isna(url):
            return None
        try:
            return url.split("sid=")[1]
        except IndexError:
            return None

    colegios = []
    for index, row in df.iterrows():
        #Para evitar errores, verificar que las celdas tengan contenido antes de intentar acceder a ellas
        nombre = row['CENTRO'] if pd.notna(row['CENTRO']) else ""
        comunidad_autonoma = row['CA'] if pd.notna(row['CA']) else ""
        codigo_interno_pri = row['Codigo interno_pri'] if pd.notna(row['Codigo interno_pri']) else ""
        codigo_interno_sec = row['Codigo interno_sec'] if pd.notna(row['Codigo interno_sec']) else ""
        codigo_interno_pro = row['Codigo interno_pro'] if pd.notna(row['Codigo interno_pro']) else ""

        pri_sid = extraer_sid(row['Url_pri'])
        sec_sid = extraer_sid(row['Url_sec'])
        pro_sid = extraer_sid(row['Url_pro'])

        colegio = {
            "cid": codigo_interno_pri if codigo_interno_pri else (codigo_interno_sec if codigo_interno_sec else codigo_interno_pro),
            "nombre": nombre,
            "comunidad_autonoma": comunidad_autonoma,
            "telefono": "",
            "email": "",
            "pri_sid": pri_sid,
            "pro_sid": pro_sid,
            "sec_sid": sec_sid
        }
        colegios.append(colegio)

    return json.dumps({"colegios": colegios}, indent=4, ensure_ascii=False)

# Función auxiliar para procesar el archivo XLSX (oculta para esta respuesta)
def _procesar_datos_xlsx(archivo_xlsx):
    """
    Procesa el archivo XLSX y devuelve una lista de diccionarios con la información de los colegios.
    """
    try:
        df = pd.read_excel(archivo_xlsx, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Error al leer el archivo XLSX: {str(e)}")

    # Eliminar filas con valores NaN en la columna 'Unnamed: 0'
    df = df[df['Unnamed: 0'].notna()]

    # Renombrar columnas para facilitar el acceso
    df.rename(columns={'Unnamed: 0': 'CENTRO',
                       'Unnamed: 1': 'CA',
                       'Unnamed: 2': 'Codigo interno_pri',
                       'Unnamed: 3': 'Url_pri',
                       'Unnamed: 5': 'Codigo interno_sec',
                       'Unnamed: 6': 'Url_sec',
                       'Unnamed: 8': 'Codigo interno_pro',
                       'Unnamed: 9': 'Url_pro'}, inplace=True)

    # Filtrar las columnas necesarias
    df = df[['CENTRO', 'CA', 'Codigo interno_pri', 'Url_pri', 'Codigo interno_sec', 'Url_sec', 'Codigo interno_pro', 'Url_pro']]

    # Eliminar filas donde la columna 'CENTRO' es igual a 'CENTRO' (cabecera)
    df = df[df['CENTRO'] != 'CENTRO']

    # Función auxiliar para extraer el sid de la URL
    def extraer_sid(url):
        if pd.isna(url):
            return None
        try:
            return url.split("sid=")[1]
        except IndexError:
            return None

    colegios = []
    for index, row in df.iterrows():
        #Para evitar errores, verificar que las celdas tengan contenido antes de intentar acceder a ellas
        nombre = row['CENTRO'] if pd.notna(row['CENTRO']) else ""
        comunidad_autonoma = row['CA'] if pd.notna(row['CA']) else ""
        codigo_interno_pri = row['Codigo interno_pri'] if pd.notna(row['Codigo interno_pri']) else ""
        codigo_interno_sec = row['Codigo interno_sec'] if pd.notna(row['Codigo interno_sec']) else ""
        codigo_interno_pro = row['Codigo interno_pro'] if pd.notna(row['Codigo interno_pro']) else ""

        pri_sid = extraer_sid(row['Url_pri'])
        sec_sid = extraer_sid(row['Url_sec'])
        pro_sid = extraer_sid(row['Url_pro'])

        colegio = {
            "cid": codigo_interno_pri if codigo_interno_pri else (codigo_interno_sec if codigo_interno_sec else codigo_interno_pro),
            "nombre": nombre,
            "comunidad_autonoma": comunidad_autonoma,
            "telefono": "",
            "email": "",
            "pri_sid": pri_sid,
            "pro_sid": pro_sid,
            "sec_sid": sec_sid
        }
        colegios.append(colegio)

    return colegios

def excel1_to_json(excel_path, max_rows=None):
    """Convert Excel data to JSON and save to a file."""
    # Cargar el archivo Excel
    df = pd.read_excel(excel_path)
    
    # Filtrar las primeras 'max_rows' filas si se especifica
    if max_rows:
        df = df.iloc[:max_rows]
    
    colegios = {}
    
    for _, row in df.iterrows():
        cid = row["ID DE CENTRO"].split(" - ")[0]  # Extraer código del colegio
        nombre = row["AN"]
        comunidad = row["CCAA"] if row["CCAA"] != "NO TIENE" else ""
        ssid = row["SSID"]
        nivel = row["ID DE CENTRO"].split(" - ")[1]  # Obtener el nivel (Primaria, Profesorado, Secundaria)
        
        if cid not in colegios:
            colegios[cid] = {
                "cid": cid,
                "nombre": nombre,
                "comunidad_autonoma": comunidad,
                "telefono": "",
                "email": "",
                "pri_sid": "",
                "pro_sid": "",
                "sec_sid": "",
            }
        
        # Asignar SSID según el nivel
        if "Primaria" in nivel:
            colegios[cid]["pri_sid"] = str(ssid)
        elif "Profesorado" in nivel:
            colegios[cid]["pro_sid"] = str(ssid)
        elif "Secundaria" in nivel:
            colegios[cid]["sec_sid"] = str(ssid)
    
    # Convertir a formato JSON
    json_data = {"colegios": list(colegios.values())}
    
    return json_data

def excel_to_json_file(exel_path, output_filename="colegios_encuestas_output.json", max_rows=None):
    """Convert Excel data to JSON and save to a file using functions."""
    
    # Ejemplo de uso:
    archivo_xlsx = 'Lote-2-Antonio-Febrero-7.xlsx'  # Reemplaza con la ruta correcta a tu archivo
    json_output = excel2_to_json(archivo_xlsx)

    # Imprimir el JSON resultante (opcional)
    print(json_output)
        
    output_path = "unicef/datamerge/json/"
    json_data = excel1_to_json(exel_path, max_rows)
    output_path_name = output_path + output_filename
    output_path = save_json_to_file(json_data, output_path_name)
    return output_path
