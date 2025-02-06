import pandas as pd
import json

def save_json_to_file(json_data, output_path):
    """Save JSON data to a file."""
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4, ensure_ascii=False)
    return output_path

def excel_to_json(excel_path, max_rows=None):
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
    output_path = "unicef/datamerge/json/"
    json_data = excel_to_json(exel_path, max_rows)
    output_path_name = output_path + output_filename
    output_path = save_json_to_file(json_data, output_path_name)
    return output_path
