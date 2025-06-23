from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import os
import json
from datetime import datetime, timedelta
import jwt

app = Flask(__name__)
app.secret_key = 'clave_secreta_muy_segura'
JWT_SECRET = 'jwt_secret_compartido_entre_microservicios'
SESSION_TIMEOUT = timedelta(minutes=5)

# URL del microservicio de datos
DATA_SERVICE_URL = 'http://localhost:5005'
DATA_AUTH_URL='http://localhost:5000'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def menu_pacientes():
    return render_template('menu_pacientes.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('http://localhost:5000/')

@app.route('/ver_citas', methods=['GET'])
def ver_citas():
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/ver_citas'))

    direccion_wallet = session['wallet_address']
    
    try:
        # Llamar al microservicio de datos para obtener las citas
        response = requests.get(f'{DATA_SERVICE_URL}/api/citas/wallet/{direccion_wallet}')
        
        if response.status_code == 200:
            citas = response.json().get('citas', [])
        else:
            citas = []
            print(f"Error obteniendo citas: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        citas = []

    return render_template('ver_citas.html', citas=citas)

@app.route('/auth')
def auth():
    token = request.args.get('token')
    next_url = request.args.get('next', '/')

    if not token:
        return "No se proporcionó token de autenticación", 400

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        session['wallet_address'] = payload['wallet_address']
        session['rol'] = payload['rol']
        session['session_expira'] = datetime.utcnow() + SESSION_TIMEOUT
        return redirect(next_url)
    except jwt.ExpiredSignatureError:
        return "Token de autenticación expirado", 401
    except jwt.InvalidTokenError:
        return "Token de autenticación inválido", 401

@app.route('/agendar_cita', methods=['GET', 'POST'])
def agendar_cita():
    wallet_address = session.get('wallet_address', '')
    wallet_number = wallet_address[:42]

    if request.method == 'GET':
        return render_template('agendar_cita.html', nombre=wallet_number, error=None)

    nombre = request.form['nombre']
    fecha = request.form['fecha']
    hora = request.form['hora']
    tx_hash = request.form.get('tx_hash')


    # Validaciones básicas del lado del cliente
    try:
        dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        return render_template('agendar_cita.html', nombre=wallet_number,
                               error="Fecha u hora inválida.")

    if dt.weekday() > 4:
        return render_template('agendar_cita.html', nombre=wallet_number,
                               error="Solo se pueden agendar citas de lunes a viernes.")
    if dt.hour < 8 or dt.hour >= 15:
        return render_template('agendar_cita.html', nombre=wallet_number,
                               error="La hora debe estar entre las 08:00 y las 14:00.")

    # Datos de la cita
    cita_data = {
        "wallet_address": wallet_address,
        "nombre": nombre,
        "fecha": fecha,
        "hora": hora,
        "tx_hash": tx_hash
    }

    try:
        # Llamar al microservicio de datos para crear la cita
        response = requests.post(f'{DATA_SERVICE_URL}/api/citas', json=cita_data)
        
        if response.status_code == 201:
            result = response.json()
            return render_template("confirmacion_cita.html", archivo=result.get('archivo'))
        elif response.status_code == 409:
            error_msg = response.json().get('error', 'Horario no disponible')
            return render_template('agendar_cita.html', nombre=wallet_number, error=error_msg)
        else:
            error_msg = response.json().get('error', 'Error al crear la cita')
            return render_template('agendar_cita.html', nombre=wallet_number, error=error_msg)
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        return render_template('agendar_cita.html', nombre=wallet_number,
                               error="Error de conexión. Inténtalo más tarde.")

@app.route('/ver_historial')
def ver_historial():
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/ver_historial'))
    
    wallet_address = session['wallet_address']
    
    try:
        # Obtener el CID del historial desde el microservicio de datos
        response = requests.get(f'{DATA_SERVICE_URL}/api/historial/cid/{wallet_address}')
        
        if response.status_code == 200:
            result = response.json()
            cid = result.get('cid')
            
            if cid:
                # Descargar el JSON directamente desde IPFS en el frontend
                archivo_tmp = os.path.join(BASE_DIR, f"historial_tmp_{wallet_address}.json")
                
                if descargar_json_de_ipfs(cid, archivo_tmp):
                    try:
                        with open(archivo_tmp, 'r') as f:
                            datos = json.load(f)
                    except Exception as e:
                        datos = {"error": "No se pudo leer el JSON", "detalle": str(e)}
                    finally:
                        if os.path.exists(archivo_tmp):
                            os.remove(archivo_tmp)
                else:
                    datos = {"error": "No se pudo descargar desde IPFS"}
            else:
                datos = {"error": "CID no encontrado"}
                
        elif response.status_code == 404:
            datos = {"error": "No se encontró historial médico para su cartera"}
        else:
            datos = {"error": "Error obteniendo información del historial"}
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        datos = {"error": "Error de conexión con el servicio de datos"}

    return render_template("ver_historial.html", historial=datos)

@app.route('/salir_historial')
def salir_historial():
    return redirect(url_for('menu_pacientes'))

@app.route('/anular', methods=['POST'])
def anular_cita():
    archivo = request.form.get('cita_id')

    if not archivo:
        return "Falta el identificador de la cita.", 400

    try:
        # Llamar al microservicio de datos para eliminar la cita
        response = requests.delete(f'{DATA_SERVICE_URL}/api/citas/{archivo}')
        
        if response.status_code == 200:
            return redirect(url_for('ver_citas'))
        elif response.status_code == 404:
            return "Cita no encontrada.", 404
        else:
            error_msg = response.json().get('error', 'Error al eliminar la cita')
            return f"No se pudo eliminar la cita: {error_msg}", 500
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        return "Error de conexión. Inténtalo más tarde.", 500

# Función auxiliar para descargar desde IPFS
def descargar_json_de_ipfs(cid, nombre_archivo_salida):
    try:
        url = f'http://127.0.0.1:5001/api/v0/cat?arg={cid}'
        response = requests.post(url)
        if response.status_code == 200:
            with open(nombre_archivo_salida, 'wb') as f:
                f.write(response.content)
            return True
        else:
            print(f"Error IPFS: {response.content}")
            return False
    except Exception as e:
        print(f"Error IPFS: {e}")
        return False

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5004)