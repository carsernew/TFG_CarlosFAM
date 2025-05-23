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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CITAS_JSON_DIR = os.path.join(BASE_DIR, 'citas_json')
os.makedirs(CITAS_JSON_DIR, exist_ok=True)

@app.route('/')
def menu_pacientes():
    return render_template('menu_pacientes.html')

@app.route('/ver_citas', methods=['GET', 'POST'])
def ver_citas():
    citas = []
    nombre = ''

    if request.method == 'POST':
        nombre = request.form['nombre']
        for filename in os.listdir(CITAS_JSON_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(CITAS_JSON_DIR, filename), 'r') as f:
                    cita = json.load(f)
                    if cita.get('nombre') == nombre:
                        citas.append((filename, cita.get('fecha'), cita.get('hora')))
    
    return render_template('ver_citas.html', citas=citas, nombre=nombre)

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
    if request.method == 'GET':
        wallet_address = session.get('wallet_address', '')
        wallet_number = wallet_address[:42]  
        return render_template('agendar_cita.html', nombre=wallet_number)

    wallet_address = session.get('wallet_address', '')
    nombre = request.form['nombre']
    fecha = request.form['fecha']
    hora = request.form['hora']

    try:
        dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "Fecha u hora inválida", 400

    if dt.weekday() > 4:
        return "Solo se pueden agendar citas de lunes a viernes.", 400
    if dt.hour < 8 or dt.hour >= 15:
        return "La hora debe estar entre las 08:00 y las 14:00.", 400

    recorte = wallet_address[:8]
    nombre_archivo = f"Cita_{fecha}_{recorte}.json"
    ruta = os.path.join(CITAS_JSON_DIR, nombre_archivo)

    cita_json = {
        "nombre": nombre,
        "fecha": fecha,
        "hora": hora
    }

    with open(ruta, 'w') as f:
        json.dump(cita_json, f, indent=2)

    return render_template("confirmacion_cita.html", archivo=nombre_archivo)

@app.route('/ver_historial')
def ver_historial():
    cid = "QmeEdvhVJ2uDe828ow5Rx2qgVM6N21ro94ze23f7hbnnps"
    archivo_tmp = os.path.join(BASE_DIR, "historial_tmp.json")

    if descargar_json_de_ipfs(cid, archivo_tmp):
        try:
            with open(archivo_tmp, 'r') as f:
                datos = json.load(f)
        except Exception as e:
            datos = {"error": "No se pudo leer el JSON", "detalle": str(e)}
        finally:
            os.remove(archivo_tmp)
    else:
        datos = {"error": "No se pudo descargar desde IPFS"}

    return render_template("ver_historial.html", historial=datos)

@app.route('/salir_historial')
def salir_historial():
    temp_file = session.pop('temp_historial', None)
    if temp_file and os.path.exists(temp_file):
        os.remove(temp_file)
    return redirect(url_for('menu_pacientes'))

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
