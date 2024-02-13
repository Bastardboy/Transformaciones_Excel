from flask import Flask, render_template, request, send_from_directory, session, abort
import os
import uuid
from Casos.utils import procesar_archivo, limpiar_detalle, cargar_archivos, consolidar_archivos, cargar_archivo

app = Flask(__name__)

#SESSION_TYPE = 'filesystem'  # Almacena la sesión en el sistema de archivos
# app.config.from_object(__name__)
# Session(app)

app.secret_key = 'tu_clave_secreta_super_secreta'  # Cambia esto a una cadena segura

# Filtro para obtener el nombre base de un archivo
@app.template_filter('basename')
def basename_filter(s):
    return os.path.basename(s)
app.jinja_env.filters['basename'] = basename_filter

#Ruta para la descarga de los archivos seccion Limpiados
@app.route('/limpiados/<user_id>/<filename>', methods=['GET'])
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
        ruta_temporal = 'Limpiados'

        user_id = session.get('user_id')

        output_paths = []

        regex_pattern = request.form.get('regex_pattern', '')  # Obtener el patrón de expresión regular desde el formulario

        for file in uploaded_files:
            file_path = os.path.join(ruta_temporal, file.filename)
            file.save(file_path)

            output_path = procesar_archivo(file_path, regex_pattern, user_id)
            output_paths.append(output_path)

            os.remove(file_path)

        # Guardar los resultados en la sesión del usuario
        session['output_paths'] = output_paths
        print(f'Contenido de la session: {session["output_paths"]}')
        return render_template('result.html', message='Archivos procesados y guardados exitosamente.', output_paths=output_paths)

    return render_template('Limpiar.html')


@app.route('/detalles', methods=['GET', 'POST'])
def detalles():
    if request.method == 'POST':
        upload_files = request.files.getlist('file2[]')
        ruta_temporal = 'Detallados'

        user_id = session.get('user_id')

        output_paths = []

        for file in upload_files:
            file_path = os.path.join(ruta_temporal, file.filename)
            file.save(file_path)

            output_path = limpiar_detalle(file_path, user_id)
            output_paths.append(output_path)

            os.remove(file_path)

        # Guardar los resultados en la sesión del usuario
        session['output_paths'] = output_paths
        print(f'Contenido de la session: {session["output_paths"]}')
        return render_template('result2.html', message='Archivos procesados y guardados exitosamente.', output_paths=output_paths)

    return render_template('detalles.html')

# Modifica la función consolidar
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
            
            session['archivo_base'] = saved_files_base
            session['archivo_combinar'] = saved_files_combinar
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

    print(f'headers_base: {headers_base}')
    print(f'headers_combinar: {headers_combinar}')

    print(f'saved_files_combinar: {saved_files_combinar}')

    saved_files_base = saved_files_base.replace("\\", "/")

    print(f'saved_files_base: {saved_files_base}')


    # Llama a la función consolidar_archivos para manejar la consolidación
    output_path = consolidar_archivos(saved_files_base,  saved_files_combinar, headers_base, headers_combinar, user_id)

    print(f'output_path: {output_path}')


    return render_template('result3.html', message='Archivo Consolidado y guardado con éxito', output_paths=output_path)

@app.route('/')
def index():

    user_id = session.get('user_id')

    if user_id is None:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
        print(f'Nuevo usuario. ID: {user_id}')
    else:
        print(f'Usuario existente. ID: {user_id}')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
 