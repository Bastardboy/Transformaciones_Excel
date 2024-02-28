from flask import Flask, render_template, request, send_from_directory, session, abort, jsonify, make_response
import os
import uuid
from Casos.utils import procesar_multiples_archivos, limpiar_detalle, cargar_archivos, consolidar_archivos, cargar_archivo, cargar_archivos_limpiar, descargar_en_paralelo, eliminar_archivo_despues_de_tiempo
import threading


#logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(message)s')

app = Flask(__name__)
UPLOAD_FOLDER = 'Folios'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'tu_clave_secreta_super_secreta'  # Cambia esto a una cadena segura
#logging.info('El servidor ha iniciado')

@app.route('/obtener_columnas', methods=['GET'])
def obtener_columnas():
    columnas = session.get('columnas_combinar', [])
    return jsonify({'columnas_combinar': columnas})

# Filtro para obtener el nombre base de un archivo
@app.template_filter('basename')
def basename_filter(s):
    return os.path.basename(s)
app.jinja_env.filters['basename'] = basename_filter

# RUTAS DE DESCARGA DE ARCHIVOS. SI SE QUIERE AGREGAR UNA NUEVA RUTA, SE DEBE AGREGAR UNA NUEVA FUNCIÓN Y ASIGNARLA EN EL HTML

@app.route('/limpiar_archivos/<user_id>/<filename>', methods=['GET'])
def limpiados(user_id, filename):
    ruta_limpiados = os.path.join('Limpiados', user_id)

    try:
        filename = os.path.basename(filename)
        return send_from_directory(ruta_limpiados, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route('/detallados/<user_id>/<filename>', methods=['GET'])
def detallados(user_id, filename):
    ruta_detallados = os.path.join('Detallados', user_id)

    try:
        filename = os.path.basename(filename)
        return send_from_directory(ruta_detallados, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route('/consolidados/<user_id>/<filename>', methods=['GET'])
def consolidados(user_id, filename):
    
    ruta_consolidados = os.path.join('Consolidados', user_id)

    try:
        print(f'ID de usuario que se obtiene dentro de la función Consolidados: {user_id}')

        return send_from_directory(ruta_consolidados, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

# RUTAS PARA EL PROCESAMIENTO DE ARCHIVOS

# RUTAS PARA EL PROCESO DE LIMPIAR ARCHIVOS EN BASE A UN REGEX
@app.route('/limpiar', methods=['GET', 'POST'])
def limpiar():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('file[]')
        user_id = session.get('user_id')
        ruta_temporal = 'Limpiados'
        ruta_usuario = os.path.join(ruta_temporal, user_id)

        if not os.path.exists(ruta_usuario):
            os.makedirs(ruta_usuario)

        output_paths = []
        rutas_archivos = []
        regex_pattern = request.form.get('regex_pattern', '') 

        uploaded_files_paths = []
        
        for file in uploaded_files:
            file_path = os.path.join(ruta_usuario, file.filename)
            file.save(file_path)
            uploaded_files_paths.append(file_path)  

        output_path, headers = cargar_archivos_limpiar(uploaded_files_paths, user_id)
        archivos_con_encabezados = dict(zip(output_path, headers))
        rutas_archivos.extend(output_path)
        session['rutas_archivos'] = rutas_archivos
        session['regex_pattern'] = regex_pattern
        session['archivos_con_encabezados'] = archivos_con_encabezados
        return render_template('Limpiar2.html', output_paths=output_paths, regex_pattern=regex_pattern, archivos_con_encabezados=archivos_con_encabezados)

    return render_template('Limpiar.html')

@app.route('/limpiar_archivos', methods=['POST'])
def limpiar_archivos():
    user_id = session.get('user_id')
    regex_pattern = session.get('regex_pattern')
    archivos_con_encabezados = session.get('archivos_con_encabezados')
    rutas_archivos = session.get('rutas_archivos')
    nombre_columna = [nombre.strip() for nombre in request.form.get('nombre_columna').split(',')]
    headers = {}
    for archivo in archivos_con_encabezados.keys():
        headers[archivo] = request.form.get('encabezados_' + archivo)
    
    columna_orden = None 
    output_paths = procesar_multiples_archivos(rutas_archivos, regex_pattern, nombre_columna, headers, user_id, columna_orden)

    return render_template('result.html', message='Archivos procesados y guardados exitosamente.', output_paths=output_paths)

# RUTAS PARA EL PROCESO DE CONSOLIDAR ARCHIVOS EN BASE GLOBAL O POR COLUMNAS
@app.route('/consolidar', methods=['GET','POST'])
def consolidar():
    saved_files_base = []
    headers_base = []
    saved_files_combinar = []
    headers_combinar = []

    if request.method == 'POST':
        modo_seleccionado = request.form.get('modo_seleccionado')

        if modo_seleccionado == 'concatenar_archivos':
            upload_filas_consolidar = request.files.getlist('file3[]')
            user_id = session.get('user_id')
            output_paths= []
            print(f'Archivos subidos: {upload_filas_consolidar}')

            consolidar_sin_columnas = cargar_archivo(upload_filas_consolidar, user_id)
            output_paths.append(consolidar_sin_columnas)
            print(f'ID de usuario que se obtiene dentro de la función Consolidados: {user_id}')
            print(f'rutas de salida: {output_paths}')

            return render_template('result4.html', message='Archivo Consolidado y guardado con éxito', output_paths=output_paths[0])
            
        elif modo_seleccionado == 'concatenar_por_columnas':
            uploaded_files_base = request.files.getlist('file4[]')
            uploaded_files_combinar = request.files.getlist('file5[]')
            user_id = session.get('user_id')
            saved_files_base, headers_base, saved_files_combinar, headers_combinar = cargar_archivos(
                uploaded_files_base, uploaded_files_combinar, user_id)
            
            session['archivo_base'] = saved_files_base
            session['archivo_combinar'] = saved_files_combinar
            session['columnas_combinar'] = headers_combinar
            return render_template('consolidacion2.html', saved_files_base=saved_files_base, saved_files_combinar=saved_files_combinar, headers_base=headers_base, headers_combinar=headers_combinar)
        
    return render_template('consolidacion.html')

@app.route('/consolidar_archivos', methods=['POST'])
def consolidar_columna():
    user_id = session.get('user_id')
    headers_base = request.form.get('encabezados_base')
    headers_combinar = request.form.get('encabezados_combinar')

    saved_files_base = session.get('archivo_base')[0]
    saved_files_combinar = session.get('archivo_combinar')
    print(f'Archivo Base subido: {saved_files_base}')
    print(f'Archivo a combinar subido: {saved_files_combinar}')

    columnas_seleccionadas = request.form.getlist('columnas_seleccionadas')

    saved_files_base = saved_files_base.replace("\\", "/")
    
    output_path = consolidar_archivos(saved_files_base, saved_files_combinar, headers_base, headers_combinar, columnas_seleccionadas, user_id)

    print(f'ruta de salida: {output_path}')
    return render_template('result3.html', message='Archivo Consolidado y guardado con éxito', output_paths=output_path)


# RUTAS PARA EL PROCESO DE DETALLAR ARCHIVOS, ELIMINAR EN BASE , O |
@app.route('/detalles', methods=['GET', 'POST'])
def detalles():
    print("Entrando a la ruta /detalles")
    if request.method == 'POST':
        print("Método POST detectado")
        modo_seleccionado = request.form.get('modo_seleccionado_detalle')
        print(f"Modo seleccionado: {modo_seleccionado}")

        if modo_seleccionado == 'limpiar_coma':
            upload_files = request.files.getlist('file1[]')
        elif modo_seleccionado == 'limpiar_tubo':
            upload_files = request.files.getlist('file2[]')

        print(f"Número de archivos cargados: {len(upload_files)}")

        ruta_temporal = 'Detallados'
        user_id = session.get('user_id')
        print(f"ID de usuario: {user_id}")
        output_paths = []

        for file in upload_files:
            file_path = os.path.join(ruta_temporal, file.filename)
            print(f"Guardando archivo en: {file_path}")
            file.save(file_path)

            print("Llamando a la función limpiar_detalle")
            output_path = limpiar_detalle(file_path, modo_seleccionado, user_id)
            print(f"Ruta de salida: {output_path}")
            output_paths.append(output_path)

            print("Eliminando archivo temporal")
            os.remove(file_path)

        print("Guardando rutas de salida en la sesión")
        session['output_paths'] = output_paths

        print("Renderizando plantilla result2.html")
        return render_template('result2.html', message='Archivos procesados y guardados exitosamente.', output_paths=output_paths)

    print("Renderizando plantilla detalles.html")
    return render_template('detalles.html')


@app.route('/descargas/<nombre_archivo>', methods=['GET'])
def servir_archivo(nombre_archivo):
    # Construir la ruta del archivo en la carpeta del usuario
    ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']), nombre_archivo)

    # Verificar si el archivo existe
    if not os.path.exists(ruta_archivo):
        return make_response("Archivo no encontrado", 404)

    # Enviar el archivo al usuario como descarga
    respuesta = make_response(send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id'])), nombre_archivo, as_attachment=True, mimetype='application/pdf'))

    # Iniciar un nuevo hilo que eliminará el archivo después de un cierto período de tiempo
    threading.Thread(target=eliminar_archivo_despues_de_tiempo, args=(ruta_archivo, 60)).start()

    return respuesta

@app.route('/buscar', methods=['GET','POST'])
def folios():
    return render_template('folios.html')

@app.route('/buscar_folios', methods=['GET','POST'])
def descargar_desde_numeros_de_folio():
    try:
        # Obtener el ID del usuario de la sesión
        user_id = session['user_id']

        # Crear la carpeta del usuario si no existe
        directorio_usuario = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
        if not os.path.exists(directorio_usuario):
            os.makedirs(directorio_usuario)

        data = request.json
        print("Datos recibidos: ", data)

        if 'busquedas' not in data or not isinstance(data['busquedas'], list):
            return jsonify({"error": "El formato del JSON es incorrecto"}), 400

        enlaces_descarga = []
        errores = []

        for parametros in data['busquedas']:
            enlaces, errores_descarga = descargar_en_paralelo(parametros, directorio_usuario)
            enlaces_descarga.extend(enlaces)
            errores.extend(errores_descarga)

        mensaje_respuesta = "Descarga de los folios al servidor" if not errores else "Descargas completadas para los folios encontrados al servidor"
        return jsonify({"mensaje": mensaje_respuesta, "enlaces_descarga": enlaces_descarga, "errores": errores}), 200

    except Exception as e:
        return jsonify({"error": f"Error inesperado: {e}"}), 500

# INICIO DE LA APLICACIÓN Y ASIGNACIÓN DE UN ID ÚNICO
@app.route('/')
def index():
    user_id = session.get('user_id')
    print(f'ID de usuario: {user_id}')
    if user_id is None:
        user_id = str(uuid.uuid4())  # Genera un nuevo UUID
        session['user_id'] = user_id
    # Devuelve la respuesta en todos los casos
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True )
    #logging.info('El servidor ha terminado')
