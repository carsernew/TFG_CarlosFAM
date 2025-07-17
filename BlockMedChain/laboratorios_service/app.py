from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import os
import json
from datetime import datetime, timedelta
import jwt

app = Flask(__name__)
app.secret_key = 'clave_secreta_medico_muy_segura'
JWT_SECRET = 'jwt_secret_compartido_entre_microservicios'
SESSION_TIMEOUT = timedelta(minutes=5)
DATA_SERVICE_URL = 'http://localhost:5005'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def menu_laboratorios():
    return render_template('menu_laboratorios.html')

@app.route('/estadisticas')
def estadisticas_dashboard():
    return render_template('estadisticas.html')

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

@app.route('/historiales_anonimos', methods=['GET'])
def historiales_anonimos():
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/historiales_anonimos'))
    
    # Obtener historiales anonimizados desde el microservicio 5005
    historiales = []
    try:
        response = requests.get(f'{DATA_SERVICE_URL}/api/historial/anonimizado/all')
        if response.status_code == 200:
            data = response.json()
            historiales = data.get('historiales_anonimizados', [])
        else:
            print(f"Error obteniendo historiales: {response.status_code}")
    except Exception as e:
        print(f"Error conectando con el servicio de datos: {e}")
    
    return render_template('historiales_anonimos.html', historiales=historiales)

@app.route('/ver_historial_anonimo/<cid>')
def ver_historial_anonimo(cid):
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next=f'/ver_historial_anonimo/{cid}'))
    
    # Obtener el historial específico por CID
    historial_data = None
    try:
        # Descargar contenido desde IPFS
        contenido = descargar_json_de_ipfs(cid)
        if contenido:
            historial_data = {
                "cid": cid,
                "contenido": contenido
            }
    except Exception as e:
        print(f"Error obteniendo historial: {e}")
    
    return render_template('ver_historial_anonimo.html', 
                         historial=historial_data, 
                         cid=cid)

def descargar_json_de_ipfs(cid):
    """
    Descarga contenido JSON desde IPFS usando un CID
    """
    try:
        url = f'http://127.0.0.1:5001/api/v0/cat?arg={cid}'
        response = requests.post(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error IPFS: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error IPFS: {e}")
        return None

@app.route('/logout')
def logout():
    session.clear()
    return redirect('http://localhost:5000/')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5007)