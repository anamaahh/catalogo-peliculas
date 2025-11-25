from flask import Flask, request, jsonify, render_template, session, redirect
import requests
import os
from dotenv import load_dotenv

#Configuración Firebase
try:
    from firebase_config import db
    from firebase_admin import auth as auth_firebase
except ImportError:
    print("Error: No se pudo importar firebase_config")
    db = None

load_dotenv()

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = 'clave-secreta-catalogo-2024'

#API OMDb
CLAVE_OMDB = os.getenv('OMDB_API_KEY', 'e50e83fa')
URL_OMDB = "http://www.omdbapi.com/"

class CatalogoPeliculas:
    def __init__(self):
        self.db = db
    
    def verificar_token(self, token_id):
        try:
            if not auth_firebase:
                return None
            token_decodificado = auth_firebase.verify_id_token(token_id)
            return token_decodificado['uid']
        except Exception as error:
            print(f"Error verificando token: {error}")
            return None

    def actualizar_pelicula(self, id_usuario, id_pelicula, datos_pelicula):
        try:
            if not self.db:
                return False
            referencia = self.db.collection('users').document(id_usuario).collection('movies').document(id_pelicula)
            
            datos_pelicula['id'] = id_pelicula
            referencia.update(datos_pelicula)
            return True
        except Exception as error:
            print(f"Error actualizando: {error}")
            return False    
    
    def obtener_peliculas(self, id_usuario):
        try:
            if not self.db:
                return []
            referencia = self.db.collection('users').document(id_usuario).collection('movies')
            peliculas = referencia.stream()
            return [{"id": pelicula.id, **pelicula.to_dict()} for pelicula in peliculas]
        except Exception as error:
            print(f"Error obteniendo: {error}")
            return []
    
    def agregar_pelicula(self, id_usuario, datos_pelicula):
        try:
            if not self.db:
                return False
            referencia = self.db.collection('users').document(id_usuario).collection('movies')
            documento = referencia.document()
            datos_pelicula['id'] = documento.id
            documento.set(datos_pelicula)
            return True
        except Exception as error:
            print(f"Error agregando: {error}")
            return False
    
    def eliminar_pelicula(self, id_usuario, id_pelicula):
        try:
            if not self.db:
                return False
            referencia = self.db.collection('users').document(id_usuario).collection('movies').document(id_pelicula)
            referencia.delete()
            return True
        except Exception as error:
            print(f"Error eliminando: {error}")
            return False

catalogo = CatalogoPeliculas()

#Autenticación
@app.before_request
def antes_de_peticion():
    rutas_publicas = ['pagina_login', 'static', 'manejar_login', 'pagina_reset', 'accion_firebase', 'manejar_reset']
    
    if request.endpoint in rutas_publicas:
        return None
    
    if 'user_id' not in session:
        return redirect('/login')
    
    return None

#Paginas
@app.route('/')
def inicio():
    return render_template('catalogoo.html')

@app.route('/login')
def pagina_login():
    if 'user_id' in session:
        return redirect('/')
    return render_template('login.html')

@app.route('/olvido-contra')
def pagina_reset():
    codigo = request.args.get('oobCode')
    if not codigo:
        return redirect('/login?error=Enlace inválido')
    return render_template('olvido-contra.html', oobCode=codigo)

# Acciones Firebase
@app.route('/auth/action')
def accion_firebase():
    modo = request.args.get('mode')
    codigo = request.args.get('oobCode')
    
    if modo == 'resetPassword':  # ← Firebase manda esto
        return redirect(f'/olvido-contra?oobCode={codigo}')  # ← Tú rediriges a español
    elif modo == 'verifyEmail':
        return redirect('/login?message=Email verificado')
    else:
        return redirect('/login')

#APIS
@app.route('/api/login', methods=['POST'])
def manejar_login():
    datos = request.json
    token = datos.get('idToken')
    
    id_usuario = catalogo.verificar_token(token)
    if id_usuario:
        session['user_id'] = id_usuario
        return jsonify({'success': True, 'message': 'Login exitoso'})
    else:
        return jsonify({'success': False, 'message': 'Token inválido'}), 401

@app.route('/api/logout', methods=['POST'])
def manejar_logout():
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Sesión cerrada'})

@app.route('/api/movies', methods=['GET'])
def obtener_peliculas():
    id_usuario = session.get('user_id')
    if not id_usuario:
        return jsonify({'error': 'No autorizado'}), 401
    
    peliculas = catalogo.obtener_peliculas(id_usuario)
    return jsonify(peliculas)

@app.route('/api/movies', methods=['POST'])
def agregar_pelicula():
    id_usuario = session.get('user_id')
    if not id_usuario:
        return jsonify({'error': 'No autorizado'}), 401
    
    datos = request.json
    
    campos_requeridos = ['title', 'year', 'director', 'genre']
    for campo in campos_requeridos:
        if campo not in datos or not datos[campo]:
            return jsonify({'error': f'Falta {campo}'}), 400
    
    #Buscar en OMDb
    try:
        params = {'t': datos['title'], 'apikey': CLAVE_OMDB}
        respuesta = requests.get(URL_OMDB, params=params)
        datos_omdb = respuesta.json()

        datos['poster'] = ''
        datos['plot'] = ''
        datos['imdbRating'] = 'N/A'

        if datos_omdb.get('Response') == 'True':
            datos['poster'] = datos_omdb.get('Poster', '')
            datos['plot'] = datos_omdb.get('Plot', '')
            datos['imdbRating'] = datos_omdb.get('imdbRating', 'N/A')

    except Exception as error:
        print(f"Error OMDb: {error}")

    if catalogo.agregar_pelicula(id_usuario, datos):
        return jsonify({'success': True, 'message': 'Película agregada'})
    else:
        return jsonify({'error': 'Error agregando'}), 500

@app.route('/api/movies/<movie_id>', methods=['PUT'])
def actualizar_pelicula(movie_id):
    id_usuario = session.get('user_id')
    if not id_usuario:
        return jsonify({'error': 'No autorizado'}), 401
    
    datos = request.json
    
    campos_requeridos = ['title', 'year', 'director', 'genre']
    for campo in campos_requeridos:
        if campo not in datos or not datos[campo]:
            return jsonify({'error': f'Falta {campo}'}), 400
    
    # Buscar poster si cambió título o año
    try:
        referencia = db.collection('users').document(id_usuario).collection('movies').document(movie_id)
        pelicula_existente = referencia.get()
        
        if pelicula_existente.exists:
            datos_existentes = pelicula_existente.to_dict()
            
            titulo_cambio = datos_existentes.get('title') != datos['title']
            año_cambio = datos_existentes.get('year') != datos['year']
            
            if titulo_cambio or año_cambio:
                params = {'t': datos['title'], 'apikey': CLAVE_OMDB}
                respuesta = requests.get(URL_OMDB, params=params)
                datos_omdb = respuesta.json()

                if datos_omdb.get('Response') == 'True':
                    datos['poster'] = datos_omdb.get('Poster', '')
                    datos['plot'] = datos_omdb.get('Plot', '')
                    datos['imdbRating'] = datos_omdb.get('imdbRating', 'N/A')
                else:
                    datos['poster'] = datos_existentes.get('poster', '')
                    datos['plot'] = datos_existentes.get('plot', '')
                    datos['imdbRating'] = datos_existentes.get('imdbRating', 'N/A')
            else:
                datos['poster'] = datos_existentes.get('poster', '')
                datos['plot'] = datos_existentes.get('plot', '')
                datos['imdbRating'] = datos_existentes.get('imdbRating', 'N/A')
    except Exception as error:
        print(f"Error OMDb: {error}")
        if pelicula_existente.exists:
            datos_existentes = pelicula_existente.to_dict()
            datos['poster'] = datos_existentes.get('poster', '')
            datos['plot'] = datos_existentes.get('plot', '')
            datos['imdbRating'] = datos_existentes.get('imdbRating', 'N/A')
    
    if catalogo.actualizar_pelicula(id_usuario, movie_id, datos):
        return jsonify({'success': True, 'message': 'Película actualizada'})
    else:
        return jsonify({'error': 'Error actualizando'}), 500

@app.route('/api/movies/<movie_id>', methods=['DELETE'])
def eliminar_pelicula(movie_id):
    id_usuario = session.get('user_id')
    if not id_usuario:
        return jsonify({'error': 'No autorizado'}), 401
    
    if catalogo.eliminar_pelicula(id_usuario, movie_id):
        return jsonify({'success': True, 'message': 'Película eliminada'})
    else:
        return jsonify({'error': 'Error eliminando'}), 500

@app.route('/api/search-omdb', methods=['POST'])
def buscar_omdb():
    datos = request.json
    titulo = datos.get('title', '')
    año = datos.get('year', '')
    
    try:
        params = {'t': titulo, 'y': año, 'apikey': CLAVE_OMDB}
        respuesta = requests.get(URL_OMDB, params=params)
        datos_omdb = respuesta.json()
        
        if datos_omdb.get('Response') == 'True':
            return jsonify({
                'success': True,
                'data': {
                    'title': datos_omdb.get('Title'),
                    'year': datos_omdb.get('Year'),
                    'director': datos_omdb.get('Director'),
                    'genre': datos_omdb.get('Genre'),
                    'poster': datos_omdb.get('Poster'),
                    'plot': datos_omdb.get('Plot'),
                    'imdbRating': datos_omdb.get('imdbRating')
                }
            })
        else:
            return jsonify({'success': False, 'message': 'No encontrada'})
    except Exception as error:
        return jsonify({'success': False, 'message': str(error)})

@app.route('/api/olvido-contra', methods=['POST'])
def manejar_reset():
    try:
        datos = request.json
        codigo = datos.get('oobCode')
        nueva_contraseña = datos.get('newPassword')
        
        if not codigo or not nueva_contraseña:
            return jsonify({
                'success': False, 
                'message': 'Código y contraseña requeridos'
            }), 400
        
        correo = auth_firebase.verify_password_reset_code(codigo)
        auth_firebase.confirm_password_reset(codigo, nueva_contraseña)
        
        print(f"Contraseña cambiada: {correo}")
        
        return jsonify({
            'success': True, 
            'message': 'Contraseña cambiada'
        })
        
    except Exception as error:
        print(f"Error: {error}")
        mensaje = 'Error cambiando contraseña'
        
        if 'expired' in str(error):
            mensaje = 'Enlace expirado'
        elif 'invalid' in str(error):
            mensaje = 'Enlace inválido'
        
        return jsonify({
            'success': False, 
            'message': mensaje
        }), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)