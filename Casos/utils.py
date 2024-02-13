import re
import os
import pandas as pd
import time
import csv
from openpyxl import load_workbook

# Función para separar los números de las OV por un regex
def separar_numeros(s, regex_pattern):
    caracteres = [re.escape(c.strip()) for c in regex_pattern.split(',') if c.strip()]

    patron = '|'.join(caracteres)

    # Actualizado para tratar "rev. " seguido de un número como un solo valor
    regex_pattern = rf'(?i)(\d+)(?:{patron}(?:\d+|rev\. [12]\s*\d+))*'  # Actualizado para manejar "rev. 1" y "rev. 2"

    valores = re.findall(regex_pattern, s, flags=re.IGNORECASE)

    return [valor for valor in valores if not re.match(r'^\d$', valor)]

# Función para escribir la columna OV Limpio
def limpiar_ov(valor):
    if str(valor).isdigit():
        return int(valor)
    else:
        return valor

# Función para limpiar la carpeta static de archivos basura
def limpiar_carpeta_static():
    ruta_temporal = 'Limpiados'
    for archivo in os.listdir(ruta_temporal):
        file_path = os.path.join(ruta_temporal, archivo)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"No se pudo eliminar {file_path}. Error: {e}")


# Función para procesar el archivo de Ventas Mayoristas
def procesar_archivo(archivo, regex_pattern, user_id):
    # Orden que tendrá el excel para Ventas Mayoristas
    column_order = ['ID', 'OV', 'OV LIMPIO', 'ID Prefactibilidad', 'Ejecutivo/\ndirector', 'País', 'Fecha Oportunidad', 'Fecha de Cierre Venta', 'Cliente', 'Dirección', 'Zona', 'Detalle', 'Servicio', 'Renta UF', 'Valor UF Cruzada', 'Uf habilitación', 'Plazo contrato', 'Plazo Implementación Min', 'Plazo Implementación Máx', 'Unnamed: 18', 'UF Ajustada', 'VENTA TOTAL', 'Plazo Implementación']

    # Columnas que pueden no existir en ventas Mayoristas y se agregarán.
    columnas = ['Renta UF', 'Valor UF Cruzada', 'Uf habilitación', 'Plazo contrato', 'Plazo Implementación Min', 'Plazo Implementación Máx']

    ruta_raiz = 'Limpiados'
    ruta_usuario = os.path.join(ruta_raiz, user_id)
    
    if not os.path.exists(ruta_usuario):
        os.makedirs(ruta_usuario)

    df = pd.read_excel(archivo, header=0)

    nuevas_filas = []

    for col in columnas:
        if col not in df.columns:
            df[col] = '0'

    # Continuar con el procesamiento como antes
    for _, row in df.iterrows():
        valores_separados = separar_numeros(str(row.get('OV', '')), regex_pattern)

        if not valores_separados:
            nueva_fila = row.copy()
            nueva_fila['OV LIMPIO'] = row.get('OV', '')
            nuevas_filas.append(nueva_fila)
        else:
            for i, valor in enumerate(valores_separados):
                nueva_fila = row.copy()
                nueva_fila['OV'] = valor
                nueva_fila['OV LIMPIO'] = limpiar_ov(valor)

                # Verificar si estamos en la primera fila y el valor aún no se ha llenado
                if i != 0:
                    nueva_fila[columnas] = ''
                
                nuevas_filas.append(nueva_fila)

    df_extendido = pd.DataFrame(nuevas_filas, columns=column_order)
    
    # Guardar el archivo en la carpeta del usuario
    output_path = os.path.join(ruta_usuario, f'limpiado_{user_id}.xlsx')
    df_extendido.to_excel(output_path, index=False)

    # Obtener el nombre original del archivo sin la ruta
    nombre_archivo = os.path.basename(archivo)
    
    # Generar el nombre del archivo de salida
    output_path = os.path.join(ruta_usuario, f'limpiado_{nombre_archivo}')
    
    df_extendido.to_excel(output_path, index=False)

    return output_path

# Función para limpiar los archivos detalles de Netcracker
def limpiar_detalle(archivo, user_id):
    ruta_temporal = 'Detallados'
    ruta_usuario = os.path.join(ruta_temporal, user_id)

    if not os.path.exists(ruta_usuario):
        os.makedirs(ruta_usuario)

    data = []
    max_fields = 0
    try:
        with open(archivo, 'r', encoding='latin1') as file:
            reader = csv.reader(file, delimiter='|')
            for row in reader:
                data.append(row)
                if len(row) > max_fields:
                    max_fields = len(row)

        # Rellenar las filas con menos campos con NaN
        for i in range(len(data)):
            while len(data[i]) < max_fields:
                data[i].append(None)

        # Convertir los datos a un DataFrame
        df = pd.DataFrame(data)
        try: 
            df.iloc[:, 15:] = df.iloc[:, 15:].apply(pd.to_numeric, errors='coerce')
        except Exception as e:
            print(f'Error al convertir a números: {e}')

        nombre_archivo = os.path.basename(archivo)
        try: 
            # Guardar el DataFrame en un archivo Excel
            output_file_path = os.path.join(ruta_usuario, f'Detalle_Separado_{nombre_archivo}.xlsx')
            df.to_excel(output_file_path, index=False)
            return output_file_path
        except Exception as e:
            print(f'Error al guardar el archivo: {e}')
            return None
    except Exception as e:
        print(f'Error al leer el archivo: {e}')
        return None
    

def cargar_archivo(archivos, user_id):
    ruta_temporal = 'Consolidados'
    ruta_usuario = os.path.join(ruta_temporal, user_id)

    if not os.path.exists(ruta_usuario):
        os.makedirs(ruta_usuario)

    df_final = None

    for archivo in archivos:
        try:
            file_path = os.path.join(ruta_usuario, archivo.filename)
            archivo.save(file_path)

            # Lee el DataFrame desde el archivo y agrega a la lista
            df_actual = pd.read_excel(file_path, header=0)

            # Concatena todos los DataFrames en uno solo
            df_final = pd.concat([df_final, df_actual])
        except Exception as e:
            print(f'Error al procesar el archivo {archivo.filename}: {e}')

    try:
        nombre_archivo_final = f'Archivo_Consolidado.xlsx'
        ruta_archivo_final = os.path.join(ruta_usuario, nombre_archivo_final)
        df_final.to_excel(ruta_archivo_final, index=False)

        return ruta_archivo_final

    except Exception as e:
        print(f'Error al guardar el archivo consolidado: {e}')
        return None


    
# Función para realizar una carga de archivos del caso 2 [Consolidar en base a una columna]   
def cargar_archivos(archivos_base, archivos_combinar, user_id):
    ruta_temporal = 'Consolidados'
    ruta_usuario = os.path.join(ruta_temporal, user_id)

    if not os.path.exists(ruta_usuario):
        os.makedirs(ruta_usuario)

    headers_base = None  # Lista para almacenar los encabezados del Archivo Base
    headers_combinar = None  # Lista para almacenar los encabezados del Archivo a Combinar

    saved_files_base = []
    saved_files_combinar = []

    for archivo_base in archivos_base:
        try:
            file_path = os.path.join(ruta_usuario, archivo_base.filename)
            archivo_base.save(file_path)
            saved_files_base.append(file_path)

            # Leer solo los encabezados del archivo con openpyxl
            wb = load_workbook(filename=file_path, read_only=True)
            ws = wb.active
            headers_base = [cell.value for cell in ws[1]]

        except Exception as e:
            print(f'Error al procesar el archivo {archivo_base.filename}: {e}')

    for archivo_combinar in archivos_combinar:
        try:
            file_path = os.path.join(ruta_usuario, archivo_combinar.filename)
            archivo_combinar.save(file_path)
            saved_files_combinar.append(file_path)

            # Leer solo los encabezados del archivo con openpyxl
            wb = load_workbook(filename=file_path, read_only=True)
            ws = wb.active
            headers_combinar = [cell.value for cell in ws[1]]

        except Exception as e:
            print(f'Error al procesar el archivo {archivo_combinar.filename}: {e}')

    return saved_files_base, headers_base, saved_files_combinar, headers_combinar



def consolidar_archivos(archivo_base, archivos_combinar, header_base, header_combinar, user_id):
    ruta_temporal = 'Consolidados'
    ruta_usuario = os.path.join(ruta_temporal, user_id)

    if not os.path.exists(ruta_usuario):
        os.makedirs(ruta_usuario)

    try:
        archivo_base = os.path.normpath(archivo_base)
        archivos_combinar = [os.path.normpath(archivo) for archivo in archivos_combinar]
        df_base = pd.read_excel(archivo_base, header=0)
        start_time = time.time()
        # Leer y combinar los archivos a fusionar
        for archivo_combinar in archivos_combinar:
            df_combinar = pd.read_excel(archivo_combinar, header=0)

            df_base = pd.merge(df_base, df_combinar, left_on=header_base, right_on=header_combinar, how='left')
            
        end_time = time.time()
        print(f'Tiempo de ejecución para el merge: {end_time - start_time} segundos')

        nombre_archivo_base = os.path.basename(archivo_base) 
        # Guardar el resultado en un nuevo archivo
        resultado_path = os.path.join(ruta_usuario,  f'Consolidación_para_{nombre_archivo_base}')
        df_base.to_excel(resultado_path, index=False)

        return resultado_path

    except Exception as e:
        print(f'Error al consolidar archivos: {e}')
        return None
