from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
from datetime import datetime, timedelta
import jwt  # Necesitarás instalar PyJWT: pip install PyJWT

app = Flask(__name__)
app.secret_key = 'clave_secreta_muy_segura'
JWT_SECRET = 'jwt_secret_compartido_entre_microservicios'
SESSION_TIMEOUT = timedelta(minutes=5)


# Cargar wallets permitidas desde archivo
def cargar_wallets_permitidas():
    filename = "wallets_permitidas.txt"
    if not os.path.exists(filename):
        open(filename, 'w').close()
    with open(filename, "r") as file:
        return {line.strip().lower() for line in file.readlines()}

@app.before_request
def verificar_sesion():
    rutas_protegidas = {'/menu', '/elegir_rol', '/anular'}
    if request.path in rutas_protegidas:
        wallet_address = session.get('wallet_address')
        session_expira = session.get('session_expira')
        if session_expira and isinstance(session_expira, str):
            session_expira = datetime.fromisoformat(session_expira)
        if not wallet_address or (session_expira and datetime.utcnow() > session_expira):
            session.clear()
            return redirect(url_for('index'))

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/conectar', methods=['POST'])
def conectar():
    wallet_address = request.form.get('wallet_address')
    if not wallet_address:
        return redirect(url_for('index'))

    wallet_lower = wallet_address.lower()

    def cargar_wallets(archivo):
        if not os.path.exists(archivo):
            return set()
        with open(archivo, "r") as file:
            return {line.strip().lower() for line in file.readlines()}

    # Comprobar en cada archivo de roles
    roles_posibles = {
        'paciente': wallet_lower in cargar_wallets("wallets/wallets_pacientes.txt"),
        'doctor': wallet_lower in cargar_wallets("wallets/wallets_doctores.txt"),
        'laboratorio': wallet_lower in cargar_wallets("wallets/wallets_laboratorios.txt"),
    }

    # Filtrar los roles válidos
    roles_validos = [rol for rol, tiene in roles_posibles.items() if tiene]

    if not roles_validos:
        return redirect(url_for('index'))

    # Guardar wallet en sesión (en minúscula por consistencia)
    session['wallet_address'] = wallet_lower

    if len(roles_validos) == 1:
        # Si solo tiene un rol, iniciamos sesión directamente
        rol = roles_validos[0]
        session['rol'] = rol
        expira = datetime.utcnow() + SESSION_TIMEOUT
        session['session_expira'] = expira.isoformat()
        
        # Generar token JWT
        token = jwt.encode({
            'wallet_address': wallet_lower,
            'rol': rol,
            'exp': expira
        }, JWT_SECRET, algorithm='HS256')
        
        # Guardar token en sesión
        session['auth_token'] = token
        
        if rol == 'paciente':
            redirect_url = f"http://localhost:5004/auth?token={token}"
            return redirect(redirect_url)
        elif rol == 'doctor':
            redirect_url = f"http://localhost:5006/auth?token={token}"
            return redirect(redirect_url)

        # Para otros roles, ir al menú normal
        return redirect(url_for('menu'))

    # Si tiene múltiples roles, guardar la lista y redirigir para elegir
    session['roles_validos'] = roles_validos
    return redirect(url_for('elegir_rol'))

# También modificar elegir_rol para redirigir si se elige el rol de paciente
@app.route('/elegir_rol', methods=['GET', 'POST'])
def elegir_rol():
    if request.method == 'POST':
        rol_elegido = request.form.get('rol')
        if rol_elegido and rol_elegido in session.get('roles_validos', []):
            session['rol'] = rol_elegido
            expira = datetime.utcnow() + SESSION_TIMEOUT
            session['session_expira'] = expira.isoformat()
            
            # Generar token JWT
            token = jwt.encode({
                'wallet_address': session['wallet_address'],
                'rol': rol_elegido,
                'exp': expira
            }, JWT_SECRET, algorithm='HS256')
            
            # Guardar token en sesión
            session['auth_token'] = token
            
            # Si el rol elegido es paciente, redirigir automáticamente al microservicio de pacientes
            if rol_elegido == 'paciente':
                redirect_url = f"http://localhost:5004/auth?token={token}"
                return redirect(redirect_url)
            elif rol_elegido == 'doctor':
                redirect_url = f"http://localhost:5006/auth?token={token}"
                return redirect(redirect_url)

            
            # Para otros roles, ir al menú normal
            return redirect(url_for('menu'))
        return redirect(url_for('elegir_rol'))

    roles_validos = session.get('roles_validos', [])
    return render_template('elegir_rol.html', roles_validos=roles_validos)

# Añadir ruta para redirigir al servicio de pacientes
@app.route('/ir_a_pacientes')
def ir_a_pacientes():
    if 'auth_token' not in session:
        return redirect(url_for('index'))
    
    token = session['auth_token']
    redirect_url = f"http://localhost:5004/auth?token={token}"
    return redirect(redirect_url)

@app.route('/ir_a_doctores')
def ir_a_doctores():
    if 'auth_token' not in session:
        return redirect(url_for('index'))
    
    token = session['auth_token']
    redirect_url = f"http://localhost:5006/auth?token={token}"
    return redirect(redirect_url)


# Añadir una ruta para validar token (para que otros servicios puedan verificar)
@app.route('/validate_token', methods=['POST'])
def validate_token():
    token = request.json.get('token')
    if not token:
        return jsonify({'valid': False, 'error': 'No token provided'}), 400
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return jsonify({'valid': True, 'payload': payload})
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'valid': False, 'error': 'Invalid token'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/menu')
def menu():
    rol = session.get('rol')
    if not rol:
        return redirect(url_for('index'))

    session['session_expira'] = (datetime.utcnow() + SESSION_TIMEOUT).isoformat()

    if rol == 'paciente':
        return render_template('pacientes_service/templates/menu_pacientes.html')
    elif rol == 'doctor':
        return render_template('doctores_service/templates/menu_doctores.html')
    elif rol == 'laboratorio':
        return render_template('laboratorios_service/templates/menu_laboratorios.html')
    else:
        return redirect(url_for('index'))



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)