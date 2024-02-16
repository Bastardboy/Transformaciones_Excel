from flask import Flask, render_template, request, send_from_directory, session, abort, jsonify, logging
import os
import uuid
from Casos.utils import procesar_multiples_archivos, limpiar_detalle, cargar_archivos, consolidar_archivos, cargar_archivo, cargar_archivos_limpiar
from itertools import chain

app = Flask(__name__)

#SESSION_TYPE = 'filesystem'  # Almacena la sesión en el sistema de archivos
# app.config.from_object(__name__)
# Session(app)

app.secret_key = 'tu_clave_secreta_super_secreta'  # Cambia esto a una cadena segura

@app.route('/obtener_columnas', methods=['GET'])
def obtener_columnas():
    columnas = session.get('columnas_combinar', [])
    print(f'Columnas a combinar: {columnas}')
    return jsonify({'columnas_combinar': columnas})

# Filtro para obtener el nombre base de un archivo
@app.template_filter('basename')
def basename_filter(s):
    return os.path.basename(s)
app.jinja_env.filters['basename'] = basename_filter

#Ruta para la descarga de los archivos seccion Limpiados
@app.route('/limpiar_archivos/<user_id>/<filename>', methods=['GET'])
def limpiados(user_id, filename):
    ruta_limpiados = os.path.join('Limpiados', user_id)

    try:
        filename = os.path.basename(filename)
        return send_from_directory(ruta_limpiados, filename, as_attachment=True)
    except FileNotFoundError:
        print(f'Intentando enviar {filename} desde {ruta_limpiados}')
        abort(404)

#Ruta para la descarga de los archivos seccion detallados
@app.route('/detallados/<user_id>/<filename>', methods=['GET'])
def detallados(user_id, filename):
    ruta_detallados = os.path.join('Detallados', user_id)

    try:
        filename = os.path.basename(filename)
        return send_from_directory(ruta_detallados, filename, as_attachment=True)
    except FileNotFoundError:
        print(f'Intentando enviar {filename} desde {ruta_detallados}')
        abort(404)


@app.route('/consolidados/<user_id>/<filename>', methods=['GET'])
def consolidados(user_id, filename):
    ruta_consolidados = os.path.join('Consolidados', user_id)

    try:
        return send_from_directory(ruta_consolidados, filename, as_attachment=True)
    except FileNotFoundError:
        print(f'Intentando enviar {filename} desde {ruta_consolidados}')
        abort(404)

@app.route('/limpiar', methods=['GET', 'POST'])
def limpiar():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('file[]')
        user_id = session.get('user_id')
        ruta_temporal = 'Limpiados'
        print(f'Archivos cargados (?):{uploaded_files}')
        ruta_usuario = os.path.join(ruta_temporal, user_id)

        # Asegúrate de que el directorio existe antes de guardar los archivos
        if not os.path.exists(ruta_usuario):
            os.makedirs(ruta_usuario)

        output_paths = []
        rutas_archivos = []
        regex_pattern = request.form.get('regex_pattern', '')  # Obtener el patrón de expresión regular desde el formulario

        uploaded_files_paths = []
        
        for file in uploaded_files:
            file_path = os.path.join(ruta_usuario, file.filename)
            file.save(file_path)
            uploaded_files_paths.append(file_path)  # Agregar la ruta del archivo a la lista

        print(f'uploaded_files_paths: {uploaded_files_paths}')

        output_path, headers = cargar_archivos_limpiar(uploaded_files_paths, user_id)
        archivos_con_encabezados = dict(zip(output_path, headers))
        rutas_archivos.extend(output_path)
        session['rutas_archivos'] = rutas_archivos
        session['regex_pattern'] = regex_pattern
        session['archivos_con_encabezados'] = archivos_con_encabezados
        return render_template('limpiar2.html', output_paths=output_paths, regex_pattern=regex_pattern, archivos_con_encabezados=archivos_con_encabezados)

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

    print(f'Headers: {headers}') # Headers Seleccionados
    print(f'Archivos con encabezados: {archivos_con_encabezados}') # Archivos y sus encabezados correspondientes
    print(f'Rutas archivos: {rutas_archivos}') # Ruta hacia donde se encuentran los archivos
    print(f'Nombre columna: {nombre_columna}') # Nombre de las columnas que deben existir en los archivos (sino, se crean)
    print(f'User ID: {user_id}') # ID del usuario
    
    columna_orden = None  # Deberías definir esto si es necesario
    output_paths = procesar_multiples_archivos(rutas_archivos, regex_pattern, nombre_columna, headers, user_id, columna_orden)

    return render_template('result.html', message='Archivos procesados y guardados exitosamente.', output_paths=output_paths)

@app.route('/consolidar', methods=['GET','POST'])
def consolidar():
    saved_files_base = []
    headers_base = []
    saved_files_combinar = []
    headers_combinar = []

    if request.method == 'POST':
        modo_seleccionado = request.form.get('modo_seleccionado')
        print(f'Modo seleccionado en la solicitud POST: {modo_seleccionado}')

        if modo_seleccionado == 'concatenar_archivos':
            upload_filas_consolidar = request.files.getlist('file3[]')
            user_id = session.get('user_id')
            output_paths= []
            print(f'ID de usuario: {user_id}')
            print(f'Archivos a consolidar: {upload_filas_consolidar}')
        
            consolidar_sin_columnas = cargar_archivo(upload_filas_consolidar, user_id) 
            print(f'consolidar_sin_columnas: {consolidar_sin_columnas}')  # Añadido para depuración

            output_paths.append(consolidar_sin_columnas)
            print(f'output_paths: {output_paths}')  # Añadido para depuración

            return render_template('result3.html', message='Archivo Consolidado y guardado con éxito', output_paths=output_paths)
            
        elif modo_seleccionado == 'concatenar_por_columnas':
            print('Entró en cocatenar_por_columnas')
            uploaded_files_base = request.files.getlist('file4[]')
            uploaded_files_combinar = request.files.getlist('file5[]')
            user_id = session.get('user_id')
            # Llama a la función cargar_archivos para manejar la carga
            saved_files_base, headers_base, saved_files_combinar, headers_combinar = cargar_archivos(
                uploaded_files_base, uploaded_files_combinar, user_id)
            
            session['columnas_combinar'] = headers_combinar
            return render_template('consolidacion2.html', saved_files_base=saved_files_base, saved_files_combinar=saved_files_combinar, headers_base=headers_base, headers_combinar=headers_combinar)
        
    return render_template('consolidacion.html')

@app.route('/consolidar_archivos', methods=['POST'])
def consolidar_columna():
    print(f'Nos encontramos en consolidar_archivos')
    user_id = session.get('user_id')
    headers_base = request.form.get('encabezados_base')
    headers_combinar = request.form.get('encabezados_combinar')

    saved_files_base = session.get('archivo_base')[0]
    saved_files_combinar = session.get('archivo_combinar')

    columnas_seleccionadas = request.form.getlist('columnas_seleccionadas')

    saved_files_base = saved_files_base.replace("\\", "/")

    # Llama a la función consolidar_archivos para manejar la consolidación
    output_path = consolidar_archivos(saved_files_base,  saved_files_combinar, headers_base, headers_combinar, columnas_seleccionadas, user_id)

    print(f'output_path: {output_path}')


    return render_template('result3.html', message='Archivo Consolidado y guardado con éxito', output_paths=output_path)

@app.route('/detalles', methods=['GET', 'POST'])
def detalles():
    # Hay que devolver las columnas, para que haga el menu desplegable
    if request.method == 'POST':
        modo_seleccionado = request.form.get('modo_seleccionado_detalle')
        print(f'Modo seleccionado en la solicitud POST: {modo_seleccionado}')

        if modo_seleccionado == 'limpiar_coma':
            upload_files = request.files.getlist('file1[]')
        elif modo_seleccionado == 'limpiar_tubo':
            upload_files = request.files.getlist('file2[]')

        ruta_temporal = 'Detallados'
        user_id = session.get('user_id')
        output_paths = []

        for file in upload_files:
            file_path = os.path.join(ruta_temporal, file.filename)
            file.save(file_path)

            # Pasa el modo seleccionado a la función limpiar_detalle
            output_path = limpiar_detalle(file_path, modo_seleccionado, user_id)
            output_paths.append(output_path)

            os.remove(file_path)

        # Guardar los resultados en la sesión del usuario
        session['output_paths'] = output_paths
        print(f'Contenido de la session: {session["output_paths"]}')

        return render_template('result2.html', message='Archivos procesados y guardados exitosamente.', output_paths=output_paths)

    return render_template('detalles.html')


@app.route('/')
def index():

    user_id = session.get('user_id')

    if user_id is None:
        user_id = str(uuid.uuid4())  # Genera un nuevo UUID
        session['user_id'] = user_id
        print(f'Nuevo usuario. ID: {user_id}')
    else:
        print(f'Usuario existente. ID: {user_id}')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
 